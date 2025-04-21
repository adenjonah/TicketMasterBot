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
            # Get the actual table names (case-sensitive)
            server_table = await get_table_name(conn, 'server')
            time_series_table = await get_table_name(conn, 'servertimeseries')
            notable_table = await get_table_name(conn, 'notableeventstimeseries')
            
            if not server_table:
                logger.error("Server table not found")
                print("Available tables:")
                tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                """)
                for table in tables:
                    print(f"  - {table['table_name']}")
                return
                
            print(f"Found tables: {server_table}, {time_series_table}, {notable_table}")
            
            # Get server list before cleanup
            servers_before = await conn.fetch(f"SELECT * FROM {server_table}")
            print(f"Servers before cleanup: {[s['serverid'] for s in servers_before]}")
            
            if not time_series_table:
                logger.warning("ServerTimeSeries table not found, skipping foreign key operations")
            else:
                # Temporarily disable foreign key constraints
                try:
                    await conn.execute(f"ALTER TABLE {time_series_table} DROP CONSTRAINT IF EXISTS fk_server;")
                    logger.info("Dropped foreign key constraints temporarily")
                except Exception as e:
                    logger.warning(f"Could not drop foreign key constraint: {e}")
            
            # Process each legacy server ID
            for legacy_id in LEGACY_SERVER_IDS:
                short_id = SERVER_ID_MAP.get(legacy_id)
                
                # Check if the legacy server ID exists
                try:
                    legacy_exists = await conn.fetchval(
                        f"SELECT 1 FROM {server_table} WHERE LOWER(ServerID) = $1", 
                        legacy_id.lower()
                    )
                    
                    if not legacy_exists:
                        logger.info(f"Legacy server ID {legacy_id} not found. Skipping.")
                        continue
                    
                    print(f"Found legacy server ID: {legacy_id} - will migrate to {short_id}")
                    
                    # Check if the short ID already exists
                    short_exists = await conn.fetchval(
                        f"SELECT 1 FROM {server_table} WHERE LOWER(ServerID) = $1", 
                        short_id.lower()
                    )
                    
                    if short_exists:
                        # If both exist, migrate data from legacy to short if legacy has newer data
                        legacy_data = await conn.fetchrow(
                            f"SELECT * FROM {server_table} WHERE LOWER(ServerID) = $1",
                            legacy_id.lower()
                        )
                        
                        short_data = await conn.fetchrow(
                            f"SELECT * FROM {server_table} WHERE LOWER(ServerID) = $1",
                            short_id.lower()
                        )
                        
                        # Check if legacy has newer data
                        legacy_last_request = legacy_data['last_request']
                        short_last_request = short_data['last_request']
                        
                        if legacy_last_request and (not short_last_request or legacy_last_request > short_last_request):
                            logger.info(f"Updating {short_id} with newer data from {legacy_id}")
                            await conn.execute(f"""
                            UPDATE {server_table} 
                            SET status = $1, last_request = $2, events_returned = $3, new_events = $4, error_messages = $5
                            WHERE LOWER(ServerID) = $6
                            """,
                            legacy_data['status'],
                            legacy_data['last_request'],
                            legacy_data['events_returned'],
                            legacy_data['new_events'],
                            legacy_data['error_messages'],
                            short_id.lower())
                    else:
                        # Create the short ID entry with legacy data
                        legacy_data = await conn.fetchrow(
                            f"SELECT * FROM {server_table} WHERE LOWER(ServerID) = $1",
                            legacy_id.lower()
                        )
                        
                        print(f"Creating new entry for {short_id} with data from {legacy_id}")
                        await conn.execute(f"""
                        INSERT INTO {server_table} (ServerID, status, last_request, events_returned, new_events, error_messages)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        short_id,
                        legacy_data['status'],
                        legacy_data['last_request'],
                        legacy_data['events_returned'],
                        legacy_data['new_events'],
                        legacy_data['error_messages'])
                    
                    # Update all references in ServerTimeSeries
                    if time_series_table:
                        updated = await conn.execute(f"""
                        UPDATE {time_series_table} 
                        SET ServerID = $1
                        WHERE LOWER(ServerID) = $2
                        """, short_id, legacy_id.lower())
                        print(f"Updated ServerTimeSeries references: {updated}")
                    
                    # Update references in NotableEventsTimeSeries
                    if notable_table:
                        updated = await conn.execute(f"""
                        UPDATE {notable_table} 
                        SET region = $1
                        WHERE LOWER(region) = $2
                        """, short_id, legacy_id.lower())
                        print(f"Updated NotableEventsTimeSeries references: {updated}")
                    
                    # Delete the legacy entry
                    await conn.execute(
                        f"DELETE FROM {server_table} WHERE LOWER(ServerID) = $1",
                        legacy_id.lower()
                    )
                    
                    logger.info(f"Migrated data from {legacy_id} to {short_id} and deleted legacy entry")
                
                except Exception as e:
                    logger.error(f"Error processing server ID {legacy_id}: {e}")
                    print(f"Error processing {legacy_id}: {e}")
                
            # Recreate foreign key constraint
            if time_series_table:
                try:
                    await conn.execute(f"""
                    ALTER TABLE {time_series_table} 
                    ADD CONSTRAINT fk_server FOREIGN KEY (ServerID) REFERENCES {server_table}(ServerID)
                    """)
                except Exception as e:
                    logger.warning(f"Could not recreate foreign key constraint: {e}")
            
            # Count remaining servers
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {server_table}")
            servers_after = await conn.fetch(f"SELECT * FROM {server_table}")
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