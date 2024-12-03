import aiohttp  # For async HTTP requests
import discord
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from dateutil import parser
import asyncio
import urllib.parse
from config.logging import logger
import urllib.parse  # Import for URL encoding

from config.config import (
    DISCORD_BOT_TOKEN,
    DISCORD_CHANNEL_ID,
    DISCORD_CHANNEL_ID_TWO,
    TICKETMASTER_API_KEY,
    DATABASE_URL,
    DEBUG,
)

now = datetime.now(timezone.utc)

async def fetch_events_from_api(session, page, current_time, current_date):
    """Fetch events from the Ticketmaster API."""
    base_url = "https://app.ticketmaster.com/discovery/v2/events"
    params = {
        "apikey": TICKETMASTER_API_KEY,
        "source": "ticketmaster",
        "locale": "*",
        "size": 199,
        "page": page,
        "onsaleStartDateTime": current_time,
        "countryCode": "US",
        "classificationId": "KZFzniwnSyZfZ7v7nJ",
        "onsaleOnAfterStartDate": current_date,
        "sort": "onSaleStartDate,asc"
    }

    # Construct the full URL with encoded parameters
    full_url = f"{base_url}?{urllib.parse.urlencode(params)}"

    logger.info(f"Request made to {full_url}")
    async with session.get(full_url) as response:
        try:
            response.raise_for_status()
            data = await response.json()
            logger.debug(f"Response data (first 500 chars): {str(data)[:500]}")
            return data.get("_embedded", {}).get("events", [])
        except Exception as e:
            logger.error(f"Error fetching data from {full_url}: {e}")
            raise


async def process_event(event):
    """Check if an event exists and store it if not."""
    from config.db_pool import db_pool  # Ensure the pool is initialized during runtime

    logger.debug(f"Processing event: {event['name']} (ID: {event['id']})")

    try:
        async with db_pool.acquire() as conn:
            event_exists = await conn.fetchval(
                '''
                SELECT 1 FROM Events WHERE eventID = $1
                ''',
                event["id"]
            )
            if not event_exists:
                logger.info(f"Storing new event: {event['id']} - {event['name']}")
                try:
                    await store_event(event, conn)
                    logger.debug(f"Successfully stored event: {event['id']} - {event['name']}")
                except Exception as e:
                    logger.error(f"Error storing event: {event['id']}, name: {event['name']}, error: {e}")
            else:
                logger.debug(f"Event already exists in DB: {event['id']} - {event['name']}")
    except Exception as e:
        logger.error(f"Failed to acquire DB connection for event: {event['id']}, name: {event['name']}, error: {e}")