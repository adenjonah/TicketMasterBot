#!/usr/bin/env python
"""
Migration script to update server IDs from 'co' and 'th' to 'ctf' and handle the transition.
"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from config.logging import logger
from config.config import DATABASE_URL

async def update_server_ids():
    """Update server IDs from 'co' and 'th' to 'ctf'."""
    try:
        import asyncpg
        
        logger.info("Connecting to database for server ID migration...")
        conn = await asyncpg.connect(DATABASE_URL)
        
        try:
            # Start a transaction
            async with conn.transaction():
                # 1. Check if there are server entries for 'co' and 'th'
                server_check = await conn.fetch("""
                    SELECT ServerID, status, last_request, events_returned, new_events, error_messages  
                    FROM Server
                    WHERE ServerID IN ('co', 'th')
                """)
                
                if not server_check:
                    logger.info("No comedy or theater server entries found in the Server table.")
                else:
                    logger.info(f"Found {len(server_check)} server entries for comedy and/or theater.")
                    
                    # 2. Check if the 'ctf' server already exists
                    ctf_exists = await conn.fetchval("""
                        SELECT EXISTS(SELECT 1 FROM Server WHERE ServerID = 'ctf')
                    """)
                    
                    # 3. If 'ctf' doesn't exist but 'co' or 'th' does, create 'ctf' based on most recent data
                    if not ctf_exists and server_check:
                        # Find the most recent server between comedy and theater
                        most_recent = None
                        for server in server_check:
                            if most_recent is None or (server['last_request'] and (
                                most_recent['last_request'] is None or 
                                server['last_request'] > most_recent['last_request']
                            )):
                                most_recent = server
                        
                        if most_recent:
                            logger.info(f"Creating CTF server based on {most_recent['serverid']} server data")
                            
                            # Create the CTF server
                            await conn.execute("""
                                INSERT INTO Server (
                                    ServerID, status, last_request, events_returned, 
                                    new_events, error_messages
                                ) VALUES ($1, $2, $3, $4, $5, $6)
                            """, 
                            'ctf', most_recent['status'], most_recent['last_request'],
                            most_recent['events_returned'], most_recent['new_events'],
                            "Migrated from comedy/theater servers")
                            
                            logger.info("Created 'ctf' server entry.")
                    
                    # 4. Update events with server IDs 'co' or 'th' to use 'ctf'
                    events_updated = await conn.execute("""
                        UPDATE Events
                        SET region = 'ctf'
                        WHERE region IN ('co', 'th')
                    """)
                    
                    logger.info(f"Updated events from 'co'/'th' to 'ctf': {events_updated}")
                
                # 5. Update time series data
                timeseries_updated = await conn.execute("""
                    UPDATE ServerTimeSeries
                    SET ServerID = 'ctf'
                    WHERE ServerID IN ('co', 'th')
                """)
                
                logger.info(f"Updated server time series entries: {timeseries_updated}")
                
                notable_updated = await conn.execute("""
                    UPDATE NotableEventsTimeSeries
                    SET region = 'ctf'
                    WHERE region IN ('co', 'th')
                """)
                
                logger.info(f"Updated notable events time series entries: {notable_updated}")
                
                # 6. Add an entry to the time series table indicating the migration
                current_time = datetime.now(timezone.utc)
                hour_of_day = current_time.hour
                day_of_week = current_time.weekday()
                
                await conn.execute("""
                    INSERT INTO ServerTimeSeries 
                    (ServerID, timestamp, status, events_returned, new_events, 
                     hour_of_day, day_of_week, error_messages)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, 
                'ctf', current_time, 'Running', 0, 0, hour_of_day, day_of_week, 
                "Server ID migrated from comedy and theater to comedy-theatre-film (ctf)")
                
                logger.info("Added migration record to time series table.")
                
                # 7. Optionally, delete old server entries (commented out for safety)
                # Uncomment after verifying everything works correctly
                # await conn.execute("DELETE FROM Server WHERE ServerID IN ('co', 'th')")
                # logger.info("Deleted old comedy and theater server entries.")
                
            logger.info("Server ID migration completed successfully.")
            return True
        
        finally:
            await conn.close()
    
    except Exception as e:
        logger.error(f"Error during server ID migration: {str(e)}", exc_info=True)
        return False

async def main():
    """Main function to run the server ID migration."""
    print("Comedy/Theater to CTF Server ID Migration")
    print("=========================================")
    
    success = await update_server_ids()
    
    if success:
        print("Migration completed successfully.")
    else:
        print("Migration failed. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 