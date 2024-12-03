import asyncio
from datetime import datetime, timezone
import aiohttp
from database.inserting import store_event
from database.queries import event_exists
from api.ticketmaster import fetch_events_from_api
import logging

from config.config import (
    DISCORD_BOT_TOKEN,
    DISCORD_CHANNEL_ID,
    DISCORD_CHANNEL_ID_TWO,
    TICKETMASTER_API_KEY,
    REDIRECT_URI,
    DATABASE_URL,
    DEBUG,
)

logger = logging.getLogger(__name__)

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

    except Exception as e:
        logger.error(f"Unexpected error in fetch_events: {e}", exc_info=True)

async def process_event(event):
    """Check if an event exists and store it if not."""
    from config.db_pool import db_pool  # Import shared db_pool here

    try:
        async with db_pool.acquire() as conn:
            if not await event_exists(conn, event["id"]):
                logger.info(f"Storing new event: {event['id']} - {event['name']}")
                try:
                    await store_event(event)
                    logger.debug(f"Successfully stored event: {event['id']}")
                    return True  # New event added
                except Exception as e:
                    logger.error(f"Error storing event: {event['id']}, name: {event['name']}, error: {e}")
                    return False  # Failed to store event
            else:
                if DEBUG:
                    logger.debug(f"Event already exists in DB: {event['id']} - {event['name']}")
                return False  # Event already exists
    except Exception as e:
        logger.error(f"Failed to acquire DB connection for event: {event['id']}, error: {e}")
        return False  # Failed to process event