import asyncio
import os
import sys
from config.db_pool import initialize_db_pool, close_db_pool
from config.config import DATABASE_URL
from config.logging import logger

# List of legacy server IDs to drop
LEGACY_SERVER_IDS = [
    'comedy',
    'europe',
    'north',
    'west', 
    'east',
    'south'
]

# Map of legacy server IDs to their new short IDs
SERVER_ID_MAP = {
    'comedy': 'co',
    'europe': 'eu',
    'north': 'no',
    'west': 'we',
    'east': 'ea',
    'south': 'so'
}

async def migrate_and_drop_legacy_servers():
    """Migrate data from legacy servers to new format and drop the legacy entries"""
    try:
        # Print diagnostic info about the environment
        print(f"Python version: {sys.version}")
        print(f"Working directory: {os.getcwd()}")
        print(f"DATABASE_URL available: {'Yes' if DATABASE_URL else 'No'}")
        if DATABASE_URL:
            masked_url = DATABASE_URL[:15] + "..." + DATABASE_URL[-5:] if len(DATABASE_URL) > 25 else DATABASE_URL
            print(f"Database URL: {masked_url}")
        
        # Initialize database pool
        await initialize_db_pool(DATABASE_URL)
        logger.info("Database pool initialized.")
        
        from config.db_pool import db_pool
        if not db_pool:
            logger.error("Database pool is None after initialization")
            return
            
        async with db_pool.acquire() as conn:
            # Get server list before cleanup
            servers_before = await conn.fetch("SELECT ServerID FROM Server")
            print(f"Servers before cleanup: {[s['serverid'] for s in servers_before]}")
            
            # Temporarily disable foreign key constraints
            await conn.execute("ALTER TABLE ServerTimeSeries DROP CONSTRAINT IF EXISTS fk_server;")
            logger.info("Dropped foreign key constraints temporarily")
            
            # Process each legacy server ID
            for legacy_id in LEGACY_SERVER_IDS:
                short_id = SERVER_ID_MAP.get(legacy_id)
                
                # Check if the legacy server ID exists
                legacy_exists = await conn.fetchval(
                    "SELECT 1 FROM Server WHERE ServerID = $1", 
                    legacy_id
                )
                
                if not legacy_exists:
                    logger.info(f"Legacy server ID {legacy_id} not found. Skipping.")
                    continue
                
                print(f"Found legacy server ID: {legacy_id} - will migrate to {short_id}")
                
                # Check if the short ID already exists
                short_exists = await conn.fetchval(
                    "SELECT 1 FROM Server WHERE ServerID = $1", 
                    short_id
                )
                
                if short_exists:
                    # If both exist, migrate data from legacy to short if legacy has newer data
                    legacy_data = await conn.fetchrow(
                        "SELECT * FROM Server WHERE ServerID = $1",
                        legacy_id
                    )
                    
                    short_data = await conn.fetchrow(
                        "SELECT * FROM Server WHERE ServerID = $1",
                        short_id
                    )
                    
                    # Check if legacy has newer data
                    legacy_last_request = legacy_data['last_request']
                    short_last_request = short_data['last_request']
                    
                    if legacy_last_request and (not short_last_request or legacy_last_request > short_last_request):
                        logger.info(f"Updating {short_id} with newer data from {legacy_id}")
                        await conn.execute("""
                        UPDATE Server 
                        SET status = $1, last_request = $2, events_returned = $3, new_events = $4, error_messages = $5
                        WHERE ServerID = $6
                        """,
                        legacy_data['status'],
                        legacy_data['last_request'],
                        legacy_data['events_returned'],
                        legacy_data['new_events'],
                        legacy_data['error_messages'],
                        short_id)
                else:
                    # Create the short ID entry with legacy data
                    legacy_data = await conn.fetchrow(
                        "SELECT * FROM Server WHERE ServerID = $1",
                        legacy_id
                    )
                    
                    print(f"Creating new entry for {short_id} with data from {legacy_id}")
                    await conn.execute("""
                    INSERT INTO Server (ServerID, status, last_request, events_returned, new_events, error_messages)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    short_id,
                    legacy_data['status'],
                    legacy_data['last_request'],
                    legacy_data['events_returned'],
                    legacy_data['new_events'],
                    legacy_data['error_messages'])
                
                # Update all references in ServerTimeSeries
                updated = await conn.execute("""
                UPDATE ServerTimeSeries 
                SET ServerID = $1
                WHERE ServerID = $2
                """, short_id, legacy_id)
                print(f"Updated ServerTimeSeries references: {updated}")
                
                # Update references in NotableEventsTimeSeries
                updated = await conn.execute("""
                UPDATE NotableEventsTimeSeries 
                SET region = $1
                WHERE region = $2
                """, short_id, legacy_id)
                print(f"Updated NotableEventsTimeSeries references: {updated}")
                
                # Delete the legacy entry
                await conn.execute(
                    "DELETE FROM Server WHERE ServerID = $1",
                    legacy_id
                )
                
                logger.info(f"Migrated data from {legacy_id} to {short_id} and deleted legacy entry")
                
            # Recreate foreign key constraint
            await conn.execute("""
            ALTER TABLE ServerTimeSeries 
            ADD CONSTRAINT fk_server FOREIGN KEY (ServerID) REFERENCES Server(ServerID)
            """)
            
            # Count remaining servers
            count = await conn.fetchval("SELECT COUNT(*) FROM Server")
            servers_after = await conn.fetch("SELECT ServerID FROM Server")
            print(f"Servers after cleanup: {[s['serverid'] for s in servers_after]}")
            logger.info(f"Cleanup complete. Server table now has {count} entries.")
            
    except Exception as e:
        logger.error(f"Error in server cleanup: {e}", exc_info=True)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_db_pool()
        logger.info("Database pool closed.")

if __name__ == "__main__":
    print("Starting legacy server cleanup...")
    asyncio.run(migrate_and_drop_legacy_servers())
    print("Legacy server cleanup completed.") 