import discord
from discord.ext import commands, tasks
import requests
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve API keys from environment variables
TICKETMASTER_API_KEY = os.getenv('TICKETMASTER_API_KEY')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

if not TICKETMASTER_API_KEY or not DISCORD_BOT_TOKEN or not CHANNEL_ID:
    raise ValueError("Missing environment variables. Please check your .env file.")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize SQLite Database
conn = sqlite3.connect('events.db')
conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key support
c = conn.cursor()

# Drop tables if they exist to recreate schema
c.execute("DROP TABLE IF EXISTS Events")
c.execute("DROP TABLE IF EXISTS Venues")
c.execute("DROP TABLE IF EXISTS Artists")

# Create tables with the required structure
c.execute('''
CREATE TABLE IF NOT EXISTS Events (
    eventID TEXT PRIMARY KEY,
    name TEXT,
    artistID TEXT,
    venueID TEXT,
    eventDate TEXT,
    ticketOnsaleStart TEXT,
    sentToDiscord BOOLEAN DEFAULT 0,
    lastUpdated TEXT,
    FOREIGN KEY (artistID) REFERENCES Artists(artistID),
    FOREIGN KEY (venueID) REFERENCES Venues(venueID)
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS Venues (
    venueID TEXT PRIMARY KEY,
    name TEXT,
    city TEXT
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS Artists (
    artistID TEXT PRIMARY KEY,
    name TEXT,
    notable BOOLEAN
)
''')

# Add indexes for optimized querying
c.execute('''
CREATE INDEX IF NOT EXISTS idx_onsale_sent ON Events(ticketOnsaleStart, sentToDiscord);
''')

conn.commit()

def ensure_artist_exists(artist_id, artist_name):
    """Ensure the artist exists in the Artists table."""
    if artist_id is not None:
        c.execute('INSERT OR IGNORE INTO Artists (artistID, name, notable) VALUES (?, ?, ?)', (artist_id, artist_name, False))
        conn.commit()

def ensure_venue_exists(venue_id, venue_name, city):
    """Ensure the venue exists in the Venues table."""
    if venue_id is not None:
        c.execute('INSERT OR IGNORE INTO Venues (venueID, name, city) VALUES (?, ?, ?)', (venue_id, venue_name, city))
        conn.commit()

def store_event(event):
    """Store event in the database if not already present."""
    event_id = event['id']
    event_name = event['name']
    event_date = event['dates']['start']['localDate']
    onsale_start = event['sales']['public']['startDateTime']
    venue_data = event['_embedded']['venues'][0]
    venue_id = venue_data['id']
    venue_name = venue_data['name']
    venue_city = venue_data['city']['name']
    
    # Check if attractions (artists) data is available
    if 'attractions' in event['_embedded']:
        artist_id = event['_embedded']['attractions'][0]['id']
        artist_name = event['_embedded']['attractions'][0]['name']
    else:
        artist_id = None
        artist_name = None

    # Ensure the artist and venue exist
    ensure_artist_exists(artist_id, artist_name)
    ensure_venue_exists(venue_id, venue_name, venue_city)

    # Insert the event into the database with datetime as ISO 8601 strings
    c.execute('''
    INSERT OR IGNORE INTO Events (eventID, name, artistID, venueID, eventDate, ticketOnsaleStart, sentToDiscord, lastUpdated)
    VALUES (?, ?, ?, ?, ?, ?, 0, ?)
    ''', (event_id, event_name, artist_id, venue_id, event_date, onsale_start, datetime.now(timezone.utc).isoformat()))
    
    conn.commit()
    
def fetch_today_events():
    """Fetch events starting sales today from Ticketmaster and add them to the database."""
    today_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    events = []
    page = 0
    size = 199  # Maximum allowed size for one page
    total_events_received = 0
    already_seen_count = 0
    new_events_count = 0

    # Define base URL and parameters
    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    public_visibility_start_date = f"{today_date}T00:00:00Z"

    while True:
        params = {
            "apikey": TICKETMASTER_API_KEY,
            "onsaleOnAfterStartDate": today_date,               # Date filter for onsale events
            "countryCode": "US",                           # Restrict results to the US
            "size": size,                                  # Maximum results per page
            "page": page,                                  # Current page number
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Extract events from the response
            page_events = data.get("_embedded", {}).get("events", [])
            events.extend(page_events)
            total_events_received += len(page_events)

            # Pagination details
            pagination = data.get("page", {})
            total_pages = pagination.get("totalPages", 1)

            # Debugging output for each page
            print(f"Fetching page {page + 1}/{total_pages}, received {len(page_events)} events on this page.")

            # Exit the loop if all pages have been processed
            if page >= total_pages - 1 or page > 4:  # Adjust page limit if needed
                break

            # Move to the next page
            page += 1

        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            break

    # Process and store events
    for event in events:
        event_id = event['id']
        # Check if the event is already in the database
        c.execute("SELECT 1 FROM Events WHERE eventID = ?", (event_id,))
        if c.fetchone():
            already_seen_count += 1
        else:
            store_event(event)
            new_events_count += 1

    # Final debugging output
    print(f"Total events received across all pages: {total_events_received}")
    print(f"Events already seen in the database: {already_seen_count}")
    print(f"New events added to the database: {new_events_count}")  

@tasks.loop(minutes=1)
async def fetch_events_task():
    fetch_today_events()
    print("Today's events fetched and stored.")

@tasks.loop(minutes=1)  # Runs every minute
async def notify_events_task():
    now = datetime.now(timezone.utc)
    minute_ahead = now + timedelta(minutes=1)
    
    # Query events that are ready for notification
    c.execute('''
    SELECT eventID, name, ticketOnsaleStart, eventDate
    FROM Events
    WHERE sentToDiscord = 0 AND ticketOnsaleStart <= ?
    ''', (minute_ahead.isoformat(),))
    
    events_to_notify = c.fetchall()
    channel = bot.get_channel(CHANNEL_ID)

    if events_to_notify and channel:
        for event_id, name, onsale_start, event_date in events_to_notify:
            # Format and send message to Discord
            embed = discord.Embed(
                title=name,
                description=f"Event Date: {event_date}\nOnsale Start: {onsale_start}",
                color=discord.Color.blue()
            )
            await channel.send(embed=embed)
            # Mark event as sent
            c.execute("UPDATE Events SET sentToDiscord = 1 WHERE eventID = ?", (event_id,))
            conn.commit()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    fetch_events_task.start()
    notify_events_task.start()

if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)