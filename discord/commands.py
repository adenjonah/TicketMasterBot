from config.config import (
    DISCORD_BOT_TOKEN,
    DISCORD_CHANNEL_ID,
    TICKETMASTER_API_KEY,
    DATABASE_URL,
)

import discord
from discord.ext import commands
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime, timezone
import aiohttp

# Set up intents
intents = discord.Intents.default()
intents.message_content = True

# Initialize bot with intents
bot = commands.Bot(command_prefix="!", intents=intents, case_insensitive=True)

# PostgreSQL database connection
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor(cursor_factory=DictCursor)

# Available commands
COMMAND_LIST = (
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
    else:
        # For other errors, pass them on
        raise error

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
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
        
        attractions = data.get("_embedded", {}).get("attractions", [])
        if not attractions:
            await ctx.send("Artist not found, check Ticketmaster API for the correct ID.")
            return
        
        artist_name = attractions[0].get("name", "Unknown Artist")
        cur.execute("SELECT artistID FROM Artists WHERE artistID = %s", (artist_id,))
        existing_artist = cur.fetchone()

        if existing_artist:
            cur.execute("UPDATE Artists SET notable = TRUE WHERE artistID = %s", (artist_id,))
            await ctx.send(f"Artist \"{artist_name}\" with ID: {artist_id} marked as notable.")
        else:
            cur.execute("INSERT INTO Artists (artistID, name, notable) VALUES (%s, %s, %s)",
                        (artist_id, artist_name, True))
            await ctx.send(f"Artist \"{artist_name}\" with ID: {artist_id} added and marked as notable.")
        
        cur.execute("UPDATE Events SET sentToDiscord = FALSE WHERE artistID = %s", (artist_id,))
        conn.commit()
    
    except aiohttp.ClientError:
        await ctx.send("Error fetching artist data from Ticketmaster API.")
    except Exception as e:
        await ctx.send("Error adding or updating notable artist.")
        print(e)
        
@bot.command(name="next", help="Shows a list of the next notable events with ticket sales starting soon.")
async def next_events(ctx, number: int = 5):
    number = min(number, 50)
    notable_only = ctx.channel.id == DISCORD_CHANNEL_ID
    query = '''
        SELECT DISTINCT e.eventID, e.name, e.ticketOnsaleStart, e.eventDate, e.url, 
                        v.city, v.state, a.name
        FROM Events e
        LEFT JOIN Venues v ON e.venueID = v.venueID
        LEFT JOIN Artists a ON e.artistID = a.artistID
        WHERE e.ticketOnsaleStart >= NOW()
    '''
    if notable_only:
        query += " AND a.notable = TRUE"
    query += " ORDER BY e.ticketOnsaleStart ASC LIMIT %s"

    cur.execute(query, (number,))
    events = cur.fetchall()
    if not events:
        message = "No upcoming notable events with ticket sales starting soon." if notable_only else "No upcoming events with ticket sales starting soon."
        await ctx.send(message)
        return

    message_lines = []
    for idx, event in enumerate(events, start=1):
        time_str = datetime.fromisoformat(event['ticketOnsaleStart']).strftime("%Y-%m-%d %H:%M:%S")
        event_line = f"{idx}. [{event['name']}]({event['url']}) sale starts {time_str}\n"
        message_lines.append(event_line)

    embed = discord.Embed(
        title="Next Events",
        description="".join(message_lines),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

# Helper function to format dates with ordinal suffixes for the day
def format_date_with_ordinal(dt):
    day = dt.day
    suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return dt.strftime(f"%B {day}{suffix}, %Y")

@bot.command(name="ratelimit", help="Checks the current API rate limit status")
async def ratelimit(ctx):
    """Checks the Ticketmaster API rate limit status and displays it."""
    url = f"https://app.ticketmaster.com/discovery/v2/events.json?apikey={TICKETMASTER_API_KEY}&size=1"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            # Retrieve response headers
            headers = response.headers
            
            # Extract rate limit details
            rate_limit = headers.get("Rate-Limit", "Unknown")
            rate_limit_available = headers.get("Rate-Limit-Available", "Unknown")
            rate_limit_reset = headers.get("Rate-Limit-Reset", "Unknown")
            
            # Convert the reset timestamp to a human-readable format if it's available
            reset_time = "Unknown"
            if rate_limit_reset.isdigit():
                reset_time = datetime.fromtimestamp(int(rate_limit_reset) / 1000).strftime("%Y-%m-%d %H:%M:%S UTC")
            
            # Create and send an embedded message with rate limit info to Discord
            embed = discord.Embed(
                title="API Rate Limit Status",
                description=f"**Rate Limit**: {rate_limit}\n"
                            f"**Available Requests**: {rate_limit_available}\n"
                            f"**Reset Time**: {reset_time}",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
