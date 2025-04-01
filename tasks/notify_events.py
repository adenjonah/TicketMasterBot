import discord
from config.logging import logger
from helpers.formatting import format_date_human_readable
import pytz
import json
from dateutil import parser
from datetime import datetime

async def notify_events(bot, channel_id, notable_only=False):
    from config.db_pool import db_pool  # Import shared db_pool here
    """
    Notifies Discord about unsent events. If notable_only is True, only notifies about notable artist events.

    Parameters:
        bot (discord.Client): The Discord bot instance.
        channel_id (int): The Discord channel ID to send notifications to.
        notable_only (bool): Whether to only notify events with notable artists.
    """
    logger.debug(f"Starting notify_events with channel_id={channel_id}, notable_only={notable_only}")

    base_query = '''
        SELECT 
            Events.eventID, 
            Events.name, 
            Events.ticketOnsaleStart, 
            Events.eventDate, 
            Events.url, 
            Events.presaleData,
            Venues.city, 
            Venues.state, 
            Events.image_url, 
            Artists.name AS artist_name
        FROM Events
        LEFT JOIN Venues ON Events.venueID = Venues.venueID
        LEFT JOIN Artists ON Events.artistID = Artists.artistID
        WHERE Events.sentToDiscord = FALSE
    '''

    if notable_only:
        notable_filter = "AND Artists.notable = TRUE"
    else:
        notable_filter = "AND (Artists.notable = FALSE OR Artists.artistID IS NULL)"

    query = f"{base_query} {notable_filter}"

    logger.debug(f"Database query prepared: {query}")

    async with db_pool.acquire() as conn:
        try:
            logger.debug("Acquired database connection.")
            events_to_notify = await conn.fetch(query)
            logger.debug(f"Fetched {len(events_to_notify)} events to notify.")

            if not events_to_notify:
                logger.info(f"No new {"notable" if notable_only else "non-notable"} events to notify.")
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


                # Create Discord embed
                embed = discord.Embed(
                    title = f"{event['name']}" if event['artist_name'] is None else f"{event['artist_name']} - {event['name']}",
                    url=event['url'],
                    description=(
                        f"**Location**: {event['city']}, {event['state']}\n"
                        f"**Event Date**: {event_date}\n"
                        f"**Sale Start**: {onsale_start}\n\n"
                        f"React with 🔔 to set a reminder for this event!"
                    ),
                    color=discord.Color.blue()
                )
                if event['image_url']:
                    embed.set_image(url=event['image_url'])

                # Process presale information from the JSON data
                if event['presaledata']:
                    try:
                        presales = json.loads(event['presaledata'])
                        if presales:
                            presale_info = []
                            for presale in presales:
                                presale_start_utc = parser.parse(presale['startDateTime'])
                                presale_start_est = presale_start_utc.astimezone(est_tz)
                                presale_start = presale_start_est.strftime("%B %d, %Y at %I:%M %p EST")
                                
                                presale_end_utc = parser.parse(presale['endDateTime'])
                                presale_end_est = presale_end_utc.astimezone(est_tz)
                                presale_end = presale_end_est.strftime("%B %d, %Y at %I:%M %p EST")
                                
                                presale_info.append(f"**{presale['name']}**\nStart: {presale_start}\nEnd: {presale_end}")
                            
                            embed.add_field(name="📅 Presales", value="\n\n".join(presale_info), inline=False)
                    except Exception as e:
                        logger.error(f"Error processing presale data for event {event['eventid']}: {e}", exc_info=True)

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