import requests
import sqlite3
import logging
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
import discord

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

def initialize_db():
    """Create tables if they do not exist and add notable artists from artist_ids_output.txt."""
    # Create tables
    c.execute('''
    CREATE TABLE IF NOT EXISTS Events (
        eventID TEXT PRIMARY KEY,
        name TEXT,
        artistID TEXT,
        venueID TEXT,
        eventDate TEXT,
        ticketOnsaleStart TEXT,
        url TEXT,
        image_url TEXT,
        sentToDiscord BOOLEAN DEFAULT 0,
        lastUpdated TEXT
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS Venues (
        venueID TEXT PRIMARY KEY,
        name TEXT,
        city TEXT,
        state TEXT
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS Artists (
        artistID TEXT PRIMARY KEY,
        name TEXT,
        notable BOOLEAN DEFAULT 0
    )''')
    conn.commit()
    db_logger.info("Database initialized successfully.")

    # Load notable artist IDs from artist_ids.txt
    try:
        with open("artist_ids.txt", "r") as f:
            for line in f:
                # Check for the expected line format with 'Original ID:', 'Name:', and 'API ID:'
                if "Original ID:" in line and "Name:" in line and "API ID:" in line:
                    # Split the line by separators to extract values
                    original_id_part = line.split("Original ID:")[1].split(" - ")[0].strip()
                    name_part = line.split("Name:")[1].split("|")[0].strip()
                    api_id_part = line.split("API ID:")[1].strip()

                    # Insert parsed data into the Artists table
                    c.execute('INSERT OR IGNORE INTO Artists (artistID, name, notable) VALUES (?, ?, ?)',
                            (api_id_part, name_part, 1))  # 'artistID' is the API ID, 'name' is the artist name
                    
                    # Log successful insertion
                    db_logger.info(f"Added notable artist '{name_part}' with API ID '{api_id_part}' to the database.")
                else:
                    # Log if the line does not match the expected format
                    db_logger.warning(f"Line did not match expected format: {line.strip()}")

        # Commit all changes to the database
        conn.commit()
        db_logger.info("Completed adding notable artists from artist_ids.txt to the database.")
    except FileNotFoundError:
        db_logger.error("File artist_ids.txt not found.")


async def fetch_events(bot, channel_id):
    """Fetches events from Ticketmaster and handles errors by sending messages to Discord."""
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    url = "https://app.ticketmaster.com/discovery/v2/events"
    page = 0
    total_events_available = 0
    max_pages = 5
    total_new_events = 0

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
            "onsaleOnAfterStartDate": current_date
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if page == 0:
                # Set total events available only on the first page request
                total_events_available = data.get("page", {}).get("totalElements", 0)
                
                # Stop fetching if there are too many events
                if total_events_available > 999:
                    error_message = "⚠️ Error: Total events available exceed 999. Stopping further requests."
                    await notify_discord_error(bot, DISCORD_CHANNEL_ID, error_message)
                    return  # Stop further processing

            events = data.get("_embedded", {}).get("events", [])
            received_events_count = len(events)
            new_events_count = 0

            for event in events:
                if store_event(event):
                    new_events_count += 1

            total_new_events += new_events_count

            # Log request details for each page
            api_logger.info(f"Page {page + 1}: Total possible events = {total_events_available}, "
                            f"Received = {received_events_count}, New events added = {new_events_count}")

            # Stop fetching if there are no more events
            if received_events_count < 199:
                break

        except requests.exceptions.RequestException as e:
            error_message = f"⚠️ Error fetching events on page {page + 1}: {e}"
            await notify_discord_error(bot, DISCORD_CHANNEL_ID, error_message)
            break  # Stop further processing on error

        # Move to the next page
        page += 1

    # Log the final summary after fetching all pages
    api_logger.info(f"Completed fetching events. Total possible events = {total_events_available}, "
                    f"Total new events added = {total_new_events}")


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

    # Insert venue data
    c.execute('INSERT OR IGNORE INTO Venues (venueID, name, city, state) VALUES (?, ?, ?, ?)',
              (venue_id, venue_name, venue_city, venue_state))
    conn.commit()
    db_logger.info(f"Venue '{venue_name}' added to database with city '{venue_city}' and state '{venue_state}'.")

    # Insert artist data if available
    if artist_id:
        c.execute('INSERT OR IGNORE INTO Artists (artistID, name, notable) VALUES (?, ?, ?)',
                  (artist_id, artist_name, False))
        conn.commit()
        db_logger.info(f"Artist '{artist_name}' added to database.")

    # Insert event data
    c.execute('INSERT OR IGNORE INTO Events (eventID, name, artistID, venueID, eventDate, ticketOnsaleStart, url, image_url, sentToDiscord, lastUpdated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)',
              (event_id, event_name, artist_id, venue_id, event_date, onsale_start, url, image_url, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    db_logger.info(f"Event '{event_name}' added to database.")
