import asyncio
import os
import sys
from config.db_pool import initialize_db_pool, close_db_pool
from config.config import DATABASE_URL
from config.logging import logger

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

async def fix_missing_server_table():
    """Check if the Server table exists and recreate it if missing."""
    try:
        # Print diagnostic info
        print(f"Python version: {sys.version}")
        print(f"Working directory: {os.getcwd()}")
        print(f"DATABASE_URL available: {'Yes' if DATABASE_URL else 'No'}")
        
        # Initialize database pool
        await initialize_db_pool(DATABASE_URL)
        logger.info("Database pool initialized.")
        
        from config.db_pool import db_pool
        if not db_pool:
            logger.error("Database pool is None after initialization")
            return
            
        async with db_pool.acquire() as conn:
            # List all tables
            print("Checking existing tables...")
            tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            """)
            
            table_names = [table['table_name'].lower() for table in tables]
            print(f"Found tables: {table_names}")
            
            # Check if Server table exists (case insensitive)
            server_exists = any(name == 'server' for name in table_names)
            
            if not server_exists:
                print("Server table is missing! Recreating it...")
                
                # Create Server table
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
                
                # Add default server IDs
                for region_id in REGION_TO_ID.values():
                    await conn.execute("""
                    INSERT INTO Server (ServerID)
                    VALUES ($1)
                    ON CONFLICT (ServerID) DO NOTHING
                    """, region_id)
                
                print("Server table created and populated with default IDs.")
                
                # Find all existing timestamps in ServerTimeSeries to migrate
                if 'servertimeseries' in table_names:
                    print("Migrating data from ServerTimeSeries to new Server table...")
                    
                    # Get the actual timeseries table name with correct case
                    timeseries_table = await conn.fetchval("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                      AND lower(table_name) = 'servertimeseries'
                    """)
                    
                    if timeseries_table:
                        # Get most recent data for each server ID
                        server_data = await conn.fetch(f"""
                        WITH ranked_data AS (
                            SELECT 
                                ServerID,
                                status,
                                timestamp as last_request,
                                events_returned,
                                new_events,
                                error_messages,
                                ROW_NUMBER() OVER (PARTITION BY LOWER(ServerID) ORDER BY timestamp DESC) as rn
                            FROM {timeseries_table}
                        )
                        SELECT * FROM ranked_data WHERE rn = 1
                        """)
                        
                        # Update Server table with this data
                        for row in server_data:
                            server_id = row['serverid']
                            
                            # Convert legacy IDs to short IDs
                            if server_id.lower() in REGION_TO_ID:
                                server_id = REGION_TO_ID[server_id.lower()]
                            elif any(server_id.lower() == short_id.lower() for short_id in REGION_TO_ID.values()):
                                # Keep the ID but ensure consistent case
                                for short_id in REGION_TO_ID.values():
                                    if server_id.lower() == short_id.lower():
                                        server_id = short_id
                                        break
                            
                            print(f"Updating Server table with data for {server_id}")
                            
                            await conn.execute("""
                            UPDATE Server
                            SET status = $1, last_request = $2, events_returned = $3, new_events = $4, error_messages = $5
                            WHERE LOWER(ServerID) = LOWER($6)
                            """,
                            row['status'],
                            row['last_request'],
                            row['events_returned'],
                            row['new_events'],
                            row['error_messages'],
                            server_id)
                
                # Add foreign key constraint if timeseries table exists
                if 'servertimeseries' in table_names:
                    timeseries_table = await conn.fetchval("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                      AND lower(table_name) = 'servertimeseries'
                    """)
                    
                    if timeseries_table:
                        try:
                            await conn.execute(f"""
                            ALTER TABLE {timeseries_table}
                            ADD CONSTRAINT fk_server FOREIGN KEY (ServerID) REFERENCES Server(ServerID)
                            """)
                            print(f"Added foreign key constraint to {timeseries_table}")
                        except Exception as e:
                            print(f"Error adding foreign key constraint: {e}")
            else:
                # Check if all required server IDs exist
                print("Server table exists, checking for required server IDs...")
                
                # Get the actual server table name with correct case
                server_table = await conn.fetchval("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                  AND lower(table_name) = 'server'
                """)
                
                # Get existing server IDs
                existing_ids = await conn.fetch(f"""
                SELECT ServerID FROM {server_table}
                """)
                
                existing_ids_lower = [row['serverid'].lower() for row in existing_ids]
                print(f"Existing server IDs: {[row['serverid'] for row in existing_ids]}")
                
                # Add any missing IDs
                for region_id in REGION_TO_ID.values():
                    if region_id.lower() not in existing_ids_lower:
                        print(f"Adding missing server ID: {region_id}")
                        await conn.execute(f"""
                        INSERT INTO {server_table} (ServerID)
                        VALUES ($1)
                        """, region_id)
                
                # Check for and remove legacy IDs
                for legacy_id, short_id in REGION_TO_ID.items():
                    legacy_exists = False
                    for row in existing_ids:
                        if row['serverid'].lower() == legacy_id.lower():
                            legacy_exists = True
                            break
                            
                    if legacy_exists:
                        print(f"Found legacy ID {legacy_id}, migrating to {short_id}")
                        
                        # Get legacy data
                        legacy_data = await conn.fetchrow(f"""
                        SELECT * FROM {server_table}
                        WHERE LOWER(ServerID) = LOWER($1)
                        """, legacy_id)
                        
                        # Update or insert short ID
                        short_exists = False
                        for row in existing_ids:
                            if row['serverid'].lower() == short_id.lower():
                                short_exists = True
                                break
                                
                        if short_exists:
                            # Update short ID with legacy data if newer
                            short_data = await conn.fetchrow(f"""
                            SELECT * FROM {server_table}
                            WHERE LOWER(ServerID) = LOWER($1)
                            """, short_id)
                            
                            if (legacy_data['last_request'] and 
                                (not short_data['last_request'] or 
                                legacy_data['last_request'] > short_data['last_request'])):
                                
                                await conn.execute(f"""
                                UPDATE {server_table}
                                SET status = $1, last_request = $2, events_returned = $3, new_events = $4, error_messages = $5
                                WHERE LOWER(ServerID) = LOWER($6)
                                """,
                                legacy_data['status'],
                                legacy_data['last_request'],
                                legacy_data['events_returned'],
                                legacy_data['new_events'],
                                legacy_data['error_messages'],
                                short_id)
                        else:
                            # Insert new short ID with legacy data
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
                        
                        # Delete legacy ID
                        await conn.execute(f"""
                        DELETE FROM {server_table}
                        WHERE LOWER(ServerID) = LOWER($1)
                        """, legacy_id)
                        
                        # Update references in timeseries table
                        timeseries_table = await conn.fetchval("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                          AND lower(table_name) = 'servertimeseries'
                        """)
                        
                        if timeseries_table:
                            await conn.execute(f"""
                            UPDATE {timeseries_table}
                            SET ServerID = $1
                            WHERE LOWER(ServerID) = LOWER($2)
                            """, short_id, legacy_id)
                
            # Verify final state
            server_table = await conn.fetchval("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND lower(table_name) = 'server'
            """)
            
            if server_table:
                final_ids = await conn.fetch(f"""
                SELECT * FROM {server_table}
                """)
                print(f"Final server IDs: {[row['serverid'] for row in final_ids]}")
                print("Server table verification successful!")
            else:
                print("ERROR: Server table is still missing after fix attempt!")
            
    except Exception as e:
        logger.error(f"Error fixing server table: {e}", exc_info=True)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_db_pool()
        logger.info("Database pool closed.")

async def main():
    """Main function to run the fix."""
    await fix_missing_server_table()

if __name__ == "__main__":
    print("Starting server table fix...")
    asyncio.run(main())
    print("Server table fix completed.") 