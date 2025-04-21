#!/usr/bin/env python
import asyncio
import json
import asyncpg
import os
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

async def check_and_update_regions():
    """Check and update region field for European events."""
    print("Checking and updating region field for European events...")
    
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
            
            # Load European events JSON file
            json_file_path = "european_events.json"
            if os.path.exists(json_file_path):
                with open(json_file_path, 'r') as file:
                    data = json.load(file)
                
                # Extract event IDs from the JSON structure
                event_ids = []
                if '_embedded' in data and 'events' in data['_embedded']:
                    events = data['_embedded']['events']
                    for event in events:
                        event_ids.append(event['id'])
                
                print(f"Found {len(event_ids)} events in the European events JSON file.")
                
                # Update these events to have region='eu'
                update_count = 0
                for event_id in event_ids:
                    result = await conn.execute(f"""
                    UPDATE {events_table}
                    SET region = 'eu'
                    WHERE eventID = $1
                    """, event_id)
                    
                    if result and result != "UPDATE 0":
                        update_count += 1
                
                print(f"Updated region for {update_count} out of {len(event_ids)} European events.")
            else:
                print(f"Warning: European events JSON file not found at {json_file_path}.")
            
            # Print current region distribution
            region_counts = await conn.fetch(f"""
            SELECT region, COUNT(*) 
            FROM {events_table} 
            GROUP BY region
            ORDER BY COUNT(*) DESC
            """)
            
            print("\nCurrent region distribution:")
            for row in region_counts:
                print(f"  {row['region'] or 'NULL'}: {row['count']}")
            
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
            
            print("\nDatabase check completed successfully.")
            return True
            
        finally:
            await conn.close()
            print("Database connection closed.")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

async def main():
    """Main function to run the script."""
    print("Script to check and update European regions")
    print("==========================================")
    
    success = await check_and_update_regions()
    
    if success:
        print("Operation completed successfully.")
    else:
        print("Operation failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 