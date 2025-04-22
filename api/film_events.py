import os
import asyncio
from datetime import datetime, timezone
import aiohttp
from config.logging import logger
from config.config import TICKETMASTER_API_KEY, CENTER_POINT, RADIUS, UNIT, REGION

async def fetch_film_events(session, page, current_time, current_date):
    """
    Fetch film events from the Ticketmaster API.
    This is specifically designed for the film region server.
    """
    # Only use film-specific parameters for the film region
    if REGION.lower() != 'film':
        from api.event_req import fetch_events_from_api
        return await fetch_events_from_api(session, page, current_time, current_date)
    
    logger.info(f"Fetching film events...")
    
    # Film classification parameters
    classification_id = "KZFzniwnSyZfZ7v7nn"  # Film
    genre_id = "KnvZfZ7vAka"                  # Miscellaneous (Film)
    subgenre_id = "KZazBEonSMnZfZ7vFln"       # Miscellaneous
    type_id = "KZAyXgnZfZ7v7nI"               # Undefined
    subtype_id = "KZFzBErXgnZfZ7v7lJ"         # Undefined
    
    base_url = "https://app.ticketmaster.com/discovery/v2/events"
    params = {
        "apikey": TICKETMASTER_API_KEY,
        "source": "ticketmaster",
        "locale": "*",
        "size": 199,
        "page": page,
        "onsaleStartDateTime": current_time,
        "classificationId": classification_id,
        "genreId": genre_id,
        "subGenreId": subgenre_id,
        "typeId": type_id,
        "subTypeId": subtype_id,
        "onsaleOnAfterStartDate": current_date,
        "sort": "onSaleStartDate,asc",
        "latlong": CENTER_POINT,  # Latitude and Longitude
        "radius": RADIUS,         # Radius around the center point
        "unit": UNIT              # Unit for radius
    }

    # Construct the full URL with encoded parameters
    import urllib.parse
    full_url = f"{base_url}?{urllib.parse.urlencode(params)}"

    logger.info(f"Film request made to {full_url}")
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
            
            logger.info(f"[Film] Retrieved {len(events)} events, {events_with_presales} with presale information")
            return events
        except Exception as e:
            logger.error(f"Error fetching film data from {full_url}: {e}")
            raise 