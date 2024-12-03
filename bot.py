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
    try:
        logger.debug("Starting database pool initialization...")
        await initialize_db_pool(DATABASE_URL, min_size=1, max_size=100)
        logger.debug("Database pool initialized.")
        logger.debug("Initializing database schema...")
        await initialize_db()
        logger.debug("Database schema initialized.")
        logger.debug("Starting periodic tasks...")
        fetch_events_task.start()
        notify_events_task.start()
        logger.info("Tasks started.")
    except Exception as e:
        logger.error(f"Error during initialization in on_ready: {e}", exc_info=True)

@tasks.loop(minutes=1)
async def fetch_events_task():
    """Periodic task to fetch events."""
    logger.info("Starting event fetch process...")
    try:
        
        # from config.db_pool import db_pool  # Ensure db_pool is imported

        # async with db_pool.acquire() as conn:
        #     logger.debug("Deleting event with ID 'G5dIZb99QrFCb' before fetching events...")
        #     await conn.execute("DELETE FROM Events WHERE eventID = $1", 'G5dIZb99QrFCb')
        #     logger.info("Event with ID 'G5dIZb99QrFCb' deleted successfully.")


        logger.debug("Calling fetch_events...")
        await fetch_events()
        logger.debug("fetch_events completed successfully.")
    except Exception as e:
        logger.error(f"Error during event fetch: {e}", exc_info=True)

@tasks.loop(minutes=1)
async def notify_events_task():
    """Periodic task to notify Discord about events."""
    logger.info("Starting event notification process...")
    try:
        logger.debug("Notifying notable events...")
        await notify_events(bot, DISCORD_CHANNEL_ID, notable_only=True)
        logger.debug("Notifying non-notable events...")
        await notify_events(bot, DISCORD_CHANNEL_ID_TWO, notable_only=False)
        logger.debug("Event notifications completed.")
    except Exception as e:
        logger.error(f"Error during event notification: {e}", exc_info=True)

async def shutdown(loop):
    """Shutdown function to cancel tasks and close the loop."""
    logger.info("Shutting down bot...")
    try:
        logger.debug("Stopping periodic tasks...")
        fetch_events_task.stop()
        notify_events_task.stop()
        logger.debug("Periodic tasks stopped.")
        logger.debug("Cancelling all running tasks...")
        tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.debug(f"Task {task.get_name()} cancelled.")
        logger.debug("Closing database pool...")
        await close_db_pool()
        logger.info("Shutdown complete.")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)


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
        logger.debug("Running shutdown sequence...")
        asyncio.run(shutdown(asyncio.get_event_loop()))