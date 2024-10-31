import discord
from discord.ext import commands
import sqlite3
import logging
from collections import deque
from datetime import datetime, timedelta, timezone

# Set up intents
intents = discord.Intents.default()
intents.message_content = True

# Initialize bot with intents
bot = commands.Bot(command_prefix="!", intents=intents)

# Log file paths
LOG_FILES = {
    "eventlog": "logs/event_log.log",
    "dblog": "logs/db_log.log",
    "messagelog": "logs/message_log.log"
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

# Set up intents
intents = discord.Intents.default()
intents.message_content = True

# Initialize bot with intents
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.command(name="commands", help="Shows all available commands with summaries")
async def custom_help(ctx):
    """Sends an embedded help message listing all available commands."""
    help_text = (
        "**Available Commands**\n\n"
        "**!eventlog** - Displays the last 20 lines of the event log.\n"
        "**!dblog** - Displays the last 20 lines of the database log.\n"
        "**!messagelog** - Displays the last 20 lines of the message log.\n"
        "**!addNotableArtist <artist_id>** - Adds or marks an artist as notable by their ID.\n"
        "**!commands** - Shows this help message with summaries of all commands."
    )

    embed = discord.Embed(
        title="Bot Commands",
        description=help_text,
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)
    logger.info("Sent help message to Discord.")


@bot.command(name="eventlog", help="Displays the last 20 lines of the event log")
async def event_log(ctx):
    await send_log_tail(ctx, LOG_FILES["eventlog"], "Event Log")

@bot.command(name="dblog", help="Displays the last 20 lines of the database log")
async def db_log(ctx):
    await send_log_tail(ctx, LOG_FILES["dblog"], "Database Log")

@bot.command(name="messagelog", help="Displays the last 20 lines of the message log")
async def message_log(ctx):
    await send_log_tail(ctx, LOG_FILES["messagelog"], "Message Log")

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

@bot.command(name="addNotableArtist", help="Adds or marks an artist as notable by ID")
async def add_notable_artist(ctx, artist_id: str):
    """Marks an artist as notable in the database, adding them if they don't exist."""
    try:
        # Check if the artist already exists
        c.execute("SELECT artistID FROM Artists WHERE artistID = ?", (artist_id,))
        existing_artist = c.fetchone()

        if existing_artist:
            # Update the artist to be notable if they exist
            c.execute("UPDATE Artists SET notable = 1 WHERE artistID = ?", (artist_id,))
            conn.commit()
            await ctx.send(f"Artist {artist_id} marked as notable.")
        else:
            # Insert a new artist record and mark as notable if they don't exist
            c.execute("INSERT INTO Artists (artistID, name, notable) VALUES (?, ?, ?)", (artist_id, None, 1))
            conn.commit()
            await ctx.send(f"Artist {artist_id} added and marked as notable.")

        # Log this action
        logging.getLogger("dbLogger").info(f"Artist {artist_id} added/updated as notable.")
    except Exception as e:
        await ctx.send("Error adding or updating notable artist.")
        logging.getLogger("dbLogger").error(f"Failed to add/update notable artist {artist_id}: {e}")

@bot.command(name="next", help="Shows a list of the next notable events with ticket sales starting soon.")
async def next_events(ctx, number: int = 5):  # Default to 5 if no number is provided
    # Cap the number to 50
    number = min(number, 50)

    # Fetch the next `number` notable events sorted by ticket onsale start date
    c.execute('''
        SELECT Events.eventID, Events.name, Events.ticketOnsaleStart, Events.eventDate, Events.url, 
               Venues.city, Venues.state, Artists.name
        FROM Events
        LEFT JOIN Venues ON Events.venueID = Venues.venueID
        LEFT JOIN Artists ON Events.artistID = Artists.artistID
        WHERE Artists.notable = 1 AND Events.ticketOnsaleStart >= datetime('now')
        ORDER BY Events.ticketOnsaleStart ASC
        LIMIT ?
    ''', (number,))

    notable_events = c.fetchall()

    if not notable_events:
        await ctx.send("No upcoming notable events with ticket sales starting soon.")
        return

    # Prepare the message format
    message_lines = []
    for idx, event in enumerate(notable_events, start=1):
        # Parse the ticket sale start time as an aware datetime in UTC
        sale_start = datetime.strptime(event[2], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        time_remaining = sale_start - datetime.now(timezone.utc)

        # Format the time until sale starts
        if time_remaining.total_seconds() < 3600:
            # Less than an hour away
            time_str = f"in {int(time_remaining.total_seconds() // 60)} minutes"
        elif time_remaining.total_seconds() < 86400:
            # Less than a day away
            hours, remainder = divmod(time_remaining.total_seconds(), 3600)
            minutes = remainder // 60
            time_str = f"in {int(hours)} hours {int(minutes)} minutes"
        else:
            # More than a day away, use human-readable date with ordinal suffix
            time_str = format_date_with_ordinal(sale_start)

        # Create a hyperlink format: "1. Event Name (link) sale starts: ..."
        message_lines.append(f"{idx}. [{event[1]}]({event[4]}) sale starts: {time_str}")

    # Send message as an embed to preserve formatting
    embed = discord.Embed(
        title=f"Next {number} Notable Events with Upcoming Ticket Sales",
        description="\n".join(message_lines),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

# Helper function to format dates with ordinal suffixes for the day
def format_date_with_ordinal(dt):
    day = dt.day
    suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return dt.strftime(f"%B {day}{suffix}, %Y")