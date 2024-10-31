import discord
from discord.ext import commands
import sqlite3
import logging
from collections import deque
from datetime import datetime, timedelta, timezone
import aiohttp
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TICKETMASTER_API_KEY = os.getenv('TICKETMASTER_API_KEY')
DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

# Ticketmaster API Key
API_KEY = TICKETMASTER_API_KEY
# Set up intents
intents = discord.Intents.default()
intents.message_content = True

# Initialize bot with intents
bot = commands.Bot(command_prefix="!", intents=intents, case_insensitive=True)

# Log file paths
LOG_FILES = {
    "eventlog": "logs/event_log.log",
    "dblog": "logs/db_log.log",
    "messagelog": "logs/message_log.log",
    "apilog": "logs/api_log.log"
}

# SQLite database connection
conn = sqlite3.connect('events.db')
c = conn.cursor()

import discord
from discord.ext import commands
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, filename="logs/event_log.log", filemode="a",
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("commandHandler")

# Available commands
COMMAND_LIST = (
    "**!eventlog** - Displays the last 20 lines of the event log.\n"
    "**!dblog** - Displays the last 20 lines of the database log.\n"
    "**!apilog** - Displays the last 20 lines of the API log.\n"
    "**!messagelog** - Displays the last 20 lines of the message log.\n"
    "**!addArtist <artist_id>** - Adds or marks an artist as notable by their ID.\n"
    "**!commands** - Shows this help message with summaries of all commands."
)

@bot.command(name="commands", help="Shows all available commands with summaries")
async def custom_help(ctx):
    """Sends an embedded help message listing all available commands."""
    embed = discord.Embed(
        title="Bot Commands",
        description="**Available Commands**\n\n" + COMMAND_LIST,
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)
    logger.info("Sent help message to Discord.")

# Event to handle unknown commands
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title=f"Command \"{ctx.message.content}\" not recognized",
            description="**Available Commands**\n\n" + COMMAND_LIST,
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        logger.warning(f"User tried unknown command: {ctx.message.content}")
    else:
        # For other errors, pass them on
        raise error


@bot.command(name="eventlog", help="Displays the last 20 lines of the event log")
async def event_log(ctx):
    await send_log_tail(ctx, LOG_FILES["eventlog"], "Event Log")

@bot.command(name="dblog", help="Displays the last 20 lines of the database log")
async def db_log(ctx):
    await send_log_tail(ctx, LOG_FILES["dblog"], "Database Log")

@bot.command(name="messagelog", help="Displays the last 20 lines of the message log")
async def message_log(ctx):
    await send_log_tail(ctx, LOG_FILES["messagelog"], "Message Log")

@bot.command(name="apilog", help="Displays the last 20 lines of the API log")
async def api_log(ctx):
    await send_log_tail(ctx, LOG_FILES["apilog"], "API Log")

async def send_log_tail(ctx, log_file, title):
    """Helper function to send the last 20 lines of a log file as an embedded message."""
    try:
        # Read the last 20 lines of the log file
        with open(log_file, "r") as file:
            log_tail = ''.join(deque(file, maxlen=20))

        # Send as an embedded message with code block formatting
        embed = discord.Embed(
            title=title,
            description=f"```\n{log_tail}```",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Unable to retrieve {title.lower()}.")
        logging.getLogger("commandHandler").error(f"Failed to send {title}: {e}")

@bot.command(name="addArtist", help="Adds or marks an artist as notable by ID")
async def add_artist(ctx, artist_id: str):
    """Marks an artist as notable in the database, adding them if they don't exist, and verifies with Ticketmaster API."""
    try:
        # Query the Ticketmaster Discovery API to verify the artist
        api_url = f"https://app.ticketmaster.com/discovery/v2/attractions"
        params = {
            "apikey": TICKETMASTER_API_KEY,
            "id": artist_id,
            "locale": "*"
        }
        
        # Make the API request asynchronously
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params) as response:
                response.raise_for_status()  # Raises an exception for 4XX/5XX errors
                data = await response.json()  # Parse JSON asynchronously
        
        # Check if artist data is present
        attractions = data.get("_embedded", {}).get("attractions", [])
        if not attractions:
            await ctx.send("Artist not found, check Ticketmaster API for the correct ID.")
            return
        
        # Retrieve artist name and ID from the API response
        artist_name = attractions[0].get("name", "Unknown Artist")

        # Check if the artist already exists in the database
        c.execute("SELECT artistID FROM Artists WHERE artistID = ?", (artist_id,))
        existing_artist = c.fetchone()

        if existing_artist:
            # Update the artist to be notable if they exist
            c.execute("UPDATE Artists SET notable = 1 WHERE artistID = ?", (artist_id,))
            conn.commit()
            await ctx.send(f"Artist \"{artist_name}\" with ID: {artist_id} marked as notable.")
        else:
            # Insert a new artist record and mark as notable if they don't exist
            c.execute("INSERT INTO Artists (artistID, name, notable) VALUES (?, ?, ?)", (artist_id, artist_name, 1))
            conn.commit()
            await ctx.send(f"Artist \"{artist_name}\" with ID: {artist_id} added and marked as notable.")

        # Set sentToDiscord = 0 for all events with this artist
        c.execute("UPDATE Events SET sentToDiscord = 0 WHERE artistID = ?", (artist_id,))
        conn.commit()

        # Log this action
        logging.getLogger("dbLogger").info(f"Artist \"{artist_name}\" with ID {artist_id} added/updated as notable, and events marked for re-sending.")
    
    except aiohttp.ClientError as e:
        await ctx.send("Error fetching artist data from Ticketmaster API.")
        logging.getLogger("dbLogger").error(f"Ticketmaster API request failed for artist ID {artist_id}: {e}")
    
    except Exception as e:
        await ctx.send("Error adding or updating notable artist.")
        logging.getLogger("dbLogger").error(f"Failed to add/update notable artist {artist_id}: {e}")
@bot.command(name="next", help="Shows a list of the next notable events with ticket sales starting soon.")
async def next_events(ctx, number: int = 5):  # Default to 5 if no number is provided
    # Cap the number to 50
    number = min(number, 50)

    # Determine if we should filter by notable artists based on the channel
    notable_only = ctx.channel.id == DISCORD_CHANNEL_ID

    # Modify the query based on whether notable-only events should be fetched
    query = '''
        SELECT DISTINCT Events.eventID, Events.name, Events.ticketOnsaleStart, Events.eventDate, Events.url, 
            Venues.city, Venues.state, Artists.name
        FROM Events
        LEFT JOIN Venues ON Events.venueID = Venues.venueID
        LEFT JOIN Artists ON Events.artistID = Artists.artistID
        WHERE datetime(Events.ticketOnsaleStart, 'utc') >= datetime('now', 'utc')
    '''

    # Add notable-only filter if required
    if notable_only:
        query += " AND Artists.notable = 1"

    # Finalize ordering and limiting
    query += " ORDER BY Events.ticketOnsaleStart ASC LIMIT ?"

    # Execute the query with the specified limit
    c.execute(query, (number,))
    events = c.fetchall()

    if not events:
        message = "No upcoming notable events with ticket sales starting soon." if notable_only else "No upcoming events with ticket sales starting soon."
        await ctx.send(message)
        return

    # Prepare the message format and track total length
    message_lines = []
    total_length = 0
    max_description_length = 4096  # Discord's limit for embed descriptions

    for idx, event in enumerate(events, start=1):
        # Parse the ticket sale start time as an aware datetime in UTC
        sale_start = datetime.strptime(event[2], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        time_remaining = sale_start - datetime.now(timezone.utc)

        # Format the time until sale starts
        if time_remaining.total_seconds() < 3600:
            # Less than an hour away
            time_str = f"in {int(time_remaining.total_seconds() // 60)} minutes" if time_remaining.total_seconds() >= 0 else f"{int(-time_remaining.total_seconds() // 60)} minutes ago"
        elif time_remaining.total_seconds() < 86400:
            # Less than a day away
            hours, remainder = divmod(time_remaining.total_seconds(), 3600)
            minutes = remainder // 60
            time_str = f"in {int(hours)} hours {int(minutes)} minutes" if time_remaining.total_seconds() >= 0 else f"{int(hours)} hours {int(minutes)} minutes ago"
        else:
            # More than a day away, use human-readable date with ordinal suffix
            time_str = format_date_with_ordinal(sale_start)

        # Create a line for this event
        event_line = f"{idx}. [{event[1]}]({event[4]}) sale starts {time_str}\n"
        
        # Check if adding this line would exceed the max length for description
        if total_length + len(event_line) > max_description_length:
            # Send current embed and reset
            embed = discord.Embed(
                title="Next Notable Events with Upcoming Ticket Sales" if notable_only else "Next Events with Upcoming Ticket Sales",
                description="".join(message_lines),
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            message_lines.clear()
            total_length = 0

        # Add the event line to the current list and update length
        message_lines.append(event_line)
        total_length += len(event_line)

    # Send remaining lines if any
    if message_lines:
        embed = discord.Embed(
            title="Next Notable Events with Upcoming Ticket Sales" if notable_only else "Next Events with Upcoming Ticket Sales",
            description="".join(message_lines),
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

# Helper function to format dates with ordinal suffixes for the day
def format_date_with_ordinal(dt):
    day = dt.day
    suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return dt.strftime(f"%B {day}{suffix}, %Y")
