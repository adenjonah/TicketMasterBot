import discord
from discord.ext import tasks, commands
from config.db_pool import initialize_db_pool, close_db_pool
from tasks.notify_events import notify_events
from config.config import DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID, DISCORD_CHANNEL_ID_TWO, DATABASE_URL
from config.logging import logger
import asyncio
import os
from datetime import datetime
import re

intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.messages = True
intents.message_content = True
intents.reactions = True  # Enable reaction intents

bot = commands.Bot(command_prefix="!", intents=intents)

async def find_event_and_artist(embed, conn):
    """
    Helper function to find the correct event and artist from an embed.
    Returns a tuple of (artist_id, artist_name) or (None, None) if not found.
    """
    title = embed.title
    event_url = embed.url
    
    logger.debug(f"Processing message with title: '{title}' and URL: '{event_url}'")
    
    # Extract the event ID from the URL
    event_id = None
    if event_url:
        try:
            # Most Ticketmaster URLs have the event ID at the end or in a specific pattern
            # First, try to extract from URL paths like /event/{eventId}
            if '/event/' in event_url:
                parts = event_url.split('/event/')
                if len(parts) > 1:
                    event_id = parts[1].split('/')[0].split('?')[0]
            # If that doesn't work, try extracting from the end of the URL
            if not event_id:
                parts = event_url.split('/')
                if parts:
                    # Get the last part and remove any query parameters
                    event_id = parts[-1].split('?')[0]
                    
            logger.debug(f"Extracted event ID from URL: {event_id}")
        except Exception as e:
            logger.error(f"Error extracting event ID from URL {event_url}: {e}")
    
    # First try to get artist from title if in the format "Artist Name - Event Name"
    artist_id = None
    artist_name = title.split(" - ")[0] if " - " in title else None
    
    try:
        if artist_name:
            # Try to find the artist by name
            artist = await conn.fetchrow(
                "SELECT artistID FROM Artists WHERE name = $1",
                artist_name
            )
            
            if artist:
                artist_id = artist['artistid']
        
        # If we couldn't find the artist by name but have an event ID, look up by event
        if not artist_id and event_id:
            # Get the complete event details including date, time, and location
            event_details = await conn.fetchrow(
                """
                SELECT 
                    Events.eventID, 
                    Events.name as event_name, 
                    Events.artistID, 
                    Artists.name as artist_name,
                    Events.eventDate,
                    Venues.name as venue_name,
                    Venues.city,
                    Venues.state
                FROM Events
                LEFT JOIN Artists ON Events.artistID = Artists.artistID
                LEFT JOIN Venues ON Events.venueID = Venues.venueID
                WHERE Events.eventID = $1
                """,
                event_id
            )
            
            if event_details and event_details['artistid']:
                artist_id = event_details['artistid']
                artist_name = event_details['artist_name']
                logger.info(f"Found event: {event_details['event_name']} at {event_details['venue_name']} in {event_details['city']}, {event_details['state']} on {event_details['eventdate']}")
            else:
                # Handle case where no artist is associated with the event
                logger.warning(f"No artist associated with event ID: {event_id}")
                return None, None
        
        # If we still couldn't find the artist, try to find by event name and extract location/date from the embed description
        if not artist_id and title:
            # For events without artist in title, the entire title is the event name
            event_name = title
            
            # Try to extract location and date information from embed description
            location = None
            event_date = None
            
            # Parse the embed description to extract location and date
            if embed.description:
                description_lines = embed.description.split('\n')
                for line in description_lines:
                    if "Location" in line:
                        location_part = line.split("Location:")[1] if "Location:" in line else line.split("Location")[1]
                        location = location_part.strip()
                    elif "Event Date" in line:
                        date_part = line.split("Event Date:")[1] if "Event Date:" in line else line.split("Event Date")[1]
                        event_date = date_part.strip()
            
            # Build a more precise query using all available information
            query = """
                SELECT 
                    Events.eventID, 
                    Events.name as event_name, 
                    Events.artistID, 
                    Artists.name as artist_name,
                    Events.eventDate,
                    Venues.name as venue_name,
                    Venues.city,
                    Venues.state
                FROM Events
                LEFT JOIN Artists ON Events.artistID = Artists.artistID
                LEFT JOIN Venues ON Events.venueID = Venues.venueID
                WHERE Events.name = $1
            """
            
            params = [event_name]
            param_count = 1
            
            # Add location filter if available
            if location:
                city_state = location.split(', ')
                if len(city_state) == 2:
                    city, state = city_state
                    query += f" AND Venues.city = ${param_count + 1} AND Venues.state = ${param_count + 2}"
                    params.extend([city, state])
                    param_count += 2
            
            # Get matching events
            matching_events = await conn.fetch(query, *params)
            
            if matching_events:
                # If we have multiple matches, try to narrow down by date
                if len(matching_events) > 1 and event_date:
                    # Log details of all matching events for debugging
                    logger.info(f"Found {len(matching_events)} events matching '{event_name}'. Listing all matches:")
                    for i, evt in enumerate(matching_events):
                        logger.info(f"  Match #{i+1}: {evt['event_name']} at {evt['venue_name']} in {evt['city']}, {evt['state']} on {evt['eventdate']}")
                    
                    logger.info(f"Attempting to find best match by date: '{event_date}'")
                    
                    # Extract just the date part (remove time)
                    date_match = re.search(r'([A-Za-z]+ \d+, \d{4})', event_date)
                    if date_match:
                        embed_date_str = date_match.group(1)
                        try:
                            # Parse the date from the embed
                            embed_date = datetime.strptime(embed_date_str, "%B %d, %Y").date()
                            
                            # Find the closest match
                            best_match = None
                            for event in matching_events:
                                if event['eventdate']:
                                    db_date = event['eventdate'].date()
                                    if db_date == embed_date:
                                        best_match = event
                                        break
                            
                            if best_match:
                                artist_id = best_match['artistid']
                                artist_name = best_match['artist_name']
                                logger.info(f"Found exact date match: {best_match['event_name']} on {best_match['eventdate']}")
                            else:
                                # Just use the first match if no exact date match
                                artist_id = matching_events[0]['artistid']
                                artist_name = matching_events[0]['artist_name']
                                logger.info(f"No exact date match found. Using first match: {matching_events[0]['event_name']}")
                        except Exception as e:
                            logger.error(f"Error parsing date '{embed_date_str}': {e}")
                            # Fall back to first match
                            artist_id = matching_events[0]['artistid']
                            artist_name = matching_events[0]['artist_name']
                    else:
                        logger.warning(f"Could not extract date from '{event_date}'")
                        artist_id = matching_events[0]['artistid']
                        artist_name = matching_events[0]['artist_name']
                else:
                    # Just use the first match
                    artist_id = matching_events[0]['artistid']
                    artist_name = matching_events[0]['artist_name']
                    logger.info(f"Found event: {matching_events[0]['event_name']} at {matching_events[0]['venue_name']} in {matching_events[0]['city']}, {matching_events[0]['state']}")
            else:
                logger.warning(f"No events found matching name: {event_name}")
                return None, None
        
        if not artist_id:
            logger.warning(f"Could not find artist for message title: {title}")
            return None, None
        
        return artist_id, artist_name
    
    except Exception as e:
        logger.error(f"Error finding event and artist: {e}", exc_info=True)
        return None, None

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await initialize_db_pool(DATABASE_URL)
    logger.info("Database pool initialized.")
    notify_events_task.start()

@tasks.loop(minutes=1)
async def notify_events_task():
    logger.info("Starting event notification process...")
    try:
        await notify_events(bot, DISCORD_CHANNEL_ID, notable_only=True)
        await notify_events(bot, DISCORD_CHANNEL_ID_TWO, notable_only=False)
    except Exception as e:
        logger.error(f"Error during event notification: {e}", exc_info=True)

@bot.event
async def on_raw_reaction_add(payload):
    # Configure the emoji to listen for
    target_emoji = "🔔"  # Bell emoji for reminder
    
    # Ignore bot reactions
    if payload.user_id == bot.user.id:
        return
    
    # Check if the reaction is the target emoji
    if str(payload.emoji) != target_emoji:
        return
    
    # Fetch the message that was reacted to
    channel = bot.get_channel(payload.channel_id)
    if not channel:
        logger.error(f"Could not find channel with ID {payload.channel_id}")
        return
    
    try:
        message = await channel.fetch_message(payload.message_id)
    except Exception as e:
        logger.error(f"Error fetching message: {e}")
        return
    
    # Check if the message is from the bot and has embeds (artist alerts)
    if message.author.id != bot.user.id or not message.embeds:
        return
    
    # Use the helper function to find the artist
    from config.db_pool import db_pool
    from database.updating import set_artist_reminder
    
    async with db_pool.acquire() as conn:
        artist_id, artist_name = await find_event_and_artist(message.embeds[0], conn)
        
        if artist_id:
            # Use the set_artist_reminder function
            success = await set_artist_reminder(artist_id, artist_name)
            if success:
                logger.info(f"Set reminder for artist: {artist_name}")
            else:
                logger.error(f"Failed to set reminder for artist: {artist_name}")

@bot.event
async def on_raw_reaction_remove(payload):
    # Configure the emoji to listen for
    target_emoji = "🔔"  # Bell emoji for reminder
    
    # Ignore bot reactions
    if payload.user_id == bot.user.id:
        return
    
    # Check if the reaction is the target emoji
    if str(payload.emoji) != target_emoji:
        return
    
    # Fetch the message that was reacted to
    channel = bot.get_channel(payload.channel_id)
    if not channel:
        logger.error(f"Could not find channel with ID {payload.channel_id}")
        return
    
    try:
        message = await channel.fetch_message(payload.message_id)
    except Exception as e:
        logger.error(f"Error fetching message: {e}")
        return
    
    # Check if the message is from the bot and has embeds (artist alerts)
    if message.author.id != bot.user.id or not message.embeds:
        return
    
    # Check if this was the last reaction of this type
    # We only want to clear the reminder if no more users have this reaction
    still_has_bell_reaction = False
    for reaction in message.reactions:
        if str(reaction.emoji) == target_emoji and reaction.count > 0:
            still_has_bell_reaction = True
            break
            
    if still_has_bell_reaction:
        logger.info(f"Not clearing reminder as other users still have bell reactions")
        return
    
    # Use the helper function to find the artist
    from config.db_pool import db_pool
    from database.updating import clear_artist_reminder
    
    async with db_pool.acquire() as conn:
        artist_id, artist_name = await find_event_and_artist(message.embeds[0], conn)
        
        if artist_id:
            # Use the clear_artist_reminder function
            success = await clear_artist_reminder(artist_id, artist_name)
            if success:
                logger.info(f"Cleared reminder for artist: {artist_name}")
            else:
                logger.error(f"Failed to clear reminder for artist: {artist_name}")

async def shutdown():
    logger.info("Shutting down bot...")
    notify_events_task.stop()
    await close_db_pool()

async def main():
    logger.info("Starting bot...")
    for filename in os.listdir("./commands"):
        if filename.endswith(".py") and filename != "__init__.py":
            await bot.load_extension(f"commands.{filename[:-3]}")
    await bot.start(DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Shutting down bot.")
    finally:
        asyncio.run(shutdown())