from datetime import datetime, timezone
import asyncpg
from dateutil import parser
from config.logging import logger

now = datetime.now(timezone.utc)

async def store_event(event):
    """Stores a new event in the database if not already present."""
    from config.db_pool import db_pool  # Import dynamically to ensure it's initialized

    async with db_pool.acquire() as conn:
        try:
            # Extract event details
            event_id = event.get('id')
            event_name = event.get('name', 'Unnamed Event')
            event_date = parser.parse(event['dates']['start']['localDate']).astimezone(timezone.utc).replace(tzinfo=None)
            onsale_start = parser.parse(event['sales']['public']['startDateTime']).astimezone(timezone.utc).replace(tzinfo=None)
            last_updated = datetime.now(timezone.utc).replace(tzinfo=None)
            url = event.get('url', '')
            image_url = next(
                (img['url'] for img in event.get('images', []) if img.get('width', 0) >= 1024),
                None
            )

            # Venue data
            venue_data = event['_embedded'].get('venues', [{}])[0]
            venue_id = venue_data.get('id')
            venue_name = venue_data.get('name', 'Unknown Venue')
            venue_city = venue_data.get('city', {}).get('name', 'Unknown City')
            venue_state = venue_data.get('state', {}).get('stateCode', 'Unknown State')

            # Artist data
            attractions = event['_embedded'].get('attractions', [])
            artist_ids = [artist.get('id') for artist in attractions if 'id' in artist]
            artist_names = [artist.get('name', 'Unknown Artist') for artist in attractions]
            artist_name = ", ".join(artist_names) if artist_names else "Unknown Artist"

            # Check for missing IDs
            if not venue_id:
                logger.warning(f"Event {event_name} (ID: {event_id}) has no associated venue.")
                return False
            if not artist_ids:
                logger.warning(f"Event {event_name} (ID: {event_id}) has no associated artist.")

            # Check if event already exists
            existing_event = await conn.fetchrow(
                '''
                SELECT eventID FROM Events WHERE eventID = $1
                ''',
                event_id
            )

            if existing_event:
                logger.info(f"Event already exists in DB: {event_name} (ID: {event_id})")
                return False  # Skip inserting if the event exists

            # Insert venue into the database
            await conn.execute(
                '''
                INSERT INTO Venues (venueID, name, city, state)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (venueID) DO NOTHING
                ''',
                venue_id, venue_name, venue_city, venue_state
            )
            logger.debug(f"Ensured venue exists: {venue_name} (ID: {venue_id})")

            # Insert artists into the database
            for artist_id, artist_name in zip(artist_ids, artist_names):
                await conn.execute(
                    '''
                    INSERT INTO Artists (artistID, name, notable, reminder)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (artistID) DO NOTHING
                    ''',
                    artist_id, artist_name, False, False
                )
                logger.debug(f"Ensured artist exists: {artist_name} (ID: {artist_id})")

            # Insert new event into the database
            await conn.execute(
                '''
                INSERT INTO Events (eventID, name, artistID, venueID, eventDate, ticketOnsaleStart, url, image_url, sentToDiscord, lastUpdated)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ''',
                event_id, event_name, artist_ids[0] if artist_ids else None, venue_id, event_date, onsale_start, url, image_url,
                False, last_updated
            )

            logger.info(f"New event added: {event_name} (ID: {event_id})")
            return True

        except asyncpg.exceptions.UniqueViolationError:
            logger.warning(f"Duplicate entry detected: {event_name} (ID: {event_id})")
            return False

        except Exception as e:
            logger.error(f"Error storing event: {e}", exc_info=True)
            return False