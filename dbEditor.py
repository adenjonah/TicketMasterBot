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

now = datetime.now(timezone.utc)

# Load environment variables
load_dotenv()
TICKETMASTER_API_KEY = os.getenv('TICKETMASTER_API_KEY')
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
DATABASE_URL = os.getenv("DATABASE_URL")

async def get_db_connection():
    """Establish and return an async PostgreSQL connection."""
    return await asyncpg.connect(DATABASE_URL)

async def initialize_db():
    """Create tables if they do not exist and ensure schema compatibility."""
    print("Initializing the database...")
    conn = await get_db_connection()
    try:
        # Create tables with correct data types
        print("Creating tables if they do not exist...")
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS Events (
            eventID TEXT PRIMARY KEY,
            name TEXT,
            artistID TEXT,
            venueID TEXT,
            eventDate TIMESTAMPTZ,
            ticketOnsaleStart TIMESTAMPTZ,
            url TEXT,
            image_url TEXT,
            sentToDiscord BOOLEAN DEFAULT FALSE,
            lastUpdated TIMESTAMPTZ
        )''')
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS Venues (
            venueID TEXT PRIMARY KEY,
            name TEXT,
            city TEXT,
            state TEXT
        )''')
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS Artists (
            artistID TEXT PRIMARY KEY,
            name TEXT,
            notable BOOLEAN DEFAULT FALSE
        )''')
        print("Tables created successfully.")

        # Alter existing columns to TIMESTAMPTZ if necessary
        print("Altering Events table columns to TIMESTAMPTZ if necessary...")
        await conn.execute('''
        ALTER TABLE Events
        ALTER COLUMN eventDate TYPE TIMESTAMPTZ USING eventDate AT TIME ZONE 'UTC',
        ALTER COLUMN ticketOnsaleStart TYPE TIMESTAMPTZ USING ticketOnsaleStart AT TIME ZONE 'UTC',
        ALTER COLUMN lastUpdated TYPE TIMESTAMPTZ USING lastUpdated AT TIME ZONE 'UTC';
        ''')
        print("Database schema updated successfully.")

        # Load notable artist IDs from artist_ids.txt
        # ... rest of your existing code ...

    except Exception as e:
        print(f"Error during database initialization: {e}")
    finally:
        await conn.close()

async def fetch_events(bot):
    """Fetches events asynchronously from Ticketmaster API and handles errors."""
    print("Fetching events from Ticketmaster API...")
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    url = "https://app.ticketmaster.com/discovery/v2/events"
    page = 0
    max_pages = 5

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
                        await store_event(event)  # Ensure async compatibility
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

async def store_event(event):
    """Stores a new event in the database if not already present."""
    print(f"Storing event: {event['name']} (ID: {event['id']})")
    conn = await get_db_connection()

    try:
        # Extract event details
        event_id = event['id']
        event_name = event['name']
        event_date = parser.parse(event['dates']['start']['localDate']).astimezone(timezone.utc).replace(tzinfo=None)
        onsale_start = parser.parse(event['sales']['public']['startDateTime']).astimezone(timezone.utc).replace(tzinfo=None)
        last_updated = datetime.now(timezone.utc).replace(tzinfo=None)

        # Extract URL
        url = event.get('url', '')

        # Extract image URL (prefer high-resolution)
        image_url = next(
            (img['url'] for img in event.get('images', []) if img.get('width', 0) >= 1024),
            None
        )

        # Extract venue details
        venue_data = event['_embedded'].get('venues', [{}])[0]
        venue_id = venue_data.get('id')
        venue_name = venue_data.get('name', 'Unknown Venue')
        venue_city = venue_data.get('city', {}).get('name', 'Unknown City')
        venue_state = venue_data.get('state', {}).get('stateCode', 'Unknown State')

        # Extract artist details
        artist_data = event['_embedded'].get('attractions', [{}])[0]
        artist_id = artist_data.get('id')
        artist_name = artist_data.get('name', 'Unknown Artist')

        # Insert venue into the database
        await conn.execute(
            '''
            INSERT INTO Venues (venueID, name, city, state)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (venueID) DO NOTHING
            ''',
            venue_id, venue_name, venue_city, venue_state
        )
        print(f"Inserted/Updated venue: {venue_name} (ID: {venue_id})")

        # Insert artist into the database (if available)
        if artist_id:
            await conn.execute(
                '''
                INSERT INTO Artists (artistID, name, notable)
                VALUES ($1, $2, $3)
                ON CONFLICT (artistID) DO NOTHING
                ''',
                artist_id, artist_name, False
            )
            print(f"Inserted/Updated artist: {artist_name} (ID: {artist_id})")

        # Insert event into the database
        print(f"event_date: {event_date}, tzinfo: {event_date.tzinfo}")
        print(f"onsale_start: {onsale_start}, tzinfo: {onsale_start.tzinfo}")
        print(f"last_updated: {last_updated}, tzinfo: {last_updated.tzinfo}")
        
        await conn.execute(
            '''
            INSERT INTO Events (eventID, name, artistID, venueID, eventDate, ticketOnsaleStart, url, image_url, sentToDiscord, lastUpdated)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (eventID) DO NOTHING
            ''',
            event_id, event_name, artist_id, venue_id, event_date, onsale_start, url, image_url,
            False, last_updated
        )
        print(f"Event stored: {event_name} (ID: {event_id})")

        return True

    except Exception as e:
        print(f"Error storing event: {e}")
        return False

    finally:
        # Ensure connection is closed
        await conn.close()
         
async def notify_discord_error(bot, channel_id, error_message):
    """Send an error notification to a Discord channel."""
    channel = bot.get_channel(channel_id)
    if channel:
        embed = discord.Embed(
            title="Error Notification",
            description=error_message,
            color=discord.Color.red()
        )
        await channel.send(embed=embed)