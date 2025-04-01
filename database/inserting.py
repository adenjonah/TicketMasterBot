from datetime import datetime, timezone
import asyncpg
from dateutil import parser
from config.logging import logger
import json

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
            
            # Process presale information if available
            presale_data = None
            if 'sales' in event and 'presales' in event['sales']:
                presales = []
                for presale in event['sales']['presales']:
                    try:
                        presale_name = presale.get('name', 'Unnamed Presale')
                        presale_start = parser.parse(presale.get('startDateTime')).astimezone(timezone.utc).isoformat()
                        presale_end = parser.parse(presale.get('endDateTime')).astimezone(timezone.utc).isoformat()
                        
                        presales.append({
                            'name': presale_name,
                            'startDateTime': presale_start,
                            'endDateTime': presale_end,
                            'url': url
                        })
                    except Exception as presale_error:
                        logger.error(f"Error processing presale for event {event_id}: {presale_error}", exc_info=True)
                
                if presales:
                    presale_data = json.dumps(presales)
                    logger.debug(f"Processed {len(presales)} presales for event: {event_name} (ID: {event_id})")

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
                    INSERT INTO Artists (artistID, name, notable)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (artistID) DO NOTHING
                    ''',
                    artist_id, artist_name, False
                )
                logger.debug(f"Ensured artist exists: {artist_name} (ID: {artist_id})")

            # Insert new event into the database with presale data
            await conn.execute(
                '''
                INSERT INTO Events (eventID, name, artistID, venueID, eventDate, ticketOnsaleStart, url, image_url, sentToDiscord, lastUpdated, reminder, presaleData)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ''',
                event_id, event_name, artist_ids[0] if artist_ids else None, venue_id, event_date, onsale_start, url, image_url,
                False, last_updated, None, presale_data
            )

            logger.info(f"New event added: {event_name} (ID: {event_id})")
            return True

        except asyncpg.exceptions.UniqueViolationError:
            logger.warning(f"Duplicate entry detected: {event_name} (ID: {event_id})")
            return False

        except Exception as e:
            logger.error(f"Error storing event: {e}", exc_info=True)
            return False
        

async def update_status(region, last_request=None, events_returned=None, new_events=None, error_messages=None):
        """
        Update the status of a server in the database.
        
        Parameters:
            region (str): The ServerID (region).
            last_request (datetime, optional): The timestamp of the last request.
            events_returned (int, optional): The number of events returned.
            new_events (int, optional): The number of new events.
            error_messages (str, optional): Error messages, if any.
        """
        from config.db_pool import db_pool  # Import dynamically to ensure it's initialized

        # Determine the status based on the presence of error messages
        if error_messages is not None:
            status = "Error"
        else:
            status = "Running"

        # Use current time if last_request is not provided
        timestamp = last_request if last_request else datetime.now(timezone.utc)
        
        # Calculate hour of day and day of week for time pattern analysis
        hour_of_day = timestamp.hour
        day_of_week = timestamp.weekday()  # Monday is 0, Sunday is 6

        async with db_pool.acquire() as conn:
            try:
                if error_messages is not None and all(arg is None for arg in [last_request, events_returned, new_events]):
                    # Only update error_messages and status
                    await conn.execute(
                        '''
                        INSERT INTO Server (ServerID, status, error_messages)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (ServerID) DO UPDATE
                        SET status = EXCLUDED.status,
                            error_messages = EXCLUDED.error_messages
                        ''',
                        region, status, error_messages
                    )
                    logger.info(f"Error status updated for server: {region} (Status: {status})")
                else:
                    # Perform a full update
                    await conn.execute(
                        '''
                        INSERT INTO Server (ServerID, status, last_request, events_returned, new_events, error_messages)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (ServerID) DO UPDATE
                        SET status = EXCLUDED.status,
                            last_request = EXCLUDED.last_request,
                            events_returned = EXCLUDED.events_returned,
                            new_events = EXCLUDED.new_events,
                            error_messages = EXCLUDED.error_messages
                        ''',
                        region, status, timestamp, events_returned, new_events, error_messages
                    )
                    logger.info(f"Server status updated: {region} (Status: {status})")
                
                # Always add a time series entry regardless of the update type
                await conn.execute(
                    '''
                    INSERT INTO ServerTimeSeries 
                    (ServerID, timestamp, status, events_returned, new_events, hour_of_day, day_of_week, error_messages)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ''',
                    region, timestamp, status, 
                    events_returned or 0, new_events or 0, 
                    hour_of_day, day_of_week, error_messages
                )
                logger.info(f"Time series data recorded for region {region} at hour {hour_of_day}")
                
            except Exception as e:
                logger.error(f"Error updating server status for region '{region}': {e}", exc_info=True)

async def record_notable_events_data(region, timestamp=None, total_events=0, new_events=0):
    """
    Record time series data for notable artist events.
    
    Parameters:
        region (str): The region identifier.
        timestamp (datetime, optional): The timestamp of the data point.
        total_events (int): Total number of notable events.
        new_events (int): Number of new notable events.
    """
    from config.db_pool import db_pool  # Import dynamically to ensure it's initialized
    
    # Use current time if timestamp is not provided
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    # Calculate hour of day and day of week for time pattern analysis
    hour_of_day = timestamp.hour
    day_of_week = timestamp.weekday()  # Monday is 0, Sunday is 6
    
    async with db_pool.acquire() as conn:
        try:
            # Insert data into the NotableEventsTimeSeries table
            await conn.execute(
                '''
                INSERT INTO NotableEventsTimeSeries
                (timestamp, hour_of_day, day_of_week, total_events, new_events, region)
                VALUES ($1, $2, $3, $4, $5, $6)
                ''',
                timestamp, hour_of_day, day_of_week, total_events, new_events, region
            )
            logger.info(f"Notable events time series data recorded for region {region}: {new_events} new events")
            
        except Exception as e:
            logger.error(f"Error recording notable events time series for region '{region}': {e}", exc_info=True)