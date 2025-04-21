import asyncio
import json
import os
import asyncpg

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

async def mark_events_as_unsent(json_file_path):
    """Mark all events from the European events JSON file as unsent in Discord and set region to 'eu'."""
    print(f"Loading events from {json_file_path}...")
    
    # Check if file exists
    if not os.path.exists(json_file_path):
        print(f"Error: File {json_file_path} not found.")
        return False
    
    # Load JSON data
    try:
        with open(json_file_path, 'r') as file:
            data = json.load(file)
        
        # Extract event IDs from the JSON structure
        event_ids = []
        if '_embedded' in data and 'events' in data['_embedded']:
            events = data['_embedded']['events']
            for event in events:
                event_ids.append(event['id'])
        
        print(f"Found {len(event_ids)} events in the JSON file.")
        
        if not event_ids:
            print("No events found in the JSON file.")
            return False
        
        # Connect directly to the database
        print(f"Connecting to database...")
        conn = await asyncpg.connect(DATABASE_URL)
        
        try:
            # Get the actual events table name
            events_table = await get_table_name(conn, 'events')
            
            if not events_table:
                print("Error: Events table not found.")
                return False
            
            print(f"Using events table: {events_table}")
            
            # Update events to mark them as unsent and set region to 'eu'
            update_count = 0
            for event_id in event_ids:
                result = await conn.execute(f"""
                UPDATE {events_table}
                SET sentToDiscord = FALSE, region = 'eu'
                WHERE eventID = $1
                """, event_id)
                
                if result and result != "UPDATE 0":
                    update_count += 1
            
            print(f"Successfully marked {update_count} out of {len(event_ids)} events as unsent and set region to 'eu'.")
            
            if update_count < len(event_ids):
                print(f"Note: {len(event_ids) - update_count} events were not found in the database.")
            
            return True
            
        finally:
            await conn.close()
            print("Database connection closed.")
            
    except json.JSONDecodeError:
        print(f"Error: {json_file_path} is not a valid JSON file.")
        return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

async def main():
    """Main function to run the script."""
    json_file_path = "european_events.json"
    
    print("Script to mark European events as unsent in Discord and set region to 'eu'")
    print("=========================================================================")
    
    success = await mark_events_as_unsent(json_file_path)
    
    if success:
        print("Operation completed successfully.")
    else:
        print("Operation failed.")

if __name__ == "__main__":
    asyncio.run(main()) 