import discord
from discord.ext import commands, tasks
import requests
import os
import sqlite3
from datetime import datetime, timezone
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
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS seen_events (event_id TEXT PRIMARY KEY)''')
conn.commit()

def event_seen(event_id):
    c.execute("SELECT 1 FROM seen_events WHERE event_id = ?", (event_id,))
    return c.fetchone() is not None

def mark_event_seen(event_id):
    c.execute("INSERT INTO seen_events (event_id) VALUES (?)", (event_id,))
    conn.commit()

def get_all_events(onsale_start_date):
    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    
    # Initialize pagination variables
    events = []
    page = 0
    size = 199  # Maximum allowed size for one page

    # Create the publicVisibilityStartDateTime dynamically based on onsale_start_date
    public_visibility_start_date = f"{onsale_start_date}T00:00:00Z"

    while True:
        params = {
            "apikey": TICKETMASTER_API_KEY,
            "onsaleOnStartDate": onsale_start_date,  # Filter events with onsale starting on this date
            "countryCode": "US",                    # Filter events only in the US
            # "publicVisibilityStartDateTime": public_visibility_start_date,  # IDK if we want this bc we miss like 200 events that were visible before
            "size": size,                            # Limit to maximum 199 results per page
            "page": page,                            # Current page number
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Extract events from the response
            page_events = data.get("_embedded", {}).get("events", [])
            events.extend(page_events)
            
            # Extract pagination details
            pagination = data.get("page", {})
            total_pages = pagination.get("totalPages", 1)

            # If we've processed all pages, break the loop
            if page >= total_pages - 1 or page > 4:
                break

            # Move to the next page
            page += 1

        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            break

    return events

@tasks.loop(minutes=1)
async def check_for_new_events():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f"Error: Could not find channel with ID {CHANNEL_ID}")
        return

    # Get today's date to filter events that are on sale today
    onsale_start_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    events = get_all_events(onsale_start_date)
    
    total_events = len(events)
    seen_events_count = 0
    new_events = []
    
    for event in events:
        event_id = event['id']
        if event_seen(event_id):
            seen_events_count += 1
        else:
            mark_event_seen(event_id)  # Mark this event as seen
            new_events.append(event)
    
    new_events_count = len(new_events)

    # Print summary to terminal
    print(f"Total events received: {total_events}")
    print(f"Events already seen: {seen_events_count}")
    print(f"New events: {new_events_count}")
    
    if new_events:
        for event in new_events:
            # Get sale start and end dates if available
            sales_start = event.get('sales', {}).get('public', {}).get('startDateTime', 'Unknown')
            sales_end = event.get('sales', {}).get('public', {}).get('endDateTime', 'Unknown')
            
            # Format the sales times into something more readable
            sales_start = datetime.strptime(sales_start, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S") if sales_start != 'Unknown' else 'Unknown'
            sales_end = datetime.strptime(sales_end, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S") if sales_end != 'Unknown' else 'Unknown'
            
            embed = discord.Embed(
                title=event['name'],
                url=event['url'],
                description=f"Date: {event['dates']['start']['localDate']}\n"
                            f"Ticket Sales Start: {sales_start}\n"
                            f"Ticket Sales End: {sales_end}",
                color=discord.Color.blue()
            )
            if 'images' in event and event['images']:
                embed.set_thumbnail(url=event['images'][0]['url'])
            await channel.send(embed=embed)
    else:
        print("No new events found.")

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    check_for_new_events.start()

@bot.command(name='events')
async def list_events(ctx):
    # Get today's date to filter events that are on sale today
    onsale_start_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    events = get_all_events(onsale_start_date)
    
    if not events:
        await ctx.send("No events with today's onsale date found.")
        return

    for event in events[:5]:  # Limit to 5 events to avoid flooding the channel
        # Get sale start and end dates if available
        sales_start = event.get('sales', {}).get('public', {}).get('startDateTime', 'Unknown')
        sales_end = event.get('sales', {}).get('public', {}).get('endDateTime', 'Unknown')

        # Format the sales times into something more readable
        sales_start = datetime.strptime(sales_start, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S") if sales_start != 'Unknown' else 'Unknown'
        sales_end = datetime.strptime(sales_end, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S") if sales_end != 'Unknown' else 'Unknown'
        
        embed = discord.Embed(
            title=event['name'],
            url=event['url'],
            description=f"Date: {event['dates']['start']['localDate']}\n"
                        f"Ticket Sales Start: {sales_start}\n"
                        f"Ticket Sales End: {sales_end}",
            color=discord.Color.green()
        )
        if 'images' in event and event['images']:
            embed.set_thumbnail(url=event['images'][0]['url'])
        await ctx.send(embed=embed)

    if len(events) > 5:
        await ctx.send(f"And {len(events) - 5} more events...")

if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)

