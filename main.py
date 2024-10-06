import requests
from datetime import datetime, timezone
import sqlite3
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve Ticketmaster API key from environment variable
API_KEY = os.getenv('TICKETMASTER_API_KEY')
if not API_KEY:
    raise ValueError("Ticketmaster API key not found. Please ensure it's set in the .env file.")

BASE_URL = 'https://app.ticketmaster.com/discovery/v2/events.json'

# Set up the SQLite database for storing event details
conn = sqlite3.connect('seen_events.db')
cur = conn.cursor()

# Create a table if it doesn't exist to store seen event details
cur.execute('''CREATE TABLE IF NOT EXISTS seen_events (
    event_id TEXT PRIMARY KEY,
    name TEXT,
    sales_start TEXT,
    event_date TEXT,
    location TEXT
)''')
conn.commit()

# Function to check if an event ID is already in the database
def is_event_seen(event_id):
    cur.execute('SELECT 1 FROM seen_events WHERE event_id = ?', (event_id,))
    return cur.fetchone() is not None

# Function to mark an event as seen and store its details in the database
def mark_event_as_seen(event_id, name, sales_start, event_date, location):
    cur.execute('''
        INSERT OR IGNORE INTO seen_events (event_id, name, sales_start, event_date, location) 
        VALUES (?, ?, ?, ?, ?)''', (event_id, name, sales_start, event_date, location))
    conn.commit()

# Function to filter invalid sales dates (e.g., 1900-01-01)
def is_valid_sales_date(sales_start_dt):
    if sales_start_dt < datetime(2023, 1, 1, tzinfo=timezone.utc):  # Adjust as needed
        return False
    return True

# Function to fetch and process events
async def fetch_events(onsale_start_after, page_size=200):
    total_requested = 0
    total_received = 0
    already_seen = 0
    new_events_found = 0

    params = {
        'apikey': API_KEY,
        'countryCode': 'US',  # Filter for US events only
        'onsaleStartDateTime': onsale_start_after,  # Future sales start dates only
        'size': page_size,  # Maximize the size to get more events
        'sort': 'relevance,desc',  # Sort by relevance/popularity
        'classificationName': 'music, sports, festival'  # Filter by major event categories
    }

    print(f"Requesting events with onsaleStartDateTime after {onsale_start_after} and filtered by classification")

    response = requests.get(BASE_URL, params=params)

    # Check for a successful request
    if response.status_code == 200:
        data = response.json()
        events = data.get('_embedded', {}).get('events', [])

        total_requested += params['size']
        total_received += len(events)
        
        if events:
            print(f"Total events received: {len(events)}")
        else:
            print(f"No events received for onsaleStartDateTime after {onsale_start_after}")
            return None

        for event in events:
            event_id = event['id']

            # Check if the event has already been seen
            if is_event_seen(event_id):
                already_seen += 1
                continue

            # Get the public ticket sales start date
            sales_start = event['sales']['public'].get('startDateTime', None)
            event_name = event['name']
            event_location = event['_embedded']['venues'][0]['name']
            event_date = event['dates']['start'].get('localDate')

            if sales_start:
                # Convert the string to a datetime object and assign UTC timezone to make it aware
                sales_start_dt = datetime.strptime(sales_start, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)

                if sales_start_dt > datetime.now(timezone.utc) and is_valid_sales_date(sales_start_dt):
                    # Print new event details to the console
                    print(f"New Event: {event_name} at {event_location}")
                    print(f"Sales Start: {sales_start_dt}")
                    print(f"Event Date: {event_date}")
                    print('-' * 40)

                    # Mark the event as seen and store additional info
                    mark_event_as_seen(event_id, event_name, sales_start, event_date, event_location)

                    new_events_found += 1
                else:
                    print(f"Skipping {event_name} as it doesn't meet the sales start date criteria.")
            else:
                print(f"Skipping {event_name} as no sales start date found.")

        # Return the last event's onsaleStartDateTime for future requests
        last_event_sales_start = events[-1]['sales']['public']['startDateTime'] if events else None
        print(f"Last event's sales start datetime: {last_event_sales_start}")
        return last_event_sales_start

    else:
        print(f"Error: {response.status_code}, Message: {response.text}")
        return None

# Main function to continuously check for new events in batches
async def main():
    # Start the loop with the current time and incrementally fetch future events
    onsale_start_after = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    while True:
        print(f"Checking for events with onsale start after {onsale_start_after} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
        last_event_sales_start = await fetch_events(onsale_start_after)

        if not last_event_sales_start:
            print("No new events found or an error occurred.")
            break
        else:
            onsale_start_after = last_event_sales_start

        print("Waiting 60 seconds before starting the next cycle...")
        await asyncio.sleep(60)  # Wait for 60 seconds before starting the process again

# Run the event loop
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Script terminated by user.")

# Close the database connection when done
conn.close()