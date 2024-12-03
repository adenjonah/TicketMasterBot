import asyncio
from tasks.fetch_and_process import fetch_events
from config.db_pool import initialize_db_pool, close_db_pool
from config.config import DATABASE_URL
from config.logging import logger

async def main():
    """Main function for the API crawler."""
    try:
        logger.info("Initializing database pool...")
        await initialize_db_pool(DATABASE_URL)
        logger.info("Database pool initialized.")

        while True:
            logger.info("Fetching events...")
            await fetch_events()
            logger.info("Event fetch completed.")
            await asyncio.sleep(60)  # Run every 1 minute
    except Exception as e:
        logger.error(f"Error in API crawler: {e}", exc_info=True)
    finally:
        logger.info("Closing database pool...")
        await close_db_pool()

if __name__ == "__main__":
    asyncio.run(main())