from datetime import datetime, timezone
import urllib.parse
from config.logging import logger
import urllib.parse  # Import for URL encoding

from config.config import (
    TICKETMASTER_API_KEY,
    CENTER_POINT,
    RADIUS,
    UNIT,
    CLASSIFICATION_ID,
    GENRE_ID,
)

now = datetime.now(timezone.utc)

async def fetch_events_from_api(session, page, current_time, current_date):
    """
    Fetch events from the Ticketmaster API with presale information.
    
    This function specifically requests event data including presale information
    and ensures that the full sales data (including presales) is included in the response.
    """
    base_url = "https://app.ticketmaster.com/discovery/v2/events"
    params = {
        "apikey": TICKETMASTER_API_KEY,
        "source": "ticketmaster",
        "locale": "*",
        "size": 199,
        "page": page,
        "onsaleStartDateTime": current_time,
        "classificationId": CLASSIFICATION_ID,
        "onsaleOnAfterStartDate": current_date,
        "sort": "onSaleStartDate,asc",
        "latlong": CENTER_POINT,  # Latitude and Longitude
        "radius": RADIUS,         # Radius around the center point
        "unit": UNIT              # Unit for radius
    }
    
    # Add genre ID filter if specified
    if GENRE_ID:
        params["genreId"] = GENRE_ID

    # Construct the full URL with encoded parameters
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
            
            logger.info(f"Retrieved {len(events)} events, {events_with_presales} with presale information")
            return events
        except Exception as e:
            logger.error(f"Error fetching data from {full_url}: {e}")
            raise

async def fetch_event_details(session, event_id):
    """
    Fetch detailed information about a specific event, including presale data.
    
    Args:
        session: The aiohttp client session
        event_id: The ID of the event to fetch details for
        
    Returns:
        A dictionary containing the event details or None if not found
    """
    base_url = f"https://app.ticketmaster.com/discovery/v2/events/{event_id}"
    params = {
        "apikey": TICKETMASTER_API_KEY,
    }
    
    # Construct the full URL with encoded parameters
    full_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    logger.info(f"Fetching detailed event info for {event_id}")
    async with session.get(full_url) as response:
        try:
            response.raise_for_status()
            event_data = await response.json()
            
            # Check for presale information
            if 'sales' in event_data and 'presales' in event_data['sales']:
                presale_count = len(event_data['sales']['presales'])
                logger.debug(f"Event {event_id} has {presale_count} presale(s) in detailed view")
            else:
                logger.debug(f"Event {event_id} has no presales in detailed view")
                
            return event_data
        except Exception as e:
            logger.error(f"Error fetching event details for {event_id}: {e}")
            return None