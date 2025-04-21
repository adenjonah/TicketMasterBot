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
            servers = await conn.fetch("SELECT ServerID FROM Server")
            logger.info(f"Found {len(servers)} server entries in the database.")
            
            # Step 1: Fix any full names to use short IDs
            for server in servers:
                server_id = server['serverid'].lower()
                if server_id in REGION_TO_ID.keys():
                    new_id = REGION_TO_ID[server_id]
                    logger.info(f"Converting full name {server_id} to short ID {new_id}")
                    
                    # Update all references in ServerTimeSeries first
                    await conn.execute(
                        "UPDATE ServerTimeSeries SET ServerID = $1 WHERE ServerID = $2",
                        new_id, server_id
                    )
                    
                    # Update references in NotableEventsTimeSeries
                    await conn.execute(
                        "UPDATE NotableEventsTimeSeries SET region = $1 WHERE region = $2",
                        new_id, server_id
                    )
                    
                    # Delete the old entry from Server
                    await conn.execute(
                        "DELETE FROM Server WHERE ServerID = $1",
                        server_id
                    )
            
            # Step 2: Get the current list of server IDs after fixing full names
            servers = await conn.fetch("SELECT ServerID FROM Server")
            seen_ids = set()
            duplicates = []
            
            # Find duplicates
            for server in servers:
                server_id = server['serverid'].lower()
                if server_id in seen_ids:
                    duplicates.append(server_id)
                else:
                    seen_ids.add(server_id)
            
            if duplicates:
                logger.info(f"Found duplicate server IDs: {duplicates}")
                
                # Handle duplicates by keeping only one entry
                for dup in duplicates:
                    # Get all duplicate entries
                    dup_entries = await conn.fetch(
                        "SELECT ServerID, status, last_request FROM Server WHERE LOWER(ServerID) = $1 ORDER BY last_request DESC NULLS LAST",
                        dup
                    )
                    
                    # Keep the most recent one (first in sorted list)
                    if len(dup_entries) > 1:
                        keep_id = dup_entries[0]['serverid']
                        logger.info(f"Keeping server ID: {keep_id}")
                        
                        # Remove the others
                        for i in range(1, len(dup_entries)):
                            remove_id = dup_entries[i]['serverid']
                            logger.info(f"Removing duplicate server ID: {remove_id}")
                            
                            # Update all references in ServerTimeSeries first
                            await conn.execute(
                                "UPDATE ServerTimeSeries SET ServerID = $1 WHERE ServerID = $2",
                                keep_id, remove_id
                            )
                            
                            # Update references in NotableEventsTimeSeries if needed
                            await conn.execute(
                                "UPDATE NotableEventsTimeSeries SET region = $1 WHERE region = $2",
                                keep_id, remove_id
                            )
                            
                            # Delete the duplicate entry from Server
                            await conn.execute(
                                "DELETE FROM Server WHERE ServerID = $1",
                                remove_id
                            )
            
            # Step 3: Ensure all required server IDs exist
            for region, short_id in REGION_TO_ID.items():
                # Check if the server ID exists
                exists = await conn.fetchval(
                    "SELECT 1 FROM Server WHERE ServerID = $1", 
                    short_id
                )
                
                if not exists:
                    logger.info(f"Adding missing server ID: {short_id} for region {region}")
                    await conn.execute(
                        "INSERT INTO Server (ServerID) VALUES ($1)",
                        short_id
                    )
            
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