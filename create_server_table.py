import asyncio
import os
import sys
from config.db_pool import initialize_db_pool, close_db_pool
from config.config import DATABASE_URL
from config.logging import logger

# List of expected server IDs with short format
SERVER_IDS = [
    'no',  # North
    'ea',  # East
    'so',  # South
    'we',  # West
    'eu',  # Europe
    'co'   # Comedy/Theater/Film
]

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

async def create_server_table():
    """Create the Server table if it doesn't exist and populate with default ServerIDs."""
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
            # Get the list of existing tables
            print("Available tables:")
            tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            """)
            for table in tables:
                print(f"  - {table['table_name']}")
            
            # Check if Server table exists
            server_table = await get_table_name(conn, 'server')
            
            if server_table:
                print(f"Server table found: {server_table}")
                
                # Check if we have the expected ServerIDs
                rows = await conn.fetch(f"SELECT * FROM {server_table}")
                existing_ids = [row['serverid'].lower() for row in rows]
                print(f"Existing server IDs: {existing_ids}")
                
                # Add any missing server IDs
                for server_id in SERVER_IDS:
                    if server_id.lower() not in existing_ids:
                        print(f"Adding missing server ID: {server_id}")
                        await conn.execute(f"""
                        INSERT INTO {server_table} (ServerID)
                        VALUES ($1)
                        """, server_id)
                        
                # Show final server IDs
                rows = await conn.fetch(f"SELECT * FROM {server_table}")
                final_ids = [row['serverid'] for row in rows]
                print(f"Final server IDs: {final_ids}")
            else:
                print("Server table not found. Creating it...")
                
                # Create the Server table
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
                logger.info("Created Server table")
                
                # Add the default server IDs
                for server_id in SERVER_IDS:
                    await conn.execute("""
                    INSERT INTO Server (ServerID)
                    VALUES ($1)
                    """, server_id)
                
                logger.info(f"Added {len(SERVER_IDS)} default server IDs")
                
                # Show final server IDs
                rows = await conn.fetch("SELECT * FROM Server")
                final_ids = [row['serverid'] for row in rows]
                print(f"Final server IDs: {final_ids}")
                
                # Get the time series table if it exists
                time_series_table = await get_table_name(conn, 'servertimeseries')
                if time_series_table:
                    # Add foreign key constraint
                    try:
                        await conn.execute(f"""
                        ALTER TABLE {time_series_table} 
                        ADD CONSTRAINT fk_server FOREIGN KEY (ServerID) REFERENCES Server(ServerID)
                        """)
                        logger.info("Added foreign key constraint to ServerTimeSeries table")
                    except Exception as e:
                        logger.warning(f"Could not add foreign key constraint: {e}")
            
    except Exception as e:
        logger.error(f"Error in server table creation: {e}", exc_info=True)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_db_pool()
        logger.info("Database pool closed.")

if __name__ == "__main__":
    print("Starting server table check/creation...")
    asyncio.run(create_server_table())
    print("Server table check/creation completed.") 