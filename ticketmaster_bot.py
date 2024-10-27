import discord
from discord.ext import commands, tasks
import requests
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()
TICKETMASTER_API_KEY = os.getenv('TICKETMASTER_API_KEY')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

if not TICKETMASTER_API_KEY or not DISCORD_BOT_TOKEN or not CHANNEL_ID:
    raise ValueError("Missing environment variables. Please check your .env file.")

total_events_received = 0
already_seen_count = 0
new_events_count = 0

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

class EventBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.synced = False

    async def on_ready(self):
        if not self.synced:
            await bot.tree.sync()
            self.synced = True
        print(f'{self.user} has connected to Discord!')

bot = EventBot(command_prefix='!', intents=intents)

@bot.tree.command(name="data", description="Shows info on events received during the last ping")
async def data(interaction: discord.Interaction):
    response = (
        f"**Last Fetch Summary:**\n"
        f"Total events received: {total_events_received}\n"
        f"Events already in database: {already_seen_count}\n"
        f"New events added to database: {new_events_count}\n"
    )
    await interaction.response.send_message(response)

@bot.tree.command(name="future", description="Lists future events not yet sent to Discord with drop times")
async def future(interaction: discord.Interaction):
    now = datetime.now(timezone.utc)
    c.execute('''
    SELECT name, ticketOnsaleStart 
    FROM Events 
    WHERE sentToDiscord = 0 AND ticketOnsaleStart > ?
    ORDER BY ticketOnsaleStart ASC
    ''', (now.isoformat(),))
    future_events = c.fetchall()

    if future_events:
        response = "Upcoming Events:\n"
        for event in future_events:
            name, onsale_start = event
            onsale_datetime = datetime.strptime(onsale_start, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            time_diff = onsale_datetime - now
            days, remainder = divmod(time_diff.total_seconds(), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, _ = divmod(remainder, 60)
            if days > 0:
                net_time = f"{int(days)}d {int(hours)}hr {int(minutes)}min"
            elif hours > 0:
                net_time = f"{int(hours)}hr {int(minutes)}min"
            else:
                net_time = f"{int(minutes)}min"
            response += f"**{name}** - Sale Starts in {net_time}\n"
    else:
        response = "No future events scheduled."

    await interaction.response.send_message(response)
    

# Initialize SQLite Database
conn = sqlite3.connect('events.db')
conn.execute("PRAGMA foreign_keys = ON")
c = conn.cursor()

# KEEP THIS COMMENTED UNLESS DEBUGGING
# c.execute("DROP TABLE IF EXISTS Events")
# c.execute("DROP TABLE IF EXISTS Venues")
# c.execute("DROP TABLE IF EXISTS Artists")

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
    city TEXT,
    state TEXT 
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS Artists (
    artistID TEXT PRIMARY KEY,
    name TEXT,
    notable BOOLEAN
)
''')

c.execute('''
CREATE INDEX IF NOT EXISTS idx_onsale_sent ON Events(ticketOnsaleStart, sentToDiscord);
''')

conn.commit()

def ensure_artist_exists(artist_id, artist_name):
    """Ensure the artist exists in the Artists table."""
    if artist_id is not None:
        c.execute('INSERT OR IGNORE INTO Artists (artistID, name, notable) VALUES (?, ?, ?)', (artist_id, artist_name, False))
        conn.commit()

def ensure_venue_exists(venue_id, venue_name, city, state):
    """Ensure the venue exists in the Venues table, including city and state."""
    if venue_id is not None:
        c.execute('INSERT OR IGNORE INTO Venues (venueID, name, city, state) VALUES (?, ?, ?, ?)', (venue_id, venue_name, city, state))
        conn.commit()

def store_event(event):
    """Store event in the database if not already present."""
    event_id = event['id']
    event_name = event['name']
    event_date = event['dates']['start']['localDate']
    onsale_start = event['sales']['public']['startDateTime']
    url = event['url']

    image_url = None
    for image in event.get('images', []):
        if image.get('ratio') == '16_9' and image.get('width', 0) >= 1024:
            image_url = image['url']
            break

    if not image_url and event.get('images'):
        image_url = event['images'][0]['url']

    venue_data = event['_embedded']['venues'][0]
    venue_id = venue_data['id']
    venue_name = venue_data['name']
    venue_city = venue_data['city']['name']
    venue_state = venue_data['state']['stateCode']

    if 'attractions' in event['_embedded']:
        artist_id = event['_embedded']['attractions'][0]['id']
        artist_name = event['_embedded']['attractions'][0]['name']
    else:
        artist_id = None
        artist_name = None

    ensure_artist_exists(artist_id, artist_name)
    ensure_venue_exists(venue_id, venue_name, venue_city, venue_state)

    c.execute('''
    INSERT OR IGNORE INTO Events (eventID, name, artistID, venueID, eventDate, ticketOnsaleStart, url, image_url, sentToDiscord, lastUpdated)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
    ''', (event_id, event_name, artist_id, venue_id, event_date, onsale_start, url, image_url, datetime.now(timezone.utc).isoformat()))
    
    conn.commit()
    
def ensure_venue_exists(venue_id, venue_name, city, state):
    """Ensure the venue exists in the Venues table, including"""
    if venue_id is not None:
        c.execute('INSERT OR IGNORE INTO Venues (venueID, name, city, state) VALUES (?, ?, ?, ?)', (venue_id, venue_name, city, state))
        conn.commit()
    
def fetch_today_events():
    global total_events_received, already_seen_count, new_events_count
    
    today_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    events = []
    page = 0
    size = 199
    total_events_received = 0
    already_seen_count = 0
    new_events_count = 0

    url = "https://app.ticketmaster.com/discovery/v2/events.json"

    while True:
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
            
            page_events = data.get("_embedded", {}).get("events", [])
            events.extend(page_events)
            total_events_received += len(page_events)

            pagination = data.get("page", {})
            total_pages = pagination.get("totalPages", 1)

            print(f"Fetching page {page + 1}/{total_pages}, received {len(page_events)} events on this page.")

            if page >= total_pages - 1 or page == 5:
                break

            page += 1

        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            break

    for event in events:
        event_id = event['id']
        
        c.execute("SELECT 1 FROM Events WHERE eventID = ?", (event_id,))
        if c.fetchone():
            already_seen_count += 1
        else:
            store_event(event)
            new_events_count += 1

    print(f"Total events received across all pages: {total_events_received}")
    print(f"Events already seen in the database: {already_seen_count}")
    print(f"New events added to the database: {new_events_count}")
@tasks.loop(minutes=1)
async def fetch_events_task():
    fetch_today_events()
    print("Events fetched and stored.")

@tasks.loop(minutes=1)
async def notify_events_task():
    now = datetime.now(timezone.utc)
    minute_ahead = now + timedelta(minutes=1)
    
    c.execute('''
    SELECT Events.eventID, Events.name AS event_name, Events.ticketOnsaleStart, Events.eventDate, Events.url, 
           Venues.city, Venues.state, Events.image_url, Artists.name AS artist_name
    FROM Events
    LEFT JOIN Venues ON Events.venueID = Venues.venueID
    LEFT JOIN Artists ON Events.artistID = Artists.artistID
    WHERE Events.sentToDiscord = 0 AND Events.ticketOnsaleStart <= ?
    ''', (minute_ahead.isoformat(),))
    
    events_to_notify = c.fetchall()
    channel = bot.get_channel(CHANNEL_ID)

    if events_to_notify and channel:
        for event_id, event_name, onsale_start, event_date, url, city, state, image_url, artist_name in events_to_notify:
            formatted_event_date = datetime.strptime(event_date, "%Y-%m-%d").strftime("%B %-d, %Y")
            onsale_datetime = datetime.strptime(onsale_start, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            formatted_onsale_start = onsale_datetime.strftime("%B %-d, %Y %I:%M %p %Z").lstrip("0").replace(" 0", " ")

            time_diff = onsale_datetime - now
            if time_diff.total_seconds() > 0:
                days, remainder = divmod(time_diff.total_seconds(), 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes, _ = divmod(remainder, 60)
                if days > 0:
                    net_time = f"{int(days)}day {int(hours)}hr {int(minutes)}min from now" if hours or minutes else f"{int(days)} days from now"
                elif hours > 0:
                    net_time = f"{int(hours)}hr {int(minutes)}min from now" if minutes else f"{int(hours)}hr from now"
                else:
                    net_time = f"{int(minutes)}min from now"
            else:
                days, remainder = divmod(-time_diff.total_seconds(), 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes, _ = divmod(remainder, 60)
                if days > 0:
                    net_time = f"{int(days)}day {int(hours)}hr {int(minutes)}min ago" if hours or minutes else f"{int(days)} days ago"
                elif hours > 0:
                    net_time = f"{int(hours)}hr {int(minutes)}min ago" if minutes else f"{int(hours)}hr ago"
                else:
                    net_time = f"{int(minutes)}min ago"

            formatted_onsale_start_with_net_time = f"{formatted_onsale_start} ({net_time})"
            
            artist_info = f"**Artist**: {artist_name}\n" if artist_name else ""
            
            embed = discord.Embed(
                title=event_name,
                url=url,
                description=(
                    f"{artist_info}"
                    f"**Event Date**: {formatted_event_date}\n"
                    f"**Ticket Sale Start Date**: {formatted_onsale_start_with_net_time}\n"
                    f"**Location**: {city}, {state}"
                ),
                color=discord.Color.blue()
            )
            
            if image_url:
                embed.set_image(url=image_url)
            
            # embed.set_footer(text="Purchase Tickets Now!")
            
            await channel.send(embed=embed)
            
            c.execute("UPDATE Events SET sentToDiscord = 1 WHERE eventID = ?", (event_id,))
            conn.commit()
            
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    fetch_events_task.start()
    notify_events_task.start()

if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)