import asyncio
from tasks.fetch_and_process import fetch_events
from database.init import initialize_db
from discord.ext import tasks
from config.config import DATABASE_URL
import asyncpg
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

db_pool = None  # Initialize globally


async def initialize_bot():
    """Initialize the bot, including database and tasks."""
    global db_pool

    logger.info("Initializing bot and database...")
    
    # Initialize database connection pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    await initialize_db()
    logger.info("Database initialized.")

    # Start the periodic event fetch task
    logger.info("Starting event fetch loop...")
    fetch_events_task.start()


@tasks.loop(minutes=1)
async def fetch_events_task():
    """Periodic task to fetch events."""
    global db_pool
    logger.info("Starting event fetch process...")
    try:
        # Fetch events using the shared database pool
        await fetch_events(bot=None, db_pool=db_pool)
    except Exception as e:
        logger.error(f"Error during event fetch: {e}", exc_info=True)


async def shutdown():
    """Shut down the bot and clean up resources."""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed.")


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
        loop.run_until_complete(shutdown())
        loop.close()