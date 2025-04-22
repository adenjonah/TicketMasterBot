#!/usr/bin/env python
"""
Test the country detection functionality for European venues
"""
import asyncio
import aiohttp
import json
from database.country_lookup import determine_country_from_venue, is_european_venue
import sys

# Sample venue data for testing
SAMPLE_VENUES = [
    {
        "description": "UK venue with country code and name",
        "data": {
            "name": "O2 Arena",
            "city": {"name": "London"},
            "state": {"name": "", "stateCode": ""},
            "country": {"name": "United Kingdom", "countryCode": "GB"}
        }
    },
    {
        "description": "European venue with only city",
        "data": {
            "name": "Olympia",
            "city": {"name": "Paris"},
            "state": {"name": "", "stateCode": ""},
            "country": {"name": "", "countryCode": ""}
        }
    },
    {
        "description": "Venue with only postal code",
        "data": {
            "name": "Secret Venue",
            "city": {"name": "Secret City"},
            "postalCode": "SW1A 1AA",  # UK postal code format
            "state": {"name": "", "stateCode": ""},
            "country": {"name": "", "countryCode": ""}
        }
    },
    {
        "description": "US venue for comparison",
        "data": {
            "name": "Madison Square Garden",
            "city": {"name": "New York"},
            "state": {"name": "New York", "stateCode": "NY"},
            "country": {"name": "United States Of America", "countryCode": "US"}
        }
    }
]

async def fetch_real_venue_from_api(api_key, venue_id):
    """Fetch a real venue from the Ticketmaster API for testing."""
    base_url = f"https://app.ticketmaster.com/discovery/v2/venues/{venue_id}"
    params = {"apikey": api_key}
    
    url = f"{base_url}?apikey={api_key}"
    print(f"Fetching venue data from: {url}")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                venue_data = await response.json()
                return venue_data
            else:
                print(f"Error fetching venue: Status {response.status}")
                return None

async def test_sample_venues():
    """Test country detection on sample venue data."""
    print("\n=== Testing Sample Venues ===")
    
    for venue in SAMPLE_VENUES:
        print(f"\nVenue: {venue['data']['name']} - {venue['description']}")
        
        is_european = is_european_venue(venue['data'])
        country = determine_country_from_venue(venue['data'])
        
        print(f"Is European: {is_european}")
        print(f"Detected Country: {country}")
        
        # Print raw data for debugging
        print(f"City: {venue['data'].get('city', {}).get('name')}")
        print(f"State/Region: {venue['data'].get('state', {}).get('name')} ({venue['data'].get('state', {}).get('stateCode')})")
        if 'country' in venue['data'] and venue['data']['country']:
            print(f"Country: {venue['data']['country'].get('name')} ({venue['data']['country'].get('countryCode')})")

async def test_real_venues(api_key):
    """Test country detection on real venues from Ticketmaster API."""
    if not api_key:
        print("No API key provided, skipping real venue tests")
        return
        
    print("\n=== Testing Real Venues ===")
    
    # List of venue IDs to test (European venues)
    venue_ids = [
        "KovZpZAFkvEA",  # Venue in London
        "Z598xZC91Ze7k",  # Venue in Paris
        "KGFSG8E2C8KAW"   # Venue in Berlin
    ]
    
    for venue_id in venue_ids:
        venue_data = await fetch_real_venue_from_api(api_key, venue_id)
        if venue_data:
            print(f"\nVenue: {venue_data.get('name', 'Unknown')} (ID: {venue_id})")
            
            is_european = is_european_venue(venue_data)
            country = determine_country_from_venue(venue_data)
            
            print(f"Is European: {is_european}")
            print(f"Detected Country: {country}")
            
            # Print raw venue data for verification
            if venue_data.get('city'):
                print(f"City: {venue_data['city'].get('name')}")
            if venue_data.get('state'):
                print(f"State/Region: {venue_data['state'].get('name')} ({venue_data['state'].get('stateCode')})")
            if venue_data.get('country'):
                print(f"Country: {venue_data['country'].get('name')} ({venue_data['country'].get('countryCode')})")
            if venue_data.get('address'):
                print(f"Address: {venue_data['address'].get('line1')}")
            if venue_data.get('postalCode'):
                print(f"Postal Code: {venue_data['postalCode']}")

async def main():
    print("Testing European Venue Country Detection")
    print("=======================================")
    
    # Get API key from command line argument if provided
    api_key = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Test sample venues
    await test_sample_venues()
    
    # Test real venues if API key is provided
    if api_key:
        await test_real_venues(api_key)
    else:
        print("\nSkipping real venue tests. To test with real venues, provide an API key as an argument.")

if __name__ == "__main__":
    asyncio.run(main()) 