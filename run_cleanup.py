import asyncio
from config.db_pool import initialize_db_pool, close_db_pool
from config.config import DATABASE_URL
from config.logging import logger

async def run_cleanup():
    """Run the database cleanup with proper initialization."""
    try:
        # Initialize database pool first
        await initialize_db_pool(DATABASE_URL)
        logger.info("Database pool initialized.")
        
        # Import after db_pool is initialized
        from database.cleanup import cleanup_server_table
        await cleanup_server_table()
        logger.info("Server table cleanup completed.")
        
    except Exception as e:
        logger.error(f"Error in cleanup: {e}", exc_info=True)
    finally:
        await close_db_pool()
        logger.info("Database pool closed.")

if __name__ == "__main__":
    print("Starting database cleanup...")
    asyncio.run(run_cleanup())
    print("Database cleanup completed.") 