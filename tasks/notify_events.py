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
        logger.warning("No URL provided, using fallback URL")
        return "https://example.com"  # Fallback URL if none is provided
        
    # Remove any whitespace
    url = url.strip()
    
    # Log the original URL for debugging
    logger.debug(f"Original URL: {url}")
    
    # Check and fix various incorrect URL formats
    if url.startswith('ttps://'):
        url = 'https://' + url[7:]
        logger.debug(f"Fixed 'ttps://' to 'https://': {url}")
    elif url.startswith('hhttps://'):
        url = 'https://' + url[8:]
        logger.debug(f"Fixed 'hhttps://' to 'https://': {url}")
    elif not (url.startswith('http://') or url.startswith('https://')):
        url = 'https://' + url
        logger.debug(f"Added 'https://' prefix: {url}")
    
    # Basic URL validation
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        # Log parsed components for debugging
        logger.debug(f"Parsed URL components - Scheme: {parsed.scheme}, Netloc: {parsed.netloc}, Path: {parsed.path}")
        
        if not all([parsed.scheme, parsed.netloc]):
            logger.warning(f"Invalid URL format: {url} - Missing scheme or netloc")
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
            
        logger.debug(f"Final fixed URL: {fixed_url}")
        return fixed_url
    except Exception as e:
        logger.error(f"Error fixing URL {url}: {e}", exc_info=True)
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
                
                # Explicitly check for EU events
                eu_count = await conn.fetchval("""
                SELECT COUNT(*) FROM Events 
                WHERE sentToDiscord = FALSE 
                AND LOWER(region) = 'eu'
                """)
                logger.info(f"Found {eu_count} unsent European events with exact match 'eu'")
                
                # Exactly matches on capitalization
                eu_case_counts = await conn.fetch("""
                SELECT region, COUNT(*) FROM Events 
                WHERE sentToDiscord = FALSE 
                AND region LIKE 'e%'
                GROUP BY region
                """)
                logger.info(f"Case analysis of EU regions: {eu_case_counts}")
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
        logger.info("Filtering for European events (region='eu')")
    elif region == 'non-eu':
        filters.append("(LOWER(Events.region) != 'eu' OR Events.region IS NULL)")
        logger.info("Filtering for non-European events")
    
    # Add filters to the query
    filter_clause = ' AND '.join(filters)
    if filters:
        query = f"{base_query} AND {filter_clause}"
    else:
        query = base_query

    # Log the complete SQL query for debugging
    logger.info(f"SQL Query: {query}")

    async with db_pool.acquire() as conn:
        try:
            logger.debug("Acquired database connection.")
            
            # Count matching events with a simple COUNT(*) query
            count_query = f"""
            SELECT COUNT(*) 
            FROM Events
            LEFT JOIN Venues ON Events.venueID = Venues.venueID
            LEFT JOIN Artists ON Events.artistID = Artists.artistID
            WHERE Events.sentToDiscord = FALSE
            AND {filter_clause}
            """
            
            # Execute and log the count query
            logger.info(f"Count SQL Query: {count_query}")
            total_matching = await conn.fetchval(count_query)
            logger.info(f"Found {total_matching} total matching events in database for region={region}, notable_only={notable_only}")
            
            # Now get the actual events to notify
            events_to_notify = await conn.fetch(query)
            logger.info(f"Fetched {len(events_to_notify)} unsent events to notify for region={region}, notable_only={notable_only}")

            if not events_to_notify:
                region_str = f"({region}) " if region else ""
                logger.info(f"No new {region_str}{"notable" if notable_only else "non-notable"} events to notify.")
                return

            channel = bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Discord channel with ID {channel_id} not found.")
                return

            utc_tz = pytz.utc
            est_tz = pytz.timezone('America/New_York')

            for event in events_to_notify:
                logger.debug(f"Processing event: {event}")

                # Log the original URLs for debugging
                logger.debug(f"Event URL before fixing: {event['url']}")
                logger.debug(f"Image URL before fixing: {event['image_url']}")

                # Extract and manually convert ticketOnsaleStart to EST
                onsale_start = "TBA"
                if event['ticketonsalestart']:
                    onsale_start_utc = event['ticketonsalestart']
                    onsale_start_est = onsale_start_utc.astimezone(est_tz)
                    onsale_start = onsale_start_est.strftime("%B %d, %Y at %I:%M %p EST")

                # Extract and manually convert eventDate to EST
                event_date = "TBA"
                if event['eventdate']:
                    event_date_utc = event['eventdate']
                    event_date_est = event_date_utc.astimezone(est_tz)
                    event_date = event_date_est.strftime("%B %d, %Y at %I:%M %p EST")

                # Log the converted values
                logger.debug(f"Converted onsale_start to EST: {onsale_start}")
                logger.debug(f"Converted event_date to EST: {event_date}")

                # Set appropriate color based on region
                embed_color = discord.Color.blue()
                if event['region'] == 'eu':
                    embed_color = discord.Color.purple()  # European events get a different color

                # Format location based on region
                location_text = "TBA"
                if event['region'] == 'eu':
                    # For European events, use city and country (Venues.state contains country for EU events)
                    if event['city']:
                        if event['state']:
                            location_text = f"{event['city']}, {event['state']}"
                        else:
                            # For European cities without a state/country, just show the city
                            location_text = f"{event['city']}"
                else:
                    # For US events, use city and state as before
                    if event['city'] and event['state']:
                        location_text = f"{event['city']}, {event['state']}"
                    elif event['city']:
                        location_text = f"{event['city']}"
                    elif event['state']:
                        location_text = f"{event['state']}"

                # Fix URLs before creating embed
                fixed_event_url = _fix_url(event['url'])
                fixed_image_url = _fix_url(event['image_url']) if event['image_url'] else None
                
                logger.debug(f"Fixed event URL: {fixed_event_url}")
                logger.debug(f"Fixed image URL: {fixed_image_url}")

                # Create Discord embed
                embed = discord.Embed(
                    title = f"{event['name']}" if event['artist_name'] is None else f"{event['artist_name']} - {event['name']}",
                    url=fixed_event_url,
                    description=(
                        f"**Location**: {location_text}\n"
                        f"**Event Date**: {event_date}\n"
                        f"**Sale Start**: {onsale_start}\n\n"
                        f"React with 🔔 to set a reminder for this event!"
                    ),
                    color=embed_color
                )
                if fixed_image_url:
                    embed.set_image(url=fixed_image_url)

                # Process presale information from the JSON data
                if event['presaledata']:
                    try:
                        presales = json.loads(event['presaledata'])
                        if presales:
                            # Sort presales by start datetime to find the earliest presale
                            presales.sort(key=lambda x: parser.parse(x['startDateTime']))
                            # Only use the earliest presale
                            earliest_presale = presales[0]
                            
                            presale_start_utc = parser.parse(earliest_presale['startDateTime'])
                            presale_start_est = presale_start_utc.astimezone(est_tz)
                            presale_start = presale_start_est.strftime("%B %d, %Y at %I:%M %p EST")
                            
                            presale_end_utc = parser.parse(earliest_presale['endDateTime'])
                            presale_end_est = presale_end_utc.astimezone(est_tz)
                            presale_end = presale_end_est.strftime("%B %d, %Y at %I:%M %p EST")
                            
                            presale_info = f"**{earliest_presale['name']}**\nStart: {presale_start}\nEnd: {presale_end}"
                            
                            embed.add_field(name="📅 Earliest Presale", value=presale_info, inline=False)
                    except Exception as e:
                        logger.error(f"Error processing presale data for event {event['eventid']}: {e}", exc_info=True)

                # Add region footer text
                region_text = None  # Default to no region text
                if event['region'] == 'eu':
                    region_text = "Region: Europe"
                elif event['region'] == 'no':
                    region_text = "Region: North"
                elif event['region'] == 'ea':
                    region_text = "Region: East"
                elif event['region'] == 'so':
                    region_text = "Region: South"
                elif event['region'] == 'we':
                    region_text = "Region: West"
                elif event['region'] == 'co':
                    region_text = "Region: Comedy"
                elif event['region'] == 'th':
                    region_text = "Region: Theater"
                elif event['region'] == 'fi':
                    region_text = "Region: Film"
                
                # Only set the footer if we have a valid region to display
                if region_text:
                    embed.set_footer(text=region_text)

                # Send notification to Discord channel
                logger.debug(f"Sending event notification for {event['name']} (ID: {event['eventid']})")
                try:
                    await channel.send(embed=embed)
                except discord.errors.HTTPException as e:
                    logger.error(f"Failed to send embed for event {event['eventid']} ({event['name']}): {e}")
                    logger.error(f"Event URL: {fixed_event_url}")
                    logger.error(f"Image URL: {fixed_image_url}")
                    continue  # Skip this event and continue with the next one

                # Mark event as sent in the database
                await conn.execute(
                    "UPDATE Events SET sentToDiscord = TRUE WHERE eventID = $1",
                    event['eventid']
                )
                logger.info(f"Notified and marked event as sent: {event['name']} (ID: {event['eventid']})")
        except Exception as e:
            logger.error(f"Error notifying events: {e}", exc_info=True)
        finally:
            logger.debug("Database connection released.")