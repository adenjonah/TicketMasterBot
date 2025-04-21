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

async def cleanup_server_table():
    """Clean up the Server table by removing duplicates and standardizing IDs."""
    logger.info("Starting server table cleanup...")
    
    try:
        # Get all servers currently in the database
        async with db_pool.acquire() as conn:
            # Get the server table name with case sensitivity
            server_table = await get_table_name(conn, 'server')
            
            if not server_table:
                logger.error("Server table not found. Cannot proceed with cleanup.")
                # List all available tables
                tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                """)
                logger.info(f"Available tables: {[t['table_name'] for t in tables]}")
                
                # Create Server table if it doesn't exist
                logger.info("Creating Server table...")
                await conn.execute("""
                CREATE TABLE Server (
                    ServerID TEXT PRIMARY KEY,
                    status TEXT,
                    last_request TIMESTAMPTZ,
                    events_returned INTEGER DEFAULT 0,
                    new_events INTEGER DEFAULT 0,
                    error_messages TEXT
                )
                """)
                server_table = "Server"
                logger.info("Server table created.")
            
            # Get the time series table name
            time_series_table = await get_table_name(conn, 'servertimeseries')
            notable_table = await get_table_name(conn, 'notableeventstimeseries')
            
            logger.info(f"Using tables: Server={server_table}, TimeSeries={time_series_table}, Notable={notable_table}")
            
            # First, drop foreign key if it exists
            if time_series_table:
                try:
                    await conn.execute(f"""
                    ALTER TABLE {time_series_table} DROP CONSTRAINT IF EXISTS fk_server;
                    """)
                    logger.info("Dropped foreign key constraints temporarily")
                except Exception as e:
                    logger.warning(f"Could not drop foreign key constraint: {e}")
            
            # Get existing server IDs
            servers = await conn.fetch(f"SELECT * FROM {server_table}")
            logger.info(f"Found {len(servers)} server entries in the database.")
            
            # Process and migrate legacy IDs
            for legacy_id, short_id in REGION_TO_ID.items():
                # Check if legacy ID exists (case insensitive)
                legacy_exists = False
                legacy_row = None
                
                for row in servers:
                    if row['serverid'].lower() == legacy_id.lower():
                        legacy_exists = True
                        legacy_row = row
                        break
                
                if legacy_exists:
                    logger.info(f"Found legacy server ID: {legacy_id} - migrating to {short_id}")
                    
                    # Check if short ID exists
                    short_exists = False
                    short_row = None
                    
                    for row in servers:
                        if row['serverid'].lower() == short_id.lower():
                            short_exists = True
                            short_row = row
                            break
                    
                    if short_exists:
                        # Update short ID with legacy data if legacy has newer data
                        if legacy_row['last_request'] and (not short_row['last_request'] or legacy_row['last_request'] > short_row['last_request']):
                            await conn.execute(f"""
                            UPDATE {server_table}
                            SET status = $1, last_request = $2, events_returned = $3, new_events = $4, error_messages = $5
                            WHERE LOWER(ServerID) = $6
                            """,
                            legacy_row['status'],
                            legacy_row['last_request'],
                            legacy_row['events_returned'],
                            legacy_row['new_events'],
                            legacy_row['error_messages'],
                            short_id.lower())
                            
                            logger.info(f"Updated {short_id} with data from {legacy_id}")
                    else:
                        # Insert new short ID with legacy data
                        await conn.execute(f"""
                        INSERT INTO {server_table} (ServerID, status, last_request, events_returned, new_events, error_messages)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        short_id,
                        legacy_row['status'],
                        legacy_row['last_request'],
                        legacy_row['events_returned'],
                        legacy_row['new_events'],
                        legacy_row['error_messages'])
                        
                        logger.info(f"Created new entry {short_id} with data from {legacy_id}")
                    
                    # Update all references in ServerTimeSeries
                    if time_series_table:
                        await conn.execute(f"""
                        UPDATE {time_series_table}
                        SET ServerID = $1
                        WHERE LOWER(ServerID) = $2
                        """, short_id, legacy_id.lower())
                        
                        logger.info(f"Updated ServerTimeSeries references for {legacy_id} -> {short_id}")
                    
                    # Update references in NotableEventsTimeSeries
                    if notable_table:
                        await conn.execute(f"""
                        UPDATE {notable_table}
                        SET region = $1
                        WHERE LOWER(region) = $2
                        """, short_id, legacy_id.lower())
                        
                        logger.info(f"Updated NotableEventsTimeSeries references for {legacy_id} -> {short_id}")
                    
                    # Delete the legacy entry
                    await conn.execute(f"""
                    DELETE FROM {server_table}
                    WHERE LOWER(ServerID) = $1
                    """, legacy_id.lower())
                    
                    logger.info(f"Removed legacy ID: {legacy_id}")
            
            # Ensure all required IDs exist
            for region_id in REGION_TO_ID.values():
                exists = await conn.fetchval(f"""
                SELECT 1 FROM {server_table}
                WHERE LOWER(ServerID) = $1
                """, region_id.lower())
                
                if not exists:
                    logger.info(f"Adding missing server ID: {region_id}")
                    await conn.execute(f"""
                    INSERT INTO {server_table} (ServerID)
                    VALUES ($1)
                    """, region_id)
            
            # De-duplicate any servers that may have mixed case
            servers = await conn.fetch(f"SELECT * FROM {server_table}")
            seen_ids = {}
            
            for row in servers:
                server_id = row['serverid'].lower()
                
                if server_id in seen_ids:
                    # We already have this ID, keep only the one with the newest data
                    existing_row = seen_ids[server_id]
                    
                    if (row['last_request'] and 
                        (not existing_row['last_request'] or row['last_request'] > existing_row['last_request'])):
                        # Current row is newer, keep it and delete the existing one
                        logger.info(f"Found duplicate entry for {server_id}, keeping newer entry: {row['serverid']}")
                        
                        await conn.execute(f"""
                        DELETE FROM {server_table}
                        WHERE ServerID = $1
                        """, existing_row['serverid'])
                        
                        seen_ids[server_id] = row
                    else:
                        # Existing row is newer or same, delete current row
                        logger.info(f"Found duplicate entry for {server_id}, keeping entry: {existing_row['serverid']}")
                        
                        await conn.execute(f"""
                        DELETE FROM {server_table}
                        WHERE ServerID = $1
                        """, row['serverid'])
                else:
                    seen_ids[server_id] = row
            
            # Recreate foreign key constraint
            if time_series_table:
                try:
                    await conn.execute(f"""
                    ALTER TABLE {time_series_table}
                    ADD CONSTRAINT fk_server FOREIGN KEY (ServerID) REFERENCES {server_table}(ServerID)
                    """)
                    logger.info("Recreated foreign key constraint")
                except Exception as e:
                    logger.warning(f"Could not recreate foreign key constraint: {e}")
            
            # Get final server count
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {server_table}")
            logger.info(f"Cleanup complete. Server table now has {count} entries.")
            
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