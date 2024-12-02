import asyncio
from datetime import datetime, timezone
import aiohttp
from database.inserting import store_event
from database.queries import event_exists
from api.ticketmaster import fetch_events_from_api
import logging

logger = logging.getLogger(__name__)

async def fetch_events(bot, db_pool):
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
                try:
                    events = await fetch_events_from_api(session, page, current_time, current_date)
                    logger.info(f"Page {page + 1}: Received {len(events)} events.")
                    
                    # Collect tasks to manage concurrency
                    tasks = [process_event(db_pool, event) for event in events]
                    await asyncio.gather(*tasks)  # Process all events concurrently
                    
                    if len(events) < 199:
                        logger.info("No more events to fetch. Stopping.")
                        break
                except aiohttp.ClientError as e:
                    logger.error(f"Error fetching events on page {page + 1}: {e}")
                    break

                page += 1
                await asyncio.sleep(1)  # Avoid hitting rate limits
    except Exception as e:
        logger.error(f"Unexpected error in fetch_events: {e}", exc_info=True)

async def process_event(db_pool, event):
    """Check if an event exists and store it if not."""
    async with db_pool.acquire() as conn:
        if not await event_exists(conn, event["id"]):
            await store_event(event, db_pool)