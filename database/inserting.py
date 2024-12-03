import aiohttp  # For async HTTP requests
import psycopg2
import discord
from psycopg2.extras import DictCursor
import logging
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
import asyncpg
from dateutil import parser
import asyncio

logger = logging.getLogger(__name__)

now = datetime.now(timezone.utc)

from config.config import (
    DISCORD_BOT_TOKEN,
    DISCORD_CHANNEL_ID,
    DISCORD_CHANNEL_ID_TWO,
    TICKETMASTER_API_KEY,
    REDIRECT_URI,
    DATABASE_URL,
)

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
            artist_data = event['_embedded'].get('attractions', [{}])[0]
            artist_id = artist_data.get('id')
            artist_name = artist_data.get('name', 'Unknown Artist')

            # Check for missing IDs
            if not venue_id:
                logger.warning(f"Event {event_name} (ID: {event_id}) has no associated venue.")
                return False
            if not artist_id:
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

            # Insert artist into the database (if available)
            if artist_id:
                await conn.execute(
                    '''
                    INSERT INTO Artists (artistID, name, notable)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (artistID) DO NOTHING
                    ''',
                    artist_id, artist_name, False
                )
                logger.debug(f"Ensured artist exists: {artist_name} (ID: {artist_id})")

            # Insert new event into the database
            await conn.execute(
                '''
                INSERT INTO Events (eventID, name, artistID, venueID, eventDate, ticketOnsaleStart, url, image_url, sentToDiscord, lastUpdated)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ''',
                event_id, event_name, artist_id, venue_id, event_date, onsale_start, url, image_url,
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