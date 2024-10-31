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
    """Create tables if they do not exist and add notable artists."""
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

    # List of notable artist IDs
    notable_artist_ids = [
        "1094215", "1159272", "2453935", "2811359", "1508961", "2404695", "3168081", "3103513",
        "3251698", "731454", "806431", "766720", "806203", "3184880", "807367", "770768", "1435919",
        "2222681", "2892837", "2782189", "1957114", "736262", "2150342", "1020885", "2253625",
        "2288122", "734977", "3175130", "1567745", "2625223", "1747243", "1788754", "2001092",
        "2257710", "772848", "735647", "1997046", "798903", "777416", "766722", "2880729", "2903928",
        "1833710", "2194218", "2119390", "2131374", "768018", "2730221", "718655", "2300002",
        "2818001", "2869566", "767870", "712214", "2826519", "2397430", "2075742", "862453", "703831",
        "2712573", "775700", "1113792", "847841", "1057637", "2663489", "863832", "1148845", "2194370",
        "3164506", "847492", "2431961", "803682", "2660883", "2182670", "732705", "767989", "1429693",
        "1646704", "2998425", "1536543", "2514177", "779049", "111163", "1896592", "1580836", "3178720",
        "1904831", "2282847", "2895379", "1638380", "735392", "755226", "2733829", "726146", "2499958",
        "2590072", "2110227", "2281371", "942726", "2842518", "1542376", "1319618", "1266616", "1871860",
        "1506392", "1983434", "1013826", "3008978", "2555869", "3109542", "1244865", "2543736", "806762",
        "773309", "3297169", "2433469", "836902", "1114794"
    ]

    # Insert notable artists
    for artist_id in notable_artist_ids:
        try:
            c.execute('INSERT OR IGNORE INTO Artists (artistID, name, notable) VALUES (?, ?, ?)',
                      (artist_id, None, 1))  # 'name' is set to None as we don't have names
            db_logger.info(f"Added notable artist with ID '{artist_id}' to the database.")
        except sqlite3.Error as e:
            db_logger.error(f"Failed to add notable artist with ID '{artist_id}': {e}")
    
    conn.commit()
    db_logger.info(f"Completed adding {len(notable_artist_ids)} notable artists to the database.")

# def fetch_today_events():
#     """Fetches events from Ticketmaster using specified filters and updates the database."""
#     # Get the current UTC date and time for parameters
#     current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
#     current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

#     # Define the API URL and parameters
#     url = "https://app.ticketmaster.com/discovery/v2/events"
#     params = {
#         "apikey": TICKETMASTER_API_KEY,
#         "source": "ticketmaster",
#         "locale": "*",
#         "size": 199,
#         "onsaleStartDateTime": current_time,
#         "countryCode": "US",
#         "classificationId": "KZFzniwnSyZfZ7v7nJ",
#         "onsaleOnAfterStartDate": current_date
#     }

#     try:
#         response = requests.get(url, params=params)
#         response.raise_for_status()
#         data = response.json()
#         events = data.get("_embedded", {}).get("events", [])

#         for event in events:
#             store_event(event)
#     except requests.exceptions.RequestException as e:
#         db_logger.error(f"Error fetching events: {e}")

def fetch_today_events():
    """Fetches all events from Madison Square Garden with specific classificationId, size, and source."""
    # Define the API URL and parameters
    url = "https://app.ticketmaster.com/discovery/v2/events"
    params = {
        "apikey": TICKETMASTER_API_KEY,
        "venueId": "KovZpZA7AAEA",              # Madison Square Garden venue ID
        "classificationId": "KZFzniwnSyZfZ7v7nJ", # Specific classification ID
        "size": 199,                              # Max size of each response page
        "source": "ticketmaster"                  # Source filter for ticketmaster
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        events = data.get("_embedded", {}).get("events", [])

        for event in events:
            store_event(event)
    except requests.exceptions.RequestException as e:
        db_logger.error(f"Error fetching events for Madison Square Garden with classificationId: {e}")

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
