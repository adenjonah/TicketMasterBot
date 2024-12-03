import discord
from config.logging import logger
from helpers.formatting import format_date_human_readable
from config.config import DEBUG

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

    query = '''
    SELECT Events.eventID, Events.name, Events.ticketOnsaleStart, Events.eventDate, Events.url, 
           Venues.city, Venues.state, Events.image_url, Artists.name
    FROM Events
    LEFT JOIN Venues ON Events.venueID = Venues.venueID
    LEFT JOIN Artists ON Events.artistID = Artists.artistID
    WHERE Events.sentToDiscord = FALSE
    '''
    if notable_only:
        query += " AND Artists.notable = TRUE"
    else:
        query += " AND Artists.notable = FALSE"

    logger.debug(f"Database query prepared: {query}")

    async with db_pool.acquire() as conn:
        try:
            logger.debug("Acquired database connection.")
            events_to_notify = await conn.fetch(query)
            logger.debug(f"Fetched {len(events_to_notify)} events to notify.")

            if not events_to_notify:
                logger.info("No new events to notify.")
                return

            channel = bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Discord channel with ID {channel_id} not found.")
                return

            for event in events_to_notify:
                logger.debug(f"Processing event: {event}")
                onsale_start = format_date_human_readable(event['ticketonsalestart']) if event['ticketonsalestart'] else "TBA"
                event_date = format_date_human_readable(event['eventdate']) if event['eventdate'] else "TBA"

                embed = discord.Embed(
                    title=f"{event['name']} - {event['name']}",
                    url=event['url'],
                    description=f"**Location**: {event['city']}, {event['state']}\n"
                                f"**Event Date**: {event_date}\n"
                                f"**Sale Start**: {onsale_start}",
                    color=discord.Color.blue()
                )
                if event['image_url']:
                    embed.set_image(url=event['image_url'])

                logger.debug(f"Sending event notification for {event['name']} (ID: {event['eventid']})")
                await channel.send(embed=embed)

                # Fix the issue with tuple
                await conn.execute("UPDATE Events SET sentToDiscord = TRUE WHERE eventID = $1", event['eventid'])
                logger.info(f"Notified and marked event as sent: {event['name']} (ID: {event['eventid']})")
        except Exception as e:
            logger.error(f"Error notifying events: {e}", exc_info=True)
        finally:
            logger.debug("Database connection released.")