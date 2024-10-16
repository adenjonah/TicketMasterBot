import requests
import os
import time
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve Ticketmaster API key from environment variable
API_KEY = os.getenv('TICKETMASTER_API_KEY')
if not API_KEY:
    raise ValueError("Ticketmaster API key not found. Please ensure it's set in the .env file.")

def get_events(start_date, end_date):
    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {
        "apikey": API_KEY,
        "startDateTime": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDateTime": end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "size": 200  # Adjust as needed
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        return response.json().get("_embedded", {}).get("events", [])
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return []

def alert_new_events(events):
    for event in events:
        print(f"New event: {event['name']} on {event['dates']['start']['localDate']}")

def main():
    known_events = set()
    check_interval = 65  # 1 minute

    while True:
        now = datetime.now(timezone.utc)
        end_date = now + timedelta(days=30)  # Look for events in the next 30 days
        
        events = get_events(now, end_date)
        new_events = []
        
        for event in events:
            event_id = event['id']
            if event_id not in known_events:
                known_events.add(event_id)
                new_events.append(event)
        
        if new_events:
            alert_new_events(new_events)
        else:
            print("No new events found.")
        
        print(f"Sleeping for {check_interval} seconds...")
        time.sleep(check_interval)

if __name__ == "__main__":
    main()