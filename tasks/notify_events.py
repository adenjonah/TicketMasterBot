import discord
from config.logging import logger
from helpers.formatting import format_date_human_readable
import pytz
import json
from dateutil import parser
from datetime import datetime

def _fix_url(url):
    """Ensures a URL has the correct http/https scheme and is well-formed."""
    if not url:
        return "https://example.com"  # Fallback URL if none is provided
        
    # Remove any whitespace
    url = url.strip()
    
    # Check and fix various incorrect URL formats
    if url.startswith('ttps://'):
        url = 'https://' + url[7:]
    elif url.startswith('hhttps://'):
        url = 'https://' + url[8:]
    elif not (url.startswith('http://') or url.startswith('https://')):
        url = 'https://' + url
    
    # Basic URL validation
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            logger.warning(f"Invalid URL format: {url}")
            return "https://example.com"
            
        # Ensure the URL is properly encoded
        from urllib.parse import quote
        path = quote(parsed.path, safe='/-_~.')
        query = quote(parsed.query, safe='=&')
        fragment = quote(parsed.fragment, safe='')
        
        # Reconstruct the URL with encoded components
        fixed_url = f"{parsed.scheme}://{parsed.netloc}{path}"
        if query:
            fixed_url += f"?{query}"
        if fragment:
            fixed_url += f"#{fragment}"
            
        return fixed_url
    except Exception as e:
        logger.error(f"Error fixing URL: {e}")
        return "https://example.com"

# Test cases for URL fixing
def _test_url_fixing():
    """Test the URL fixing function with various cases."""
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
        "",  # Empty URL
        None,  # None URL
        "invalid url",  # Invalid URL
    ]
    
    logger.info("Testing URL fixing function...")
    for test_url in test_cases:
        fixed = _fix_url(test_url)
        logger.info(f"Test case: '{test_url}' -> '{fixed}'")
    
    logger.info("URL fixing tests completed.")

# Run tests when module is imported
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
    logger.info(f"Starting notify_events with channel_id={channel_id}, notable_only={notable_only}, region={region}")

    # If we're checking for European events, first do a diagnostic
    if region == 'eu':
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
                logger.info(f"Unsent events by region: {regions}")
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
            Artists.name AS artist_name
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
            logger.info(f"Found {total_matching} total matching events in database for region={region}, notable_only={notable_only}")
            
            # Get the actual events to notify
            events_to_notify = await conn.fetch(query)
            
            if not events_to_notify:
                return

            channel = bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Discord channel with ID {channel_id} not found.")
                return

            utc_tz = pytz.utc
            est_tz = pytz.timezone('America/New_York')

            # Batch process events and log in groups
            batch_size = 10
            for i in range(0, len(events_to_notify), batch_size):
                batch = events_to_notify[i:i+batch_size]
                logger.info(f"Processing batch of {len(batch)} events...")
                
                for event in batch:
                    try:
                        # Fix URLs before creating embed
                        fixed_event_url = _fix_url(event['url'])
                        fixed_image_url = _fix_url(event['image_url']) if event['image_url'] else None

                        # Create Discord embed
                        embed = discord.Embed(
                            title = f"{event['name']}" if event['artist_name'] is None else f"{event['artist_name']} - {event['name']}",
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
                            event['eventid']
                        )
                        
                    except discord.errors.HTTPException as e:
                        logger.error(f"Failed to send embed for event {event['eventid']} ({event['name']}): {e}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing event {event['eventid']}: {e}")
                        continue
                
                logger.info(f"Completed batch of {len(batch)} events")
                
        except Exception as e:
            logger.error(f"Error notifying events: {e}")
        finally:
            logger.debug("Database connection released.")