import discord
from discord.ext import tasks, commands
from config.db_pool import initialize_db_pool, close_db_pool
from tasks.notify_events import notify_events
from config.config import DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID, DISCORD_CHANNEL_ID_TWO, DATABASE_URL
from config.logging import logger
import asyncio
import os

intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.messages = True
intents.message_content = True
intents.reactions = True  # Enable reaction intents

bot = commands.Bot(command_prefix="!", intents=intents)

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
    
    # Extract artist name from the embed title
    embed = message.embeds[0]
    title = embed.title
    
    # The title format is either "Artist Name - Event Name" or just "Event Name"
    artist_name = title.split(" - ")[0] if " - " in title else None
    
    if not artist_name:
        logger.warning(f"Could not extract artist name from message title: {title}")
        return
    
    # Update the database to set reminder to true for this artist
    from config.db_pool import db_pool
    from database.updating import set_artist_reminder
    
    async with db_pool.acquire() as conn:
        try:
            # Find the artist in the database
            artist = await conn.fetchrow(
                "SELECT artistID FROM Artists WHERE name = $1",
                artist_name
            )
            
            if artist:
                # Use the set_artist_reminder function
                success = await set_artist_reminder(artist['artistid'], artist_name)
                if success:
                    logger.info(f"Set reminder for artist: {artist_name}")
                else:
                    logger.error(f"Failed to set reminder for artist: {artist_name}")
            else:
                logger.warning(f"Could not find artist in database: {artist_name}")
        except Exception as e:
            logger.error(f"Error updating artist reminder: {e}", exc_info=True)

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
    
    # Extract artist name from the embed title
    embed = message.embeds[0]
    title = embed.title
    
    # The title format is either "Artist Name - Event Name" or just "Event Name"
    artist_name = title.split(" - ")[0] if " - " in title else None
    
    if not artist_name:
        logger.warning(f"Could not extract artist name from message title: {title}")
        return
    
    # Check if this was the last reaction of this type
    # We only want to clear the reminder if no more users have this reaction
    still_has_bell_reaction = False
    for reaction in message.reactions:
        if str(reaction.emoji) == target_emoji and reaction.count > 0:
            still_has_bell_reaction = True
            break
            
    if still_has_bell_reaction:
        logger.info(f"Not clearing reminder for {artist_name} as other users still have bell reactions")
        return
        
    # Update the database to clear reminder for this artist
    from config.db_pool import db_pool
    from database.updating import clear_artist_reminder
    
    async with db_pool.acquire() as conn:
        try:
            # Find the artist in the database
            artist = await conn.fetchrow(
                "SELECT artistID FROM Artists WHERE name = $1",
                artist_name
            )
            
            if artist:
                # Use the clear_artist_reminder function
                success = await clear_artist_reminder(artist['artistid'], artist_name)
                if success:
                    logger.info(f"Cleared reminder for artist: {artist_name}")
                else:
                    logger.error(f"Failed to clear reminder for artist: {artist_name}")
            else:
                logger.warning(f"Could not find artist in database: {artist_name}")
        except Exception as e:
            logger.error(f"Error clearing artist reminder: {e}", exc_info=True)

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