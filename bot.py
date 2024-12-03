import asyncio
from discord.ext import tasks
import logging
from config.db_pool import initialize_db_pool, close_db_pool, db_pool
from tasks.fetch_and_process import fetch_events
from database.init import initialize_db
from config.config import (
    DISCORD_BOT_TOKEN,
    DISCORD_CHANNEL_ID,
    DISCORD_CHANNEL_ID_TWO,
    TICKETMASTER_API_KEY,
    REDIRECT_URI,
    DATABASE_URL,
    DEBUG,
)

# Set logging level based on DEBUG flag
logging_level = logging.DEBUG if DEBUG == "True" else logging.INFO
print(f"DEBUG: {DEBUG}")
# Configure logging
logging.basicConfig(level=logging_level, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

async def initialize_bot():
    """Initialize the bot, including database and tasks."""
    logger.info("Initializing bot and database...")
    
    # Initialize database connection pool
    await initialize_db_pool(DATABASE_URL, min_size=1, max_size=10)
    await initialize_db()
    logger.info("Database initialized.")

    # Start the periodic event fetch task
    logger.info("Starting event fetch loop...")
    fetch_events_task.start()

@tasks.loop(minutes=1)
async def fetch_events_task():
    """Periodic task to fetch events."""
    logger.info("Starting event fetch process...")
    try:
        await fetch_events()
    except Exception as e:
        logger.error(f"Error during event fetch: {e}", exc_info=True)


async def shutdown(loop):
    """Shutdown function to cancel tasks and close the loop."""
    logger.info("Shutting down bot...")
    
    # Stop periodic tasks
    fetch_events_task.stop()

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
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        logger.info("Starting bot...")
        loop.run_until_complete(initialize_bot())
        loop.run_forever()
    except KeyboardInterrupt:
        logger.warning("Shutting down bot.")
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
    finally:
        # Ensure cleanup happens before exiting
        loop.run_until_complete(shutdown(loop))
        loop.close()