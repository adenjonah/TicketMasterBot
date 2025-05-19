import asyncio
from datetime import datetime, timezone
import aiohttp
from database.inserting import store_event, update_status, record_notable_events_data
from database.queries import event_exists
from api.event_req import fetch_events_from_api, fetch_event_details
from config.logging import logger
import logging

from config.config import (
    DISCORD_BOT_TOKEN,
    DISCORD_CHANNEL_ID,
    DISCORD_CHANNEL_ID_TWO,
    TICKETMASTER_API_KEY,
    REDIRECT_URI,
    DATABASE_URL,
    REGION
)

# Map full region names to their two-character IDs
REGION_TO_ID = {
    'north': 'no',
    'east': 'ea',
    'south': 'so',
    'west': 'we',
    'europe': 'eu',
    'comedy': 'co',
    'film': 'fi'  # New film region
}

# Get server ID from region
def get_server_id(region):
    return REGION_TO_ID.get(region.lower(), region.lower()[:2])

async def fetch_events():
    """Fetch events asynchronously from Ticketmaster API and process them."""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Starting to fetch events from Ticketmaster API...")
    
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    page = 0
    max_pages = 5
    total_events_received = 0
    total_events_processed = 0
    new_events_count = 0
    
    server_id = get_server_id(REGION)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Using server ID {server_id} for region {REGION}")

    try:
        async with aiohttp.ClientSession() as session:
            while page < max_pages:
                # Use specialized event fetch methods based on region
                if REGION.lower() == 'film':
                    from api.film_events import fetch_film_events
                    events = await fetch_film_events(session, page, current_time, current_date)
                else:
                    events = await fetch_events_from_api(session, page, current_time, current_date)
                
                events_count = len(events)
                total_events_received += events_count
                
                # Only log per-page counts in debug mode
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Page {page + 1}: Received {events_count} events.")

                for event in events:
                    total_events_processed += 1
                    if await process_event(event, server_id):
                        new_events_count += 1

                if events_count < 199:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("No more events to fetch. Stopping.")
                    break

                page += 1
                await asyncio.sleep(1)  # Avoid hitting rate limits

        # Log summary info at INFO level, but only if there are new events
        if new_events_count > 0 and logger.isEnabledFor(logging.INFO):
            logger.info(f"Events update: {new_events_count} new events")
            
        # More detailed summary only in debug mode
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Total events received: {total_events_received}, "
                      f"Total events processed: {total_events_processed}, "
                      f"New events added: {new_events_count}")
        
        await update_status(server_id, datetime.now(timezone.utc), total_events_received, new_events_count, None)

    except Exception as e:
        logger.error(f"Error in fetch_events: {e}")
        await update_status(
            server_id,
            error_messages=str(e)
        )

async def process_event(event, server_id):
    """
    Check if an event exists and store it if not. For new events, fetch detailed information 
    including presale data before storing.
    """
    from config.db_pool import db_pool  # Import shared db_pool here
    from helpers.formatting import format_date_human_readable
    from tasks.notify_events import notify_events_legacy  # Import notify_events_legacy here to avoid circular imports

    try:
        async with db_pool.acquire() as conn:
            event_id = event["id"]
            if not await event_exists(conn, event_id):
                # Only log new events at debug level unless they're notable events
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Found new event: {event_id} - {event['name']}")
                
                # For new events, fetch detailed information to get complete presale data
                async with aiohttp.ClientSession() as session:
                    detailed_event = await fetch_event_details(session, event_id)
                    
                # If detailed event fetch was successful, use that instead of the list event data
                if detailed_event:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Successfully fetched detailed information for event: {event_id}")
                    event_to_store = detailed_event
                else:
                    logger.warning(f"Could not fetch details for event: {event_id}")
                    event_to_store = event
                
                try:
                    # Pass the server_id as the region parameter
                    await store_event(event_to_store, region=server_id)
                    
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Stored event: {event_id} with region: {server_id}")

                    # Check if the artist is notable after storing
                    notable_artist_query = '''
                    SELECT Artists.notable
                    FROM Artists
                    WHERE Artists.artistID = $1
                    '''
                    artist_notable = await conn.fetchval(notable_artist_query, event_to_store.get("artistID"))

                    if artist_notable:
                        # Log notable events at INFO level
                        if logger.isEnabledFor(logging.INFO):
                            logger.info(f"Notable artist event: {event_id} - {event['name']}")
                            
                        # Call notify_events_legacy with notable_only set to True
                        await notify_events_legacy(event_to_store["bot"], DISCORD_CHANNEL_ID, notable_only=True)
                        
                        # Record the notable event data in the time series
                        await record_notable_events_data(
                            region=server_id,
                            timestamp=datetime.now(timezone.utc),
                            total_events=1,  # This is just one event
                            new_events=1     # Since we're in the new event path
                        )

                    return True  # New event added

                except Exception as e:
                    logger.error(f"Error storing event {event_id}: {e}")
                    return False  # Failed to store event
            else:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Event exists: {event_id}")
                return False  # Event already exists
    except Exception as e:
        logger.error(f"DB error processing event {event.get('id', 'unknown')}: {e}")
        return False  # Failed to process event