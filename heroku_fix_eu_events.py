#!/usr/bin/env python
import asyncio
import asyncpg
import sys
import os

# Use the environment variable DATABASE_URL from Heroku
DATABASE_URL = os.environ.get('DATABASE_URL')

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

async def fix_eu_events():
    """Fix European events by ensuring their region is consistently 'eu' and they're marked as unsent."""
    print("Fixing European events in Heroku database...")
    
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL environment variable not set.")
        return False
    
    try:
        # Connect to the database
        print(f"Connecting to database...")
        conn = await asyncpg.connect(DATABASE_URL)
        
        try:
            # Get the actual events table name
            events_table = await get_table_name(conn, 'events')
            
            if not events_table:
                print("Error: Events table not found.")
                return False
            
            print(f"Using events table: {events_table}")
            
            # Check if the region column exists
            columns = await conn.fetch("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = $1
            """, events_table)
            
            column_names = [col['column_name'].lower() for col in columns]
            print(f"Existing columns in events table: {column_names}")
            
            if 'region' not in column_names:
                print("Region column does not exist in the events table. Creating it now...")
                await conn.execute(f"""
                ALTER TABLE {events_table}
                ADD COLUMN region TEXT
                """)
                print("Region column added successfully!")
            
            # Check current region distribution
            region_counts = await conn.fetch(f"""
            SELECT region, COUNT(*) 
            FROM {events_table} 
            GROUP BY region
            ORDER BY COUNT(*) DESC
            """)
            
            print("\nCurrent region distribution:")
            for row in region_counts:
                print(f"  {row['region'] or 'NULL'}: {row['count']}")
            
            # Fix any capitalization issues with EU regions
            updated_regions = await conn.execute(f"""
            UPDATE {events_table}
            SET region = 'eu'
            WHERE region IN ('EU', 'Eu', 'eU', 'europe', 'Europe', 'EUROPE')
            """)
            
            print(f"Fixed capitalization for {updated_regions.split()[1] if 'UPDATE' in updated_regions else 0} European events.")
            
            # Force all European events to be unsent
            updated_count = await conn.execute(f"""
            UPDATE {events_table}
            SET sentToDiscord = FALSE
            WHERE LOWER(region) = 'eu'
            """)
            
            print(f"Marked {updated_count.split()[1] if 'UPDATE' in updated_count else 0} European events as unsent.")
            
            # Report the number of EU events
            eu_count = await conn.fetchval(f"""
            SELECT COUNT(*) 
            FROM {events_table} 
            WHERE LOWER(region) = 'eu'
            """)
            
            print(f"\nTotal European events count: {eu_count}")
            
            # Check if any events with unsent flag are EU events
            unsent_eu_count = await conn.fetchval(f"""
            SELECT COUNT(*) 
            FROM {events_table} 
            WHERE sentToDiscord = FALSE AND LOWER(region) = 'eu'
            """)
            
            print(f"Unsent European events count: {unsent_eu_count}")
            
            # Print sample of European events
            if unsent_eu_count > 0:
                sample_events = await conn.fetch(f"""
                SELECT eventID, name, region, sentToDiscord
                FROM {events_table}
                WHERE LOWER(region) = 'eu' AND sentToDiscord = FALSE
                LIMIT 5
                """)
                
                print("\nSample of unsent European events:")
                for event in sample_events:
                    print(f"  ID: {event['eventid']}, Name: {event['name']}, Region: {event['region']}, Sent: {event['senttodiscord']}")
            
            print("\nDatabase update completed successfully.")
            return True
            
        finally:
            await conn.close()
            print("Database connection closed.")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

async def main():
    """Main function to run the script."""
    print("Script to fix European events in Heroku database")
    print("==============================================")
    
    success = await fix_eu_events()
    
    if success:
        print("Operation completed successfully.")
    else:
        print("Operation failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 