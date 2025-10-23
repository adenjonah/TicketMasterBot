import aiohttp  # New import for async HTTP requests
import sqlite3
import logging
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
import discord
import asyncio  # Required for async database transactions if needed

# Load environment variables
load_dotenv()
TICKETMASTER_API_KEY = os.getenv('TICKETMASTER_API_KEY')
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

# Set up database-specific logging
db_logger = logging.getLogger("dbLogger")
db_logger.setLevel(logging.INFO)
db_handler = logging.FileHandler("logs/db_log.log")
db_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
db_logger.addHandler(db_handler)

# Set up API-specific logging
api_logger = logging.getLogger("apiLogger")
api_logger.setLevel(logging.INFO)
api_handler = logging.FileHandler("logs/api_log.log")
api_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
api_logger.addHandler(api_handler)

# Connect to SQLite
conn = sqlite3.connect('events.db')
c = conn.cursor()

def _load_notable_artists():
    """Load notable artist IDs from artist_ids.txt file."""
    try:
        with open("artist_ids.txt", "r") as f:
            for line in f:
                if "Original ID:" in line and "Name:" in line and "API ID:" in line:
                    original_id_part = line.split("Original ID:")[1].split(" - ")[0].strip()
                    name_part = line.split("Name:")[1].split("|")[0].strip()
                    api_id_part = line.split("API ID:")[1].strip()
                    c.execute('INSERT OR IGNORE INTO Artists (artistID, name, notable) VALUES (?, ?, ?)',
                            (api_id_part, name_part, 1))
                    db_logger.info(f"Added notable artist '{name_part}' with API ID '{api_id_part}'.")
                else:
                    db_logger.warning(f"Line did not match expected format: {line.strip()}")
        conn.commit()
        db_logger.info("Completed adding notable artists from artist_ids.txt.")
    except FileNotFoundError:
        db_logger.error("File artist_ids.txt not found.")

def initialize_db():
    """Create tables if they do not exist and add notable artists from artist_ids_output.txt."""
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS Events (
        eventID TEXT PRIMARY KEY, name TEXT, artistID TEXT, venueID TEXT,
        eventDate TEXT, ticketOnsaleStart TEXT, url TEXT, image_url TEXT,
        sentToDiscord BOOLEAN DEFAULT 0, lastUpdated TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Venues (
        venueID TEXT PRIMARY KEY, name TEXT, city TEXT, state TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Artists (
        artistID TEXT PRIMARY KEY, name TEXT, notable BOOLEAN DEFAULT 0)''')
    conn.commit()
    db_logger.info("Database initialized successfully.")

    # Add VF-related columns to Events table if missing
    try:
        c.execute("PRAGMA table_info(Events)")
        existing_columns = {row[1] for row in c.fetchall()}
        vf_columns = [("hasVF", "INTEGER DEFAULT 0"), ("vfUrl", "TEXT"), ("vfDetectedAt", "TEXT")]
        for col_name, col_type in vf_columns:
            if col_name not in existing_columns:
                c.execute(f"ALTER TABLE Events ADD COLUMN {col_name} {col_type}")
                db_logger.info(f"Added column {col_name} to Events table.")
        c.execute("CREATE INDEX IF NOT EXISTS idx_events_hasVF ON Events(hasVF)")
        conn.commit()
    except sqlite3.Error as e:
        db_logger.error(f"Failed to migrate Events table for VF columns: {e}")

    _load_notable_artists()


async def fetch_events(bot):
    """Fetches events asynchronously from Ticketmaster API and handles errors."""
    now_utc = datetime.now(timezone.utc)
    current_time, current_date = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"), now_utc.strftime("%Y-%m-%d")
    url = "https://app.ticketmaster.com/discovery/v2/events"
    page, total_events_available, max_pages, total_new_events = 0, 0, 5, 0

    async with aiohttp.ClientSession() as session:
        while page < max_pages:
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

                    if page == 0:
                        total_events_available = data.get("page", {}).get("totalElements", 0)
                        if total_events_available > 999:
                            error_message = "Error: Total events exceed 999. Stopping further requests."
                            await notify_discord_error(bot, DISCORD_CHANNEL_ID, error_message)
                            return

                    events = data.get("_embedded", {}).get("events", [])
                    received_events_count = len(events)
                    new_events_count = sum(1 for event in events if store_event(event))
                    total_new_events += new_events_count
                    
                    api_logger.info(f"Page {page + 1}: Total={total_events_available}, "
                                    f"Received={received_events_count}, New={new_events_count}")
                    if received_events_count < 199:
                        break

            except aiohttp.ClientError as e:
                error_message = f"Error fetching events on page {page + 1}: {e}"
                await notify_discord_error(bot, DISCORD_CHANNEL_ID, error_message)
                print(error_message)
                break

            page += 1

    api_logger.info(f"Completed fetching events. Total possible = {total_events_available}, "
                    f"New events added = {total_new_events}")

async def notify_discord_error(bot, channel_id, error_message):
    """Send an error notification to a Discord channel."""
    channel = bot.get_channel(channel_id)
    if channel:
        embed = discord.Embed(title="Error Notification", description=error_message, color=discord.Color.red())
        await channel.send(embed=embed)
    api_logger.error(error_message)

def store_event(event):
    """Stores a new event in the database if not already present, and ensures venue and artist data are updated."""
    event_id = event['id']
    event_name = event['name']
    event_date = event['dates']['start']['localDate']
    onsale_start = event['sales']['public']['startDateTime']
    url = event['url']

    # Handle images
    image_url = next((img['url'] for img in event.get('images', []) if img.get('width', 0) >= 1024), None)

    # Handle venue data
    venue_data = event['_embedded']['venues'][0]
    venue_id = venue_data['id']
    venue_name = venue_data['name']
    venue_city = venue_data['city']['name']
    venue_state = venue_data['state']['stateCode']

    # Handle artist data
    artist_data = event['_embedded'].get('attractions', [{}])[0]
    artist_id = artist_data.get('id')
    artist_name = artist_data.get('name')

    # Insert venue and artist data
    c.execute('INSERT OR IGNORE INTO Venues (venueID, name, city, state) VALUES (?, ?, ?, ?)',
              (venue_id, venue_name, venue_city, venue_state))
    if artist_id:
        c.execute('INSERT OR IGNORE INTO Artists (artistID, name, notable) VALUES (?, ?, ?)',
                  (artist_id, artist_name, False))
    conn.commit()
    db_logger.info(f"Venue '{venue_name}' ({venue_city}, {venue_state})" + 
                   (f" and artist '{artist_name}'" if artist_id else "") + " processed.")

    # Insert event data
    c.execute('INSERT OR IGNORE INTO Events (eventID, name, artistID, venueID, eventDate, ticketOnsaleStart, url, image_url, sentToDiscord, lastUpdated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)',
              (event_id, event_name, artist_id, venue_id, event_date, onsale_start, url, image_url, datetime.now(timezone.utc).isoformat()))
    
    # Check if a new row was inserted
    is_new_event = c.rowcount > 0
    conn.commit()
    
    if is_new_event:
        db_logger.info(f"Event '{event_name}' added to database.")
        
        # Queue VF detection for this new event (backwards compatible - won't crash if vf_checker unavailable)
        try:
            from vf_checker import schedule_vf_check_for_new_event
            schedule_vf_check_for_new_event(event_id, url, artist_name or event_name)
        except ImportError:
            db_logger.debug("VF checker module not available, skipping VF detection")
        except Exception as e:
            db_logger.error(f"Failed to queue VF detection for event {event_id}: {e}")
    
    return is_new_event