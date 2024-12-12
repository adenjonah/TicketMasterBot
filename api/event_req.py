from datetime import datetime, timezone
import urllib.parse
from config.logging import logger
import urllib.parse  # Import for URL encoding

from config.config import (
    TICKETMASTER_API_KEY,
    CENTER_POINT,
    RADIUS,
    UNIT
)

now = datetime.now(timezone.utc)

async def fetch_events_from_api(session, page, current_time, current_date):
    """Fetch events from the Ticketmaster API."""
    base_url = "https://app.ticketmaster.com/discovery/v2/events"
    params = {
        "apikey": TICKETMASTER_API_KEY,
        "source": "ticketmaster",
        "locale": "*",
        "size": 199,
        "page": page,
        "onsaleStartDateTime": current_time,
        # "countryCode": "US",
        "classificationId": "KZFzniwnSyZfZ7v7nJ",
        "onsaleOnAfterStartDate": current_date,
        "sort": "onSaleStartDate,asc",
        "latlong": CENTER_POINT,  # Latitude and Longitude
        "radius": RADIUS,         # Radius around the center point
        "unit": UNIT              # Unit for radius
    }

    # Construct the full URL with encoded parameters
    full_url = f"{base_url}?{urllib.parse.urlencode(params)}"

    logger.info(f"Request made to {full_url}")
    async with session.get(full_url) as response:
        try:
            response.raise_for_status()
            data = await response.json()
            logger.debug(f"Response data (first 500 chars): {str(data)[:500]}")
            return data.get("_embedded", {}).get("events", [])
        except Exception as e:
            logger.error(f"Error fetching data from {full_url}: {e}")
            raise