import discord
from config.logging import logger
import logging
from helpers.formatting import format_date_human_readable
import pytz
import json
from dateutil import parser
from datetime import datetime
import re
from urllib.parse import urlparse, quote, unquote

# List of known bad event IDs that trigger Discord URL validation errors
KNOWN_BAD_EVENT_IDS = set([
    "1AsZk19Gkd3D7VP"  # Known problematic event ID from the logs
])

def _fix_url(url):
    """Ensures a URL has the correct http/https scheme and is well-formed."""
    if not url:
        return "https://example.com"  # Fallback URL if none is provided
    
    # For logging only in debug mode
    original_url = url
    
    try:
        # Remove any whitespace and control characters
        url = url.strip()
        url = re.sub(r'[\x00-\x1F\x7F]', '', url)  # Remove control characters
        
        # Handle specific case with capitalized protocol (Https://, Http://)
        # Discord requires lowercase protocol
        if url.startswith('Https://'):
            url = 'https://' + url[8:]
        elif url.startswith('Http://'):
            url = 'http://' + url[7:]
        
        # Check for common malformed URLs
        elif url.startswith('ttps://'):
            url = 'https://' + url[7:]
        elif url.startswith('hhttps://'):
            url = 'https://' + url[8:]
        elif url.startswith('http:/www.'):
            url = 'http://www.' + url[9:]
        elif url.startswith('https:/www.'):
            url = 'https://www.' + url[10:]
        elif url.startswith('www.'):
            url = 'https://' + url
        elif not (url.startswith('http://') or url.startswith('https://')):
            url = 'https://' + url
        
        # Replace double slashes (except after protocol)
        url = re.sub(r'(?<!:)//+', '/', url)
        
        # Fix potential percent encoding issues
        try:
            # First decode any already encoded parts to avoid double encoding
            decoded_url = unquote(url)
            
            # Parse into components
            parsed = urlparse(decoded_url)
            
            # Basic validation
            if not parsed.netloc:
                logger.warning(f"URL missing domain: {url}")
                return "https://example.com"
                
            # Ensure the URL components are properly encoded
            path = quote(parsed.path, safe='/-_.~')
            query = quote(parsed.query, safe='=&-_.~')
            fragment = quote(parsed.fragment, safe='-_.~')
            
            # Reconstruct the URL with encoded components
            # Always use lowercase scheme (http or https) as required by Discord
            scheme = parsed.scheme.lower()
            fixed_url = f"{scheme}://{parsed.netloc}{path}"
            if query:
                fixed_url += f"?{query}"
            if fragment:
                fixed_url += f"#{fragment}"
                
            # One final validation with regex for RFC 3986 compliant URLs
            if not re.match(r'^(https?):\/\/[^\s/$.?#].[^\s]*$', fixed_url):
                logger.warning(f"URL failed final validation: {fixed_url}")
                return "https://example.com"
                
            if logger.isEnabledFor(logging.DEBUG) and original_url != fixed_url:
                logger.debug(f"Fixed URL: '{original_url}' -> '{fixed_url}'")
                
            return fixed_url
            
        except Exception as e:
            logger.warning(f"Error encoding URL components: {e}")
            return "https://example.com"
            
    except Exception as e:
        logger.error(f"Error fixing URL: {e}")
        return "https://example.com"

# Test cases for URL fixing - only run in debug mode
def _test_url_fixing():
    """Test the URL fixing function with various cases."""
    if not logger.isEnabledFor(logging.DEBUG):
        return
        
    test_cases = [
        "https://example.com",
        "http://example.com",
        "example.com",
        "ttps://example.com",
        "hhttps://example.com",
        "https://example.com/path with spaces",
        "https://example.com?query=test&param=value",
        "https://example.com#fragment",
        "https://example.com/path?query=test#fragment",
        "https://example.com/path with spaces?query=test with spaces#fragment with spaces",
        "http:/www.example.com",
        "https:/www.example.com",
        "www.example.com",
        "",  # Empty URL
        None,  # None URL
        "invalid url",  # Invalid URL
        "http:// example.com",  # URL with space after scheme
        "https://example.com//path//subpath",  # Double slashes
        "https://example.com/%7Euser/",  # Already encoded URL
    ]
    
    logger.debug("Testing URL fixing function...")
    for test_url in test_cases:
        fixed = _fix_url(test_url)
        logger.debug(f"Test URL: '{test_url}' -> Fixed: '{fixed}'")
    
    logger.debug("URL fixing tests completed.")

# Run tests only in debug mode
if logger.isEnabledFor(logging.DEBUG):
    _test_url_fixing()

async def notify_events(bot, channel_id, notable_only=False, region=None):
    from config.db_pool import db_pool  # Import shared db_pool here
    """
    Notifies Discord about unsent events. 
    
    Parameters:
        bot (discord.Client): The Discord bot instance.
        channel_id (int): The Discord channel ID to send notifications to.
        notable_only (bool): Whether to only notify events with notable artists.
        region (str): Filter events by region ('eu' for European events, 'non-eu' for non-European events).
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Starting notify_events with channel_id={channel_id}, notable_only={notable_only}, region={region}")
    elif logger.isEnabledFor(logging.INFO):
        logger.info(f"Notifying {'notable' if notable_only else 'all'} events for region {region or 'all'}")

    # If we're checking for European events, first do a diagnostic
    if region == 'eu' and logger.isEnabledFor(logging.DEBUG):
        async with db_pool.acquire() as conn:
            try:
                # Check what EU regions actually exist
                regions_query = """
                SELECT region, COUNT(*) 
                FROM Events 
                WHERE sentToDiscord = FALSE 
                GROUP BY region
                """
                regions = await conn.fetch(regions_query)
                logger.debug(f"Unsent events by region: {regions}")
            except Exception as e:
                logger.error(f"Error during EU diagnostics: {e}")

    base_query = '''
        SELECT 
            Events.eventID, 
            Events.name, 
            Events.ticketOnsaleStart, 
            Events.eventDate, 
            Events.url, 
            Events.presaleData,
            Events.region,
            Venues.city, 
            Venues.state, 
            Events.image_url, 
            Artists.name AS artist_name,
            Artists.notable
        FROM Events
        LEFT JOIN Venues ON Events.venueID = Venues.venueID
        LEFT JOIN Artists ON Events.artistID = Artists.artistID
        WHERE Events.sentToDiscord = FALSE
    '''

    # Build the query filters based on parameters
    filters = []
    
    # Add the notable filter
    if notable_only:
        filters.append("Artists.notable = TRUE")
    else:
        filters.append("(Artists.notable = FALSE OR Artists.artistID IS NULL)")
    
    # Add the region filter
    if region == 'eu':
        filters.append("LOWER(Events.region) = 'eu'")
    elif region == 'non-eu':
        filters.append("(LOWER(Events.region) != 'eu' OR Events.region IS NULL)")
    
    # Add filters to exclude known bad event IDs
    if KNOWN_BAD_EVENT_IDS:
        bad_ids_list = ", ".join(f"'{event_id}'" for event_id in KNOWN_BAD_EVENT_IDS)
        filters.append(f"Events.eventID NOT IN ({bad_ids_list})")
    
    # Add filters to the query
    filter_clause = ' AND '.join(filters)
    if filters:
        query = f"{base_query} AND {filter_clause}"
    else:
        query = base_query

    async with db_pool.acquire() as conn:
        try:
            # Count matching events
            count_query = f"""
            SELECT COUNT(*) 
            FROM Events
            LEFT JOIN Venues ON Events.venueID = Venues.venueID
            LEFT JOIN Artists ON Events.artistID = Artists.artistID
            WHERE Events.sentToDiscord = FALSE
            AND {filter_clause}
            """
            
            total_matching = await conn.fetchval(count_query)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Found {total_matching} events to notify")
            elif total_matching > 0 and logger.isEnabledFor(logging.INFO):
                logger.info(f"Found {total_matching} events to notify")
            
            # Get the actual events to notify
            events_to_notify = await conn.fetch(query)
            
            if not events_to_notify:
                return

            channel = bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Discord channel with ID {channel_id} not found")
                return

            utc_tz = pytz.utc
            est_tz = pytz.timezone('America/New_York')

            # Batch process events and log in groups
            batch_size = 10
            success_count = 0
            error_count = 0
            
            for i in range(0, len(events_to_notify), batch_size):
                batch = events_to_notify[i:i+batch_size]
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Processing batch of {len(batch)} events...")
                
                for event in batch:
                    try:
                        event_id = event['eventid']
                        event_name = event['name']
                        
                        # Skip known problematic events
                        if event_id in KNOWN_BAD_EVENT_IDS:
                            logger.warning(f"Skipping known problematic event: {event_id}")
                            # Mark as sent to avoid retrying
                            await conn.execute(
                                "UPDATE Events SET sentToDiscord = TRUE WHERE eventID = $1",
                                event_id
                            )
                            continue
                        
                        # Save original URLs for troubleshooting
                        original_event_url = event['url']
                        original_image_url = event['image_url']
                        
                        # Check if the URL is empty or None (this happens with some events)
                        if not original_event_url:
                            logger.warning(f"Event {event_id} has no URL. Using fallback URL.")
                            original_event_url = f"https://www.ticketmaster.com/event/{event_id}"
                        
                        # Fix URLs before creating embed
                        fixed_event_url = _fix_url(original_event_url)
                        fixed_image_url = _fix_url(original_image_url) if original_image_url else None

                        # Create Discord embed
                        embed = discord.Embed(
                            title = f"{event_name}" if event['artist_name'] is None else f"{event['artist_name']} - {event_name}",
                            url=fixed_event_url,
                            description=(
                                f"**Location**: {event['city']}, {event['state']}\n"
                                f"**Event Date**: {event['eventdate'].astimezone(est_tz).strftime('%B %d, %Y at %I:%M %p EST') if event['eventdate'] else 'TBA'}\n"
                                f"**Sale Start**: {event['ticketonsalestart'].astimezone(est_tz).strftime('%B %d, %Y at %I:%M %p EST') if event['ticketonsalestart'] else 'TBA'}\n\n"
                                f"React with 🔔 to set a reminder for this event!"
                            ),
                            color=discord.Color.purple() if event['region'] == 'eu' else discord.Color.blue()
                        )
                        
                        if fixed_image_url:
                            embed.set_image(url=fixed_image_url)

                        # Send notification to Discord channel
                        await channel.send(embed=embed)
                        
                        # Mark event as sent in the database
                        await conn.execute(
                            "UPDATE Events SET sentToDiscord = TRUE WHERE eventID = $1",
                            event_id
                        )
                        
                        success_count += 1
                        
                    except discord.errors.HTTPException as e:
                        error_count += 1
                        # Add this event ID to the known bad events list
                        if "Not a well formed URL" in str(e):
                            KNOWN_BAD_EVENT_IDS.add(event_id)
                            logger.error(f"Added event {event_id} to known bad events list due to URL error")
                            
                        # Log detailed info on the problematic URLs
                        logger.error(f"Discord embed error for event {event['eventid']} ({event['name']}): {e}")
                        logger.error(f"Problem URL: original='{event['url']}', fixed='{fixed_event_url}'")
                        
                        # Mark it as sent to avoid trying again
                        await conn.execute(
                            "UPDATE Events SET sentToDiscord = TRUE WHERE eventID = $1",
                            event_id
                        )
                        continue
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error processing event {event.get('eventid', 'unknown')}: {e}")
                        continue
                
                if logger.isEnabledFor(logging.INFO):
                    logger.info(f"Processed batch: {len(batch)} events")
            
            # Also mark any known bad events as sent to avoid retrying them
            if KNOWN_BAD_EVENT_IDS:
                bad_ids_list = ", ".join(f"'{event_id}'" for event_id in KNOWN_BAD_EVENT_IDS)
                await conn.execute(
                    f"UPDATE Events SET sentToDiscord = TRUE WHERE eventID IN ({bad_ids_list}) AND sentToDiscord = FALSE"
                )
                logger.info(f"Marked {len(KNOWN_BAD_EVENT_IDS)} known problematic events as sent")
            
            # Log summary at the end
            if logger.isEnabledFor(logging.INFO):
                logger.info(f"Notify summary: {success_count} sent, {error_count} errors")
                
        except Exception as e:
            logger.error(f"Notification error: {e}")
        finally:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Database connection released.")