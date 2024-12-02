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
    logger.info("Fetching events from Ticketmaster API...")
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    page = 0
    max_pages = 5

    try:
        async with aiohttp.ClientSession() as session:
            while page < max_pages:
                logger.info(f"Fetching page {page + 1}...")
                if DEBUG:
                    logger.debug(f"Current time: {current_time}, Current date: {current_date}, Page: {page}")

                try:
                    events = await fetch_events_from_api(session, page, current_time, current_date)
                    logger.info(f"Page {page + 1}: Received {len(events)} events.")
                    
                    if DEBUG:
                        logger.debug(f"Fetched events data: {events[:2] if events else 'No events'} (showing first 2 if available)")
                    
                    # Collect tasks to manage concurrency
                    for event in events:
                        await process_event(event)

                    if DEBUG:
                        logger.debug(f"Completed processing tasks for page {page + 1}")

                    if len(events) < 199:
                        logger.info("No more events to fetch. Stopping.")
                        break
                except aiohttp.ClientError as e:
                    logger.error(f"Error fetching events on page {page + 1}: {e}")
                    if DEBUG:
                        logger.debug(f"ClientError details: {e}")
                    break

                page += 1
                if DEBUG:
                    logger.debug(f"Moving to the next page: {page}")
                await asyncio.sleep(1)  # Avoid hitting rate limits
    except Exception as e:
        logger.error(f"Unexpected error in fetch_events: {e}", exc_info=True)
        if DEBUG:
            logger.debug(f"Unhandled exception details: {e}")

async def process_event(event):
    """Check if an event exists and store it if not."""
    from config.db_pool import db_pool  # Import shared db_pool here

    async with db_pool.acquire() as conn:
        if not await event_exists(conn, event["id"]):
            await store_event(event)
        else:
            logger.debug(f"Event id \"{event["id"]}\" already in DB")