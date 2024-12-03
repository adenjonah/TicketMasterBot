import asyncio
from discord.ext import tasks, commands
import logging
import discord
from config.db_pool import initialize_db_pool, close_db_pool, db_pool
from tasks.fetch_and_process import fetch_events
from tasks.notify_events import notify_events
from database.init import initialize_db
from config.logging import logger
from config.config import (
    DISCORD_BOT_TOKEN,
    DISCORD_CHANNEL_ID,
    DISCORD_CHANNEL_ID_TWO,
    DATABASE_URL,
    DEBUG,
)

# Define intents for the bot
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.messages = True
intents.message_content = True

# Initialize the bot with command prefix
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    """Event triggered when the bot is ready."""
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    logger.info("Bot is ready!")

    # Initialize database and start periodic tasks
    logger.info("Initializing database and starting tasks...")
    await initialize_db_pool(DATABASE_URL, min_size=1, max_size=10)
    await initialize_db()
    fetch_events_task.start()
    notify_events_task.start()
    logger.info("Tasks started.")
    
# async def initialize_bot():
#     """Initialize the bot, including database and tasks."""
#     logger.info("Initializing bot and database...")
    
#     # Initialize database connection pool
#     await initialize_db_pool(DATABASE_URL, min_size=1, max_size=10)
#     await initialize_db()
#     logger.info("Database initialized.")

#     # Start the periodic event fetch and notification tasks
#     logger.info("Starting event fetch and notification loops...")
#     fetch_events_task.start()
#     notify_events_task.start()

@tasks.loop(minutes=1)
async def fetch_events_task():
    """Periodic task to fetch events."""
    logger.info("Starting event fetch process...")
    try:
        await fetch_events()
    except Exception as e:
        logger.error(f"Error during event fetch: {e}", exc_info=True)

@tasks.loop(minutes=1)
async def notify_events_task():
    """Periodic task to notify Discord about events."""
        
    logger.info("Starting event notification process...")
    try:
        logger.info("Notifying notable events...")
        await notify_events(bot, DISCORD_CHANNEL_ID, notable_only=True)
        logger.info("Notifying non-notable events...")
        await notify_events(bot, DISCORD_CHANNEL_ID_TWO, notable_only=False)
    except Exception as e:
        logger.error(f"Error during event notification: {e}", exc_info=True)

async def shutdown(loop):
    """Shutdown function to cancel tasks and close the loop."""
    logger.info("Shutting down bot...")
    
    # Stop periodic tasks
    fetch_events_task.stop()
    notify_events_task.stop()

    # Cancel all running tasks
    tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Close the database pool
    await close_db_pool()

    logger.info("Shutdown complete.")


if __name__ == "__main__":
    try:
        logger.info("Starting bot...")
        bot.run(DISCORD_BOT_TOKEN)  # Start the bot with commands.Bot
    except KeyboardInterrupt:
        logger.warning("Shutting down bot.")
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
    finally:
        # Ensure cleanup happens before exiting
        asyncio.run(shutdown())