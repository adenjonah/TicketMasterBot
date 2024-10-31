import requests
import sqlite3
import logging
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TICKETMASTER_API_KEY = os.getenv('TICKETMASTER_API_KEY')

# Set up database-specific logging
db_logger = logging.getLogger("dbLogger")
db_logger.setLevel(logging.INFO)
db_handler = logging.FileHandler("db_log.log")
db_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
db_logger.addHandler(db_handler)

# Connect to SQLite
conn = sqlite3.connect('events.db')
c = conn.cursor()

def initialize_db():
    """Create tables if they do not exist."""
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
        notable BOOLEAN
    )''')
    conn.commit()
    db_logger.info("Database initialized successfully.")

def fetch_today_events():
    """Fetches events from Ticketmaster and updates the database."""
    today_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    page = 0
    size = 199

    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {
        "apikey": TICKETMASTER_API_KEY,
        "onsaleOnStartDate": today_date,
        "countryCode": "US",
        "size": size,
        "page": page,
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        events = data.get("_embedded", {}).get("events", [])

        for event in events:
            store_event(event)
    except requests.exceptions.RequestException as e:
        db_logger.error(f"Error fetching events: {e}")

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
