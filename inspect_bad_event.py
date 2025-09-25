import asyncio
import aiohttp
import json
import urllib.parse
import os
import sys
from datetime import datetime, timezone

# Add the current directory to the Python path so we can import from config
sys.path.append('.')

# Event ID from the error logs
PROBLEMATIC_EVENT_ID = "1AsZk19Gkd3D7VP"

# Import API key from config
try:
    from config.config import TICKETMASTER_API_KEY
    API_KEY = TICKETMASTER_API_KEY
    print(f"Using API key from config: {API_KEY[:5]}...")
except ImportError:
    # Fallback to environment or default
    API_KEY = os.environ.get("TICKETMASTER_API_KEY", "YOUR_API_KEY")
    print(f"Using API key from environment: {API_KEY[:5] if len(API_KEY) > 5 else 'not set'}...")

async def fetch_event_details(event_id):
    """Fetch detailed information about a specific event, including its URL"""
    base_url = f"https://app.ticketmaster.com/discovery/v2/events/{event_id}"
    params = {
        "apikey": API_KEY,
    }
    
    full_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    print(f"Fetching event from: {base_url}")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(full_url) as response:
            if response.status == 200:
                event_data = await response.json()
                return event_data
            else:
                response_text = await response.text()
                print(f"Error fetching event: {response.status}")
                print(f"Response: {response_text[:200]}...")
                return None

async def inspect_problematic_event():
    """Fetch and inspect the problematic event"""
    event_data = await fetch_event_details(PROBLEMATIC_EVENT_ID)
    
    if not event_data:
        print("Could not fetch event data")
        
        # Try alternate approach - fetch from the Ticketmaster website 
        print("\nAttempting to check URL directly...")
        tm_url = f"https://www.ticketmaster.com/event/{PROBLEMATIC_EVENT_ID}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(tm_url, allow_redirects=True) as response:
                    print(f"Direct URL check status: {response.status}")
                    if response.ok:
                        final_url = str(response.url)
                        print(f"URL resolves to: {final_url}")
                        print("URL appears to be valid for this event ID")
                        return
            except Exception as e:
                print(f"Error checking direct URL: {e}")
        
        # Try alternate approach - look in your database
        print("\nLet's check your local database for this event...")
        try:
            import asyncpg
            from config.config import DATABASE_URL
            
            conn = await asyncpg.connect(DATABASE_URL)
            result = await conn.fetchrow("SELECT eventID, name, url FROM Events WHERE eventID = $1", PROBLEMATIC_EVENT_ID)
            
            if result:
                print("\n=== EVENT FROM DATABASE ===")
                print(f"Event ID: {result['eventid']}")
                print(f"Event Name: {result['name']}")
                url = result.get('url', 'No URL found')
                print(f"URL in database: '{url}'")
                
                # Analyze the URL from the database
                print("\n=== DATABASE URL ANALYSIS ===")
                if not url:
                    print("URL is empty or None")
                else:
                    print(f"URL length: {len(url)}")
                    has_control_chars = any(ord(c) < 32 or ord(c) == 127 for c in url)
                    print(f"Contains control characters: {has_control_chars}")
                    
                    if has_control_chars:
                        print("Control characters in URL:")
                        for i, c in enumerate(url):
                            if ord(c) < 32 or ord(c) == 127:
                                print(f"Position {i}: Character '{c}' (ASCII {ord(c)})")
            else:
                print("Event not found in your database")
            
            await conn.close()
        except Exception as e:
            print(f"Error checking database: {e}")
        
        return
    
    # Print basic event info
    print("\n=== EVENT DETAILS ===")
    print(f"Event ID: {event_data.get('id')}")
    print(f"Event Name: {event_data.get('name')}")
    
    # Print URL information (the problematic field)
    print("\n=== URL DETAILS ===")
    url = event_data.get('url', 'No URL found')
    print(f"URL in API response: '{url}'")
    
    # Analyze URL issues
    print("\n=== URL ANALYSIS ===")
    if not url:
        print("URL is empty or None")
    else:
        print(f"URL length: {len(url)}")
        
        # Check for problematic characters
        has_control_chars = any(ord(c) < 32 or ord(c) == 127 for c in url)
        print(f"Contains control characters: {has_control_chars}")
        
        if has_control_chars:
            print("Control characters in URL:")
            for i, c in enumerate(url):
                if ord(c) < 32 or ord(c) == 127:
                    print(f"Position {i}: Character '{c}' (ASCII {ord(c)})")
        
        # Attempt to parse with urllib
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            print(f"Scheme: '{parsed.scheme}'")
            print(f"Netloc: '{parsed.netloc}'")
            print(f"Path: '{parsed.path}'")
            print(f"Query: '{parsed.query}'")
            print(f"Fragment: '{parsed.fragment}'")
            
            # Check if URL meets basic requirements
            valid = bool(parsed.scheme and parsed.netloc)
            print(f"URL meets basic requirements: {valid}")
        except Exception as e:
            print(f"Error parsing URL: {e}")
    
    # Print URL for ticketmaster.com with event ID as fallback
    fallback_url = f"https://www.ticketmaster.com/event/{PROBLEMATIC_EVENT_ID}"
    print(f"\nFallback URL: {fallback_url}")
    
    # Save full event data to file for detailed inspection
    with open(f"event_{PROBLEMATIC_EVENT_ID}.json", "w") as f:
        json.dump(event_data, f, indent=2)
    print(f"\nFull event data saved to event_{PROBLEMATIC_EVENT_ID}.json")

if __name__ == "__main__":
    asyncio.run(inspect_problematic_event()) 