#!/usr/bin/env python
import asyncio
import asyncpg
import sys

# Define the database URL directly
DATABASE_URL = "postgres://u5uo83vleju7gr:p074eeaa2af2fea64b9daeda66b597fb6695dafe27e08e1d1ed36c6137f95b67e@c3nv2ev86aje4j.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d7qqd953vljjbn"

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
    """Fix European events by ensuring they're marked as unsent with region='eu'."""
    print("Fixing European events...")
    
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
            
            # Count how many events currently have region set to 'eu'
            eu_count = await conn.fetchval(f"""
            SELECT COUNT(*) 
            FROM {events_table} 
            WHERE LOWER(region) = 'eu'
            """)
            
            print(f"Current European events count: {eu_count}")
            
            # Force update EU events to be unsent
            updated_count = await conn.execute(f"""
            UPDATE {events_table}
            SET sentToDiscord = FALSE
            WHERE LOWER(region) = 'eu'
            """)
            
            print(f"Updated {updated_count.split()[1]} European events to be unsent.")
            
            # Check if any events with unsent flag are EU events
            unsent_eu_count = await conn.fetchval(f"""
            SELECT COUNT(*) 
            FROM {events_table} 
            WHERE sentToDiscord = FALSE AND LOWER(region) = 'eu'
            """)
            
            print(f"\nUnsent European events count: {unsent_eu_count}")
            
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
    print("Script to fix European events")
    print("============================")
    
    success = await fix_eu_events()
    
    if success:
        print("Operation completed successfully.")
    else:
        print("Operation failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 