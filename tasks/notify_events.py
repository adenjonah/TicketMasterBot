import discord
from config.logging import logger
from helpers.formatting import format_date_human_readable
import pytz
import json
from dateutil import parser
from datetime import datetime

def _fix_url(url):
    """Ensures a URL has the correct http/https scheme."""
    if not url:
        return "https://example.com"  # Fallback URL if none is provided
        
    # Check and fix various incorrect URL formats
    if url.startswith('ttps://'):
        url = 'https://' + url[7:]
    elif url.startswith('hhttps://'):
        url = 'https://' + url[8:]
    elif not (url.startswith('http://') or url.startswith('https://')):
        url = 'https://' + url
        
    return url

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
    if filters:
        query = f"{base_query} AND {' AND '.join(filters)}"
    else:
        query = base_query

    # Log the complete SQL query for debugging
    logger.info(f"SQL Query: {query}")

    async with db_pool.acquire() as conn:
        try:
            logger.debug("Acquired database connection.")
            
            # First, count how many matching events exist in the database
            count_query = query.replace("SELECT \n            Events.eventID", "SELECT COUNT(*)")
            count_query = count_query.split("ORDER BY")[0] if "ORDER BY" in count_query else count_query
            
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

                # Create Discord embed
                embed = discord.Embed(
                    title = f"{event['name']}" if event['artist_name'] is None else f"{event['artist_name']} - {event['name']}",
                    url=_fix_url(event['url']),
                    description=(
                        f"**Location**: {event['city']}, {event['state']}\n"
                        f"**Event Date**: {event_date}\n"
                        f"**Sale Start**: {onsale_start}\n\n"
                        f"React with 🔔 to set a reminder for this event!"
                    ),
                    color=embed_color
                )
                if event['image_url']:
                    embed.set_image(url=_fix_url(event['image_url']))

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
                region_text = "Region: Unknown"
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
                
                embed.set_footer(text=region_text)

                # Send notification to Discord channel
                logger.debug(f"Sending event notification for {event['name']} (ID: {event['eventid']})")
                await channel.send(embed=embed)

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