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

# Recreate the Events table with url and image_url columns
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

# Adjust store_event to save the url and image_url for each event
def store_event(event):
    """Store event in the database if not already present."""
    event_id = event['id']
    event_name = event['name']
    event_date = event['dates']['start']['localDate']
    onsale_start = event['sales']['public']['startDateTime']
    url = event['url']  # Get the event URL
    
    # Select a suitable image URL (16:9, at least 1024px wide)
    image_url = None
    for image in event.get('images', []):
        if image['ratio'] == '16_9' and image['width'] >= 1024:
            image_url = image['url']
            break

    # Fallback in case no 16:9, 1024px image is found
    if not image_url and event.get('images'):
        image_url = event['images'][0]['url']  # Use the first available image

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

    # Insert the event into the database with all details
    c.execute('''
    INSERT OR IGNORE INTO Events (eventID, name, artistID, venueID, eventDate, ticketOnsaleStart, url, image_url, sentToDiscord, lastUpdated)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
    ''', (event_id, event_name, artist_id, venue_id, event_date, onsale_start, url, image_url, datetime.now(timezone.utc).isoformat()))
    
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

    while True:
        params = {
            "apikey": TICKETMASTER_API_KEY,
            "onsaleOnStartDate": today_date,               # Date filter for onsale events
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
            if page >= total_pages - 1 or page == 5:  # Adjust page limit if needed
                break

            # Move to the next page
            page += 1

        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            break

   # Process and store events, artists, and venues
    for event in events:
        event_id = event['id']
        # Check if the event is already in the database
        c.execute("SELECT 1 FROM Events WHERE eventID = ?", (event_id,))
        if c.fetchone():
            already_seen_count += 1
        else:
            # Process and add artist
            artist_id = None
            if 'attractions' in event['_embedded']:
                artist_data = event['_embedded']['attractions'][0]
                artist_id = artist_data['id']
                artist_name = artist_data['name']
                notable = artist_data.get('classifications', [{}])[0].get('segment', {}).get('name') == 'Notable'

                # Add artist if not in the database
                c.execute("INSERT OR IGNORE INTO Artists (artistID, name, notable) VALUES (?, ?, ?)", (artist_id, artist_name, notable))

            # Process and add venue
            venue_data = event['_embedded']['venues'][0]
            venue_id = venue_data['id']
            venue_name = venue_data['name']
            city = venue_data['city']['name']

            # Add venue if not in the database
            c.execute("INSERT OR IGNORE INTO Venues (venueID, name, city) VALUES (?, ?, ?)", (venue_id, venue_name, city))

            # Process and add event
            event_name = event['name']
            event_date = event['dates']['start']['localDate']
            ticket_onsale_start = event['sales']['public']['startDateTime']
            last_updated = datetime.now(timezone.utc).isoformat()

            # Add event to the database
            c.execute('''
                INSERT INTO Events (eventID, name, artistID, venueID, eventDate, ticketOnsaleStart, sentToDiscord, lastUpdated)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            ''', (event_id, event_name, artist_id, venue_id, event_date, ticket_onsale_start, last_updated))
            
            new_events_count += 1

    # Final debugging output
    print(f"Total events received across all pages: {total_events_received}")
    print(f"Events already seen in the database: {already_seen_count}")
    print(f"New events added to the database: {new_events_count}")  

@tasks.loop(minutes=1)
async def fetch_events_task():
    fetch_today_events()
    print("Events fetched and stored.")

@tasks.loop(minutes=1)  # Runs every minute
async def notify_events_task():
    now = datetime.now(timezone.utc)
    minute_ahead = now + timedelta(minutes=1)
    
    # Query events that are ready for notification
    c.execute('''
    SELECT Events.eventID, Events.name AS event_name, Events.ticketOnsaleStart, Events.eventDate, Events.url, Venues.city, Events.image_url
    FROM Events
    JOIN Venues ON Events.venueID = Venues.venueID
    WHERE Events.sentToDiscord = 0 AND Events.ticketOnsaleStart <= ?
    ''', (minute_ahead.isoformat(),))
    
    events_to_notify = c.fetchall()
    channel = bot.get_channel(CHANNEL_ID)

    if events_to_notify and channel:
        for event_id, event_name, onsale_start, event_date, url, city, image_url in events_to_notify:
            # Create the embed with event details
            embed = discord.Embed(
                title=event_name,
                url=url,  # Adds a clickable link to the title
                description=f"**Date**: {event_date}\n**Onsale Start**: {onsale_start}\n**City**: {city}",
                color=discord.Color.blue()
            )
            
            # Set the main image if available
            if image_url:
                embed.set_image(url=image_url)
            
            # Add footer and author details
            embed.set_footer(text="Don't miss out! Get your tickets now.")
            
            # Send the embed message to the channel
            await channel.send(embed=embed)
            
            # Mark the event as sent in the database
            c.execute("UPDATE Events SET sentToDiscord = 1 WHERE eventID = ?", (event_id,))
            conn.commit()
            
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    fetch_events_task.start()
    notify_events_task.start()

if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)