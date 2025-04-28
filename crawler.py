import asyncio
from tasks.fetch_and_process import fetch_events
from config.db_pool import initialize_db_pool, close_db_pool
from config.config import DATABASE_URL
from database.init import initialize_db
from config.logging import logger
import logging

async def main():
    """Main function for the API crawler."""
    try:
        # Log startup only once at INFO level
        logger.info("Initializing crawler...")
        
        # Make initialization logs debug-only
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Initializing database pool...")
        
        await initialize_db_pool(DATABASE_URL)
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Database pool initialized.")
            logger.debug("Initializing database...")
        
        await initialize_db()
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Database initialized.")
            logger.debug("Cleaning up server table...")
        
        try:
            # Import and call cleanup function here to ensure db_pool is initialized
            from database.cleanup import cleanup_server_table
            await cleanup_server_table()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Server table cleanup completed.")
        except Exception as e:
            logger.error(f"Error cleaning up server table: {e}")

        logger.info("Crawler initialized and running")
        iteration_count = 0
        
        while True:
            # Only log every 5 iterations at INFO level to reduce log volume
            if iteration_count % 5 == 0:
                if logger.isEnabledFor(logging.INFO):
                    logger.info(f"Running event fetch iteration {iteration_count}")
            elif logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Fetching events (iteration {iteration_count})...")
                
            await fetch_events()
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Event fetch completed (iteration {iteration_count}).")
                
            iteration_count += 1
            await asyncio.sleep(60)  # Run every 1 minute
    except Exception as e:
        logger.error(f"Error in API crawler: {e}")
    finally:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Closing database pool...")
        await close_db_pool()

if __name__ == "__main__":
    asyncio.run(main())