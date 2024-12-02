import aiohttp  # For async HTTP requests
import psycopg2
import discord
from psycopg2.extras import DictCursor
import logging
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
import asyncpg
from dateutil import parser
import asyncio
from config.config import (
    DISCORD_BOT_TOKEN,
    DISCORD_CHANNEL_ID,
    DISCORD_CHANNEL_ID_TWO,
    TICKETMASTER_API_KEY,
    REDIRECT_URI,
    DATABASE_URL,
    DEBUG,
)

now = datetime.now(timezone.utc)

async def fetch_events(bot):
    """Fetches events asynchronously from Ticketmaster API and handles errors."""
    print("Fetching events from Ticketmaster API...")
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    url = "https://app.ticketmaster.com/discovery/v2/events"
    page = 0
    max_pages = 5

    # Establish a database connection
    conn = await get_db_connection()

    try:
        async with aiohttp.ClientSession() as session:
            while page < max_pages:
                print(f"Fetching page {page + 1}...")
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

                try:
                    async with session.get(url, params=params) as response:
                        response.raise_for_status()
                        data = await response.json()

                        events = data.get("_embedded", {}).get("events", [])
                        print(f"Page {page + 1}: Received {len(events)} events.")

                    for event in events:
                        event_exists = await conn.fetchval(
                            '''
                            SELECT 1 FROM Events WHERE eventID = $1
                            ''',
                            event["id"]
                        )
                        if not event_exists:
                            # Event is not in the database, store it
                            await store_event(event)
                        else:
                            # Event already exists, skip
                            print(f"Event already exists: {event['name']} (ID: {event['id']})")

                        await asyncio.sleep(0)  # Yield control back to the loop

                        # Stop fetching if fewer events than page size
                        if len(events) < 199:
                            print("No more events to fetch. Stopping.")
                            break

                except aiohttp.ClientError as e:
                    error_message = f"Error fetching events on page {page + 1}: {e}"
                    await notify_discord_error(bot, DISCORD_CHANNEL_ID, error_message)
                    print(error_message)
                    break

                # Move to the next page
                page += 1
                await asyncio.sleep(1)  # Avoid hitting rate limits
    except Exception as e:
        print(f"Unexpected error in fetch_events: {e}")
    finally:
        # Close the database connection
        await conn.close()
 
  
async def fetch_events_from_api(session, page, current_time, current_date):
    """Fetch events from the Ticketmaster API."""
    url = "https://app.ticketmaster.com/discovery/v2/events"
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
    async with session.get(url, params=params) as response:
        response.raise_for_status()
        data = await response.json()
        return data.get("_embedded", {}).get("events", [])
    
async def process_event(conn, event):
    """Check if an event exists and store it if not."""
    event_exists = await conn.fetchval(
        '''
        SELECT 1 FROM Events WHERE eventID = $1
        ''',
        event["id"]
    )
    if not event_exists:
        await store_event(event)
    else:
        print(f"Event already exists: {event['name']} (ID: {event['id']})")