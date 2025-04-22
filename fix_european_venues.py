#!/usr/bin/env python
import asyncio
import asyncpg
import sys
import os

# Define the database URL directly
DATABASE_URL = "postgres://u5uo83vleju7gr:p074eeaa2af2fea64b9daeda66b597fb6695dafe27e08e1d1ed36c6137f95b67e@c3nv2ev86aje4j.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d7qqd953vljjbn"

# Country codes to country names mapping
COUNTRY_CODES = {
    "UK": "United Kingdom",
    "GB": "United Kingdom",
    "DE": "Germany", 
    "FR": "France",
    "IT": "Italy",
    "ES": "Spain",
    "NL": "Netherlands",
    "BE": "Belgium",
    "SE": "Sweden",
    "DK": "Denmark",
    "NO": "Norway",
    "FI": "Finland",
    "AT": "Austria",
    "CH": "Switzerland",
    "IE": "Ireland",
    "PT": "Portugal",
    "GR": "Greece",
    "PL": "Poland",
    "CZ": "Czech Republic",
    "HU": "Hungary",
    "RO": "Romania",
    "BG": "Bulgaria",
    "HR": "Croatia",
    "SK": "Slovakia",
    "SI": "Slovenia",
    "LU": "Luxembourg",
    "MT": "Malta",
    "CY": "Cyprus",
    "EE": "Estonia",
    "LV": "Latvia",
    "LT": "Lithuania"
}

# City to country mapping for common European cities
CITY_TO_COUNTRY = {
    "London": "United Kingdom",
    "Manchester": "United Kingdom",
    "Birmingham": "United Kingdom",
    "Glasgow": "United Kingdom",
    "Edinburgh": "United Kingdom",
    "Liverpool": "United Kingdom",
    "Sheffield": "United Kingdom",
    "Barnstaple": "United Kingdom",
    "St Helens": "United Kingdom",
    "Leeds": "United Kingdom",
    "Brighton": "United Kingdom",
    "Oxford": "United Kingdom",
    "Cambridge": "United Kingdom",
    "Bristol": "United Kingdom",
    "Newcastle": "United Kingdom",
    "Cardiff": "United Kingdom",
    "Southampton": "United Kingdom",
    "Portsmouth": "United Kingdom",
    "York": "United Kingdom",
    "Nottingham": "United Kingdom",
    "Leicester": "United Kingdom",
    "Coventry": "United Kingdom",
    "Hull": "United Kingdom",
    "Swansea": "United Kingdom",
    "Belfast": "United Kingdom",
    "Aberdeen": "United Kingdom",
    "Dundee": "United Kingdom",
    "Paris": "France",
    "Lyon": "France",
    "Marseille": "France",
    "Berlin": "Germany",
    "Munich": "Germany",
    "Hamburg": "Germany",
    "Frankfurt": "Germany",
    "Cologne": "Germany",
    "Madrid": "Spain",
    "Barcelona": "Spain",
    "Seville": "Spain",
    "Valencia": "Spain",
    "Rome": "Italy",
    "Milan": "Italy",
    "Naples": "Italy",
    "Florence": "Italy",
    "Venice": "Italy",
    "Turin": "Italy",
    "Amsterdam": "Netherlands",
    "Rotterdam": "Netherlands",
    "The Hague": "Netherlands",
    "Brussels": "Belgium",
    "Antwerp": "Belgium",
    "Stockholm": "Sweden",
    "Gothenburg": "Sweden",
    "Malmö": "Sweden",
    "Copenhagen": "Denmark",
    "Oslo": "Norway",
    "Helsinki": "Finland",
    "Vienna": "Austria",
    "Zurich": "Switzerland",
    "Geneva": "Switzerland",
    "Bern": "Switzerland",
    "Dublin": "Ireland",
    "Cork": "Ireland",
    "Lisbon": "Portugal",
    "Porto": "Portugal",
    "Athens": "Greece",
    "Thessaloniki": "Greece",
    "Warsaw": "Poland",
    "Krakow": "Poland",
    "Prague": "Czech Republic",
    "Budapest": "Hungary",
    "Bucharest": "Romania",
    "Sofia": "Bulgaria",
    "Zagreb": "Croatia",
    "Bratislava": "Slovakia",
    "Ljubljana": "Slovenia",
    "Luxembourg": "Luxembourg",
    "Valletta": "Malta",
    "Nicosia": "Cyprus",
    "Tallinn": "Estonia",
    "Riga": "Latvia",
    "Vilnius": "Lithuania"
}

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

async def fix_european_venues():
    """Fix venue information for European events."""
    print("Fixing venue information for European events...")
    
    try:
        # Connect to the database
        print(f"Connecting to database...")
        conn = await asyncpg.connect(DATABASE_URL)
        
        try:
            # Get the actual table names
            events_table = await get_table_name(conn, 'events')
            venues_table = await get_table_name(conn, 'venues')
            
            if not events_table or not venues_table:
                print("Error: Events or Venues table not found.")
                return False
            
            print(f"Using tables: Events={events_table}, Venues={venues_table}")
            
            # Find venue IDs used by European events
            eu_venue_ids = await conn.fetch(f"""
            SELECT DISTINCT v.venueID, v.name, v.city, v.state
            FROM {events_table} e
            JOIN {venues_table} v ON e.venueID = v.venueID
            WHERE LOWER(e.region) = 'eu'
            """)
            
            print(f"Found {len(eu_venue_ids)} unique venues used by European events.")
            
            # Go through each venue and update country information if needed
            updated_count = 0
            for venue in eu_venue_ids:
                venue_id = venue['venueid']
                venue_name = venue['name']
                city = venue['city']
                state = venue['state']
                
                # Skip venues that already have country information
                if state and state in COUNTRY_CODES.values():
                    continue
                
                # Check for "Unknown State", empty state, or country code
                needs_update = (
                    not state or 
                    state == "Unknown State" or 
                    state == "Unknown" or
                    (state and state.upper() in COUNTRY_CODES)
                )
                
                if not needs_update:
                    continue
                
                new_country = None
                
                # Try to determine country from existing state (if it's a country code)
                if state and state.upper() in COUNTRY_CODES:
                    new_country = COUNTRY_CODES[state.upper()]
                # Try to determine country from city
                elif city and city in CITY_TO_COUNTRY:
                    new_country = CITY_TO_COUNTRY[city]
                # Default to UK for unrecognized venues (most common for European events)
                else:
                    new_country = "United Kingdom"
                
                if new_country:
                    # Update venue with country name
                    result = await conn.execute(f"""
                    UPDATE {venues_table}
                    SET state = $1
                    WHERE venueID = $2
                    """, new_country, venue_id)
                    
                    if result and result != "UPDATE 0":
                        updated_count += 1
                        print(f"Updated venue: {venue_name} ({city}, {state}) -> {city}, {new_country}")
            
            print(f"\nUpdated {updated_count} out of {len(eu_venue_ids)} European venues with country information.")
            
            # Check updated venue information
            print("\nSample of European venues after update:")
            updated_venues = await conn.fetch(f"""
            SELECT DISTINCT v.venueID, v.name, v.city, v.state
            FROM {events_table} e
            JOIN {venues_table} v ON e.venueID = v.venueID
            WHERE LOWER(e.region) = 'eu'
            LIMIT 10
            """)
            
            for venue in updated_venues:
                print(f"  {venue['name']}: {venue['city']}, {venue['state']}")
            
            print("\nVenue information update completed successfully.")
            return True
            
        finally:
            await conn.close()
            print("Database connection closed.")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

async def main():
    """Main function to run the script."""
    print("Script to fix European venue information")
    print("=======================================")
    
    success = await fix_european_venues()
    
    if success:
        print("Operation completed successfully.")
    else:
        print("Operation failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 