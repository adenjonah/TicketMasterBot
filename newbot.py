import discord
from discord.ext import tasks, commands
from config.db_pool import initialize_db_pool, close_db_pool
from tasks.notify_events import notify_events
from tasks.check_reminders import check_reminders
from handlers.reaction_handlers import handle_bell_reaction, handle_bell_reaction_remove, handle_x_reaction
from config.config import DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID, DISCORD_CHANNEL_ID_TWO, EUROPEAN_CHANNEL, EUROPEAN_CHANNEL_TWO, DATABASE_URL
from config.logging import logger
import logging
from database.init import initialize_db
import asyncio
import os

# Update to include message_content intent (explicitly required for 2023+ API)
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.messages = True
intents.message_content = True  # Required for accessing message content
intents.reactions = True  # Required for reaction handlers

# Use basic Bot with command prefix
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f"Bot logged in as {bot.user.name}")
    
    # Only log initialization details in debug mode
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Initializing database pool...")
        
    # Initialize database pool first
    await initialize_db_pool(DATABASE_URL)
    
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Database pool initialized.")
        logger.debug("Initializing database...")
    
    # Then initialize database and clean up server table
    await initialize_db()
    
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Database initialized.")
        logger.debug("Cleaning up server table...")
    
    try:
        # Use direct function call instead of importing from database.cleanup
        from database.cleanup import cleanup_server_table
        await cleanup_server_table()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Server table cleaned up.")
    except Exception as e:
        logger.error(f"Error cleaning up server table: {e}")
    
    # Start tasks
    notify_events_task.start()
    check_reminders_task.start()
    recheck_vf_signups_task.start()
    
    logger.info("Bot ready")

@bot.event
async def on_raw_reaction_add(payload):
    """Event handler for reactions added to messages"""
    # Handle based on emoji type
    emoji = str(payload.emoji)
    
    if emoji == "🔔":
        await handle_bell_reaction(bot, payload)
    elif emoji == "❌":
        await handle_x_reaction(bot, payload)

@bot.event
async def on_raw_reaction_remove(payload):
    """Event handler for reactions removed from messages"""
    # Check if the reaction is a bell emoji (🔔)
    if str(payload.emoji) != "🔔":
        return
    
    await handle_bell_reaction_remove(bot, payload)

@tasks.loop(minutes=1)
async def notify_events_task():
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Starting event notification process...")
    
    try:
        # Process notable US events (notable=True, region=non-eu) -> US1 (DISCORD_CHANNEL_ID)
        await notify_events(bot, DISCORD_CHANNEL_ID, notable_only=True, region='non-eu')
        
        # Process notable EU events (notable=True, region=eu) -> EU1 (EUROPEAN_CHANNEL)
        if EUROPEAN_CHANNEL and EUROPEAN_CHANNEL != 0:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Checking for notable European events to send to channel ID: {EUROPEAN_CHANNEL}")
            
            try:
                await notify_events(bot, EUROPEAN_CHANNEL, notable_only=True, region='eu')
            except discord.errors.Forbidden as e:
                logger.error(f"Failed to send to European channel: {e}")
                # Fallback to US1 if EU1 is not accessible
                await notify_events(bot, DISCORD_CHANNEL_ID, notable_only=True, region='eu')
        else:
            # If EU1 is not configured, use US1 as fallback for notable EU events
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("European channel not configured, using primary US channel for notable EU events")
            
            await notify_events(bot, DISCORD_CHANNEL_ID, notable_only=True, region='eu')
        
        # Process non-notable EU events (notable=False, region=eu) -> EU2 (EUROPEAN_CHANNEL_TWO)
        if EUROPEAN_CHANNEL_TWO and EUROPEAN_CHANNEL_TWO != 0:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Checking for non-notable European events to send to channel ID: {EUROPEAN_CHANNEL_TWO}")
            
            # Check if EU2 is same as US Unfiltered (this indicates a configuration issue)
            if EUROPEAN_CHANNEL_TWO == DISCORD_CHANNEL_ID_TWO:
                logger.warning(f"CONFIGURATION ISSUE: EUROPEAN_CHANNEL_TWO ({EUROPEAN_CHANNEL_TWO}) is the same as DISCORD_CHANNEL_ID_TWO. Non-notable EU events will go to the same channel as non-notable US events!")
            
            try:
                await notify_events(bot, EUROPEAN_CHANNEL_TWO, notable_only=False, region='eu')
            except discord.errors.Forbidden as e:
                logger.error(f"Failed to send to secondary European channel: {e}")
                # Fallback to US2 if EU2 is not accessible
                await notify_events(bot, DISCORD_CHANNEL_ID_TWO, notable_only=False, region='eu')
        else:
            # If EU2 is not configured, use US2 as fallback for non-notable EU events
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Secondary European channel not configured, using secondary US channel for non-notable EU events")
            
            await notify_events(bot, DISCORD_CHANNEL_ID_TWO, notable_only=False, region='eu')
        
        # Process non-notable US events (notable=False, region=non-eu) -> US2 (DISCORD_CHANNEL_ID_TWO)
        await notify_events(bot, DISCORD_CHANNEL_ID_TWO, notable_only=False, region='non-eu')
    except Exception as e:
        logger.error(f"Event notification error: {e}")

@tasks.loop(minutes=5)
async def check_reminders_task():
    """Check for upcoming reminders and send notifications"""
    try:
        await check_reminders(
            bot, 
            DISCORD_CHANNEL_ID,         # US1 - notable US events
            DISCORD_CHANNEL_ID_TWO,     # US2 - non-notable US events
            EUROPEAN_CHANNEL,           # EU1 - notable EU events
            EUROPEAN_CHANNEL_TWO        # EU2 - non-notable EU events
        )
    except Exception as e:
        logger.error(f"Reminder check error: {e}")

@tasks.loop(minutes=10)
async def recheck_vf_signups_task():
    """Periodically recheck recent events for VF signups that may have been added later"""
    try:
        from helpers.vf_checker import recheck_recent_events
        await recheck_recent_events()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Completed VF recheck for recent events")
    except ImportError:
        logger.debug("VF checker module not available, skipping VF recheck")
    except Exception as e:
        logger.error(f"VF recheck error: {e}")

async def shutdown():
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Shutting down bot...")
    
    notify_events_task.stop()
    check_reminders_task.stop()
    recheck_vf_signups_task.stop()
    await close_db_pool()

async def main():
    logger.info("Starting bot...")
    
    # Load command extensions
    loaded_count = 0
    for filename in os.listdir("./commands"):
        # Skip __init__.py and utils.py (they're not command cogs)
        if filename.endswith(".py") and filename not in ["__init__.py", "utils.py"]:
            try:
                await bot.load_extension(f"commands.{filename[:-3]}")
                loaded_count += 1
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Loaded extension: commands.{filename[:-3]}")
            except Exception as e:
                logger.error(f"Failed to load extension {filename}: {e}")
    
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Loaded {loaded_count} command extensions")
        
    await bot.start(DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Shutting down bot due to keyboard interrupt")
    finally:
        asyncio.run(shutdown())