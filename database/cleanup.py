import asyncio
import logging
from config.logging import logger
from config.db_pool import initialize_db_pool, db_pool, close_db_pool
from config.config import DATABASE_URL

# Map full region names to their two-character IDs
REGION_TO_ID = {
    'north': 'no',
    'east': 'ea',
    'south': 'so',
    'west': 'we',
    'europe': 'eu',
    'comedy': 'co',
    'theater': 'th'
}

async def cleanup_server_table():
    """Clean up the Server table by removing duplicates and standardizing IDs."""
    logger.info("Starting server table cleanup...")
    
    try:
        # Get all servers currently in the database
        async with db_pool.acquire() as conn:
            # First, drop any foreign key constraints so we can freely modify the Server table
            await conn.execute("""
            ALTER TABLE ServerTimeSeries DROP CONSTRAINT IF EXISTS fk_server;
            """)
            logger.info("Dropped foreign key constraints temporarily")
            
            # Get all servers
            servers = await conn.fetch("SELECT ServerID FROM Server")
            logger.info(f"Found {len(servers)} server entries in the database.")
            
            # Complete cleanup - drop and recreate the Server table with correct entries
            logger.info("Performing complete server table cleanup...")
            
            # Create a temporary table to hold the cleaned data
            await conn.execute("""
            CREATE TEMP TABLE CleanedServer (
                ServerID TEXT PRIMARY KEY,
                status TEXT,
                last_request TIMESTAMPTZ,
                events_returned INTEGER DEFAULT 0,
                new_events INTEGER DEFAULT 0,
                error_messages TEXT
            )
            """)
            
            # Process and migrate data for each region
            for region, short_id in REGION_TO_ID.items():
                # Try to find the best entry for this region (either the short ID or the full name)
                server_data = await conn.fetchrow("""
                SELECT * FROM Server 
                WHERE LOWER(ServerID) = $1 OR LOWER(ServerID) = $2
                ORDER BY last_request DESC NULLS LAST
                LIMIT 1
                """, short_id.lower(), region.lower())
                
                if server_data:
                    # Use the data but with the correct short ID
                    await conn.execute("""
                    INSERT INTO CleanedServer (ServerID, status, last_request, events_returned, new_events, error_messages)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """, 
                    short_id, 
                    server_data['status'], 
                    server_data['last_request'],
                    server_data['events_returned'],
                    server_data['new_events'],
                    server_data['error_messages'])
                    
                    logger.info(f"Migrated data for region {region} -> {short_id}")
                else:
                    # Insert a new entry with default values
                    await conn.execute("""
                    INSERT INTO CleanedServer (ServerID) VALUES ($1)
                    """, short_id)
                    logger.info(f"Created new entry for missing region {short_id}")
            
            # Update all references in the time series tables
            for region, short_id in REGION_TO_ID.items():
                # Update ServerTimeSeries
                await conn.execute("""
                UPDATE ServerTimeSeries 
                SET ServerID = $1
                WHERE LOWER(ServerID) = $2 OR LOWER(ServerID) = $3
                """, short_id, short_id.lower(), region.lower())
                
                # Update NotableEventsTimeSeries
                await conn.execute("""
                UPDATE NotableEventsTimeSeries 
                SET region = $1
                WHERE LOWER(region) = $2 OR LOWER(region) = $3
                """, short_id, short_id.lower(), region.lower())
                
                logger.info(f"Updated all references for {region} -> {short_id}")
            
            # Drop the original Server table and rename the cleaned one
            await conn.execute("DROP TABLE Server CASCADE")
            await conn.execute("ALTER TABLE CleanedServer RENAME TO Server")
            
            # Recreate the foreign key constraint
            await conn.execute("""
            ALTER TABLE ServerTimeSeries 
            ADD CONSTRAINT fk_server FOREIGN KEY (ServerID) REFERENCES Server(ServerID)
            """)
            
            final_count = await conn.fetchval("SELECT COUNT(*) FROM Server")
            logger.info(f"Server table cleanup complete. Now have {final_count} unique server entries.")
            
    except Exception as e:
        logger.error(f"Error during server table cleanup: {e}", exc_info=True)

async def main():
    """Main function to run the cleanup script."""
    try:
        logger.info("Initializing database pool...")
        await initialize_db_pool(DATABASE_URL)
        logger.info("Database pool initialized.")
        
        await cleanup_server_table()
        
    except Exception as e:
        logger.error(f"Error in cleanup script: {e}", exc_info=True)
    finally:
        logger.info("Closing database pool...")
        await close_db_pool()

if __name__ == "__main__":
    asyncio.run(main()) 