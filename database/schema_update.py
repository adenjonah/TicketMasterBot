import asyncio
import logging
from config.db_pool import initialize_db_pool, db_pool, close_db_pool
from config.config import DATABASE_URL
from config.logging import logger

async def get_table_name(conn, table_base_name):
    """Find the actual table name with case sensitivity in mind."""
    tables = await conn.fetch("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
      AND table_name ILIKE $1
    """, table_base_name)
    
    if not tables:
        return None
        
    # Return the first matching table name
    return tables[0]['table_name']

async def add_region_column_to_events():
    """Add a region column to the events table."""
    logger.info("Starting events table schema update...")
    
    try:
        async with db_pool.acquire() as conn:
            # Get the actual events table name
            events_table = await get_table_name(conn, 'events')
            
            if not events_table:
                logger.error("Events table not found. Cannot proceed with schema update.")
                return False
                
            logger.info(f"Found events table: {events_table}")
            
            # Check if the region column already exists
            columns = await conn.fetch("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = $1
            """, events_table)
            
            column_names = [col['column_name'].lower() for col in columns]
            
            if 'region' in column_names:
                logger.info("Region column already exists in the events table.")
                return True
            
            # Add the region column
            logger.info("Adding region column to events table...")
            await conn.execute(f"""
            ALTER TABLE {events_table}
            ADD COLUMN region TEXT
            """)
            
            logger.info("Region column added successfully!")
            return True
            
    except Exception as e:
        logger.error(f"Error updating events table schema: {e}", exc_info=True)
        return False

async def main():
    """Main function to run the schema update."""
    try:
        logger.info("Initializing database pool...")
        await initialize_db_pool(DATABASE_URL)
        logger.info("Database pool initialized.")
        
        success = await add_region_column_to_events()
        
        if success:
            logger.info("Schema update completed successfully.")
        else:
            logger.error("Schema update failed.")
        
    except Exception as e:
        logger.error(f"Error in schema update script: {e}", exc_info=True)
    finally:
        logger.info("Closing database pool...")
        await close_db_pool()

if __name__ == "__main__":
    print("Starting events table schema update...")
    asyncio.run(main())
    print("Schema update script completed.") 