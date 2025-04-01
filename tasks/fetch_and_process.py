import asyncio
from datetime import datetime, timezone
import aiohttp
from database.inserting import store_event, update_status
from database.queries import event_exists
from api.event_req import fetch_events_from_api, fetch_event_details
from config.logging import logger

from config.config import (
    DISCORD_BOT_TOKEN,
    DISCORD_CHANNEL_ID,
    DISCORD_CHANNEL_ID_TWO,
    TICKETMASTER_API_KEY,
    REDIRECT_URI,
    DATABASE_URL,
    REGION
)

async def fetch_events():
    """Fetch events asynchronously from Ticketmaster API and process them."""
    logger.info("Starting to fetch events from Ticketmaster API...")
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    page = 0
    max_pages = 5
    total_events_received = 0
    total_events_processed = 0
    new_events_count = 0

    try:
        async with aiohttp.ClientSession() as session:
            while page < max_pages:
                events = await fetch_events_from_api(session, page, current_time, current_date)
                events_count = len(events)
                total_events_received += events_count
                logger.info(f"Page {page + 1}: Received {events_count} events.")

                for event in events:
                    total_events_processed += 1
                    if await process_event(event):
                        new_events_count += 1

                if events_count < 199:
                    logger.info("No more events to fetch. Stopping.")
                    break

                page += 1
                await asyncio.sleep(1)  # Avoid hitting rate limits

        logger.info(f"Total events received: {total_events_received}, "
                    f"Total events processed: {total_events_processed}, "
                    f"New events added: {new_events_count}")
        
        await update_status(REGION, datetime.now(timezone.utc), total_events_received, new_events_count, None)

    except Exception as e:
        logger.error(f"Unexpected error in fetch_events: {e}", exc_info=True)
        await update_status(
            REGION,
            error_messages=str(e)
        )

async def process_event(event):
    """
    Check if an event exists and store it if not. For new events, fetch detailed information 
    including presale data before storing.
    """
    from config.db_pool import db_pool  # Import shared db_pool here
    from helpers.formatting import format_date_human_readable
    from tasks.notify_events import notify_events  # Import notify_events here to avoid circular imports

    try:
        async with db_pool.acquire() as conn:
            event_id = event["id"]
            if not await event_exists(conn, event_id):
                logger.info(f"Found new event: {event_id} - {event['name']}")
                
                # For new events, fetch detailed information to get complete presale data
                async with aiohttp.ClientSession() as session:
                    detailed_event = await fetch_event_details(session, event_id)
                    
                # If detailed event fetch was successful, use that instead of the list event data
                if detailed_event:
                    logger.info(f"Successfully fetched detailed information for event: {event_id}")
                    event_to_store = detailed_event
                else:
                    logger.warn(f"Could not fetch detailed information for event: {event_id}. Using summary data.")
                    event_to_store = event
                
                try:
                    await store_event(event_to_store)
                    logger.debug(f"Successfully stored event: {event_id}")

                    # Check if the artist is notable after storing
                    notable_artist_query = '''
                    SELECT Artists.notable
                    FROM Artists
                    WHERE Artists.artistID = $1
                    '''
                    artist_notable = await conn.fetchval(notable_artist_query, event_to_store.get("artistID"))

                    if artist_notable:
                        logger.info(f"Event {event_id} associated with notable artist. Triggering notifications.")
                        # Call notify_events with notable_only set to True
                        await notify_events(event_to_store["bot"], DISCORD_CHANNEL_ID, notable_only=True)

                    return True  # New event added

                except Exception as e:
                    logger.error(f"Error storing event: {event_id}, name: {event['name']}, error: {e}")
                    return False  # Failed to store event
            else:
                logger.debug(f"Event already exists in DB: {event_id} - {event['name']}")
                return False  # Event already exists
    except Exception as e:
        logger.error(f"Failed to acquire DB connection for event: {event_id}, error: {e}")
        return False  # Failed to process event