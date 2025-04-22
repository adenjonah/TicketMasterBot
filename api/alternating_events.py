import os
import asyncio
from datetime import datetime, timezone
import aiohttp
from config.logging import logger
from config.config import TICKETMASTER_API_KEY, CENTER_POINT, RADIUS, UNIT, REGION

# Classification IDs for Ticketmaster API
# KZFzniwnSyZfZ7v7nJ = Music
# KZFzniwnSyZfZ7v7na = Arts & Theatre
# KZFzniwnSyZfZ7v7nn = Film
# KZFzniwnSyZfZ7v7n1 = Miscellaneous
# KZFzniwnSyZfZ7v7nE = Sports

# Genre IDs within Arts & Theatre
# KnvZfZ7vAe1 = Comedy
# KnvZfZ7v7l1 = Theatre

# Define alternating classifications for the comedy-theatre-film server
CLASSIFICATIONS = [
    {
        "name": "Comedy",
        "classification_id": "KZFzniwnSyZfZ7v7na",  # Arts & Theatre
        "genre_id": "KnvZfZ7vAe1",                  # Comedy
        "subgenre_id": None,
        "type_id": None,
        "subtype_id": None
    },
    {
        "name": "Theatre",
        "classification_id": "KZFzniwnSyZfZ7v7na",  # Arts & Theatre
        "genre_id": "KnvZfZ7v7l1",                  # Theatre
        "subgenre_id": None,
        "type_id": None,
        "subtype_id": None
    },
    {
        "name": "Film Events",
        "classification_id": "KZFzniwnSyZfZ7v7nn",  # Film
        "genre_id": "KnvZfZ7vAka",                  # Miscellaneous (Film)
        "subgenre_id": "KZazBEonSMnZfZ7vFln",       # Miscellaneous
        "type_id": "KZAyXgnZfZ7v7nI",               # Undefined
        "subtype_id": "KZFzBErXgnZfZ7v7lJ"          # Undefined
    }
]

# Global state to track the current classification index
current_classification_index = 0

def get_current_classification():
    """Get the current classification based on rotation state."""
    global current_classification_index
    classification = CLASSIFICATIONS[current_classification_index]
    
    # Rotate to the next classification for the next call
    current_classification_index = (current_classification_index + 1) % len(CLASSIFICATIONS)
    
    return classification

async def fetch_events_with_alternating_classification(session, page, current_time, current_date):
    """
    Fetch events from the Ticketmaster API using alternating classifications.
    This is specifically designed for the comedy-theatre-film server to maximize
    the variety of events detected.
    """
    global current_classification_index
    
    # Only use alternating classifications for the comedy/ctf region
    if REGION.lower() not in ['comedy', 'comedy-theatre-film', 'ctf']:
        from api.event_req import fetch_events_from_api
        return await fetch_events_from_api(session, page, current_time, current_date)
    
    # Get current classification in the rotation
    classification = get_current_classification()
    logger.info(f"CTF Server using classification: {classification['name']}")
    
    base_url = "https://app.ticketmaster.com/discovery/v2/events"
    params = {
        "apikey": TICKETMASTER_API_KEY,
        "source": "ticketmaster",
        "locale": "*",
        "size": 199,
        "page": page,
        "onsaleStartDateTime": current_time,
        "classificationId": classification["classification_id"],
        "onsaleOnAfterStartDate": current_date,
        "sort": "onSaleStartDate,asc",
        "latlong": CENTER_POINT,  # Latitude and Longitude
        "radius": RADIUS,         # Radius around the center point
        "unit": UNIT              # Unit for radius
    }
    
    # Add genre ID filter if specified
    if classification["genre_id"]:
        params["genreId"] = classification["genre_id"]
        
    # Add additional classification parameters if specified
    if classification["subgenre_id"]:
        params["subGenreId"] = classification["subgenre_id"]
    if classification["type_id"]:
        params["typeId"] = classification["type_id"]
    if classification["subtype_id"]:
        params["subTypeId"] = classification["subtype_id"]

    # Construct the full URL with encoded parameters
    import urllib.parse
    full_url = f"{base_url}?{urllib.parse.urlencode(params)}"

    logger.info(f"Request made to {full_url}")
    async with session.get(full_url) as response:
        try:
            response.raise_for_status()
            data = await response.json()
            events = data.get("_embedded", {}).get("events", [])
            
            # Check if events have presale information
            events_with_presales = 0
            for event in events:
                if 'sales' in event and 'presales' in event['sales'] and event['sales']['presales']:
                    events_with_presales += 1
                    presale_count = len(event['sales']['presales'])
                    logger.debug(f"Event {event.get('id')} has {presale_count} presale(s)")
            
            logger.info(f"[CTF:{classification['name']}] Retrieved {len(events)} events, {events_with_presales} with presale information")
            return events
        except Exception as e:
            logger.error(f"Error fetching data from {full_url}: {e}")
            raise 