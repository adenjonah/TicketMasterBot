import discord
from config.logging import logger
from datetime import datetime, timezone, timedelta
import pytz

async def check_reminders(bot, channel_id_notable, channel_id_regular):
    """Check for upcoming reminders and send notifications"""
    logger.info("Checking for upcoming reminders...")
    try:
        from config.db_pool import db_pool
        
        # Get current time in UTC
        now = datetime.now(timezone.utc)
        # Look for reminders within the next 5 minutes or in the past
        check_time = now + timedelta(minutes=5)
        
        async with db_pool.acquire() as conn:
            # Find events with reminders in the next 5 minutes or in the past
            events = await conn.fetch('''
                SELECT 
                    Events.eventID, 
                    Events.name, 
                    Events.ticketOnsaleStart, 
                    Events.reminder,
                    Events.url,
                    Venues.city, 
                    Venues.state,
                    Artists.name AS artist_name
                FROM Events
                LEFT JOIN Venues ON Events.venueID = Venues.venueID
                LEFT JOIN Artists ON Events.artistID = Artists.artistID
                WHERE Events.reminder IS NOT NULL
                AND Events.reminder <= $1
            ''', check_time)
            
            if not events:
                logger.debug("No upcoming or past reminders found.")
                return
                
            logger.info(f"Found {len(events)} events with upcoming or past reminders.")
            
            # Process each event with a reminder
            for event in events:
                await process_reminder(bot, conn, event, channel_id_notable, channel_id_regular, now)
                
    except Exception as e:
        logger.error(f"Error checking reminders: {e}", exc_info=True)

async def process_reminder(bot, conn, event, channel_id_notable, channel_id_regular, now):
    """Process and send a reminder for a specific event"""
    try:
        # Get the appropriate channel based on whether the artist is notable
        is_notable = False
        if event['artist_name']:
            is_notable = await conn.fetchval(
                "SELECT notable FROM Artists WHERE name = $1",
                event['artist_name']
            )
        channel_id = channel_id_notable if is_notable else channel_id_regular
        
        channel = bot.get_channel(channel_id)
        if not channel:
            logger.error(f"Discord channel with ID {channel_id} not found.")
            return
        
        # Format times
        est_tz = pytz.timezone('America/New_York')
        onsale_start_utc = event['ticketonsalestart']
        onsale_start_est = onsale_start_utc.astimezone(est_tz)
        onsale_start = onsale_start_est.strftime("%B %d, %Y at %I:%M %p EST")
        
        # Check if reminder is past-due
        is_past_due = event['reminder'] < now
        
        # Calculate hours until ticket sale
        hours_until_sale = (event['ticketonsalestart'] - now).total_seconds() / 3600
        
        # Adjust message for reminders
        reminder_text = "**Tickets go on sale in ~12 hours!**"
        can_set_another_reminder = True
        
        if hours_until_sale < 0:
            reminder_text = "**Tickets are now on sale!**"
            can_set_another_reminder = False
        elif hours_until_sale < 1:
            reminder_text = f"**Tickets go on sale in less than 1 hour!**"
            can_set_another_reminder = False
        else:
            reminder_text = f"**Tickets go on sale in ~{int(hours_until_sale)} hours!**"
        
        # Define the footer message
        footer_text = "\n\nReact with 🔔 to this message to receive another reminder 1 hour before sale."
        if not can_set_another_reminder:
            footer_text = "\n\nTickets are now on sale or will be very soon. Good luck!"
        
        # Create reminder embed
        embed = discord.Embed(
            title=f"🔔 REMINDER: {event['name'] if not event['artist_name'] else f"{event['artist_name']} - {event['name']}"}",
            url=event['url'],
            description=(
                f"{reminder_text}\n"
                f"**Location**: {event['city']}, {event['state']}\n"
                f"**Sale Start**: {onsale_start}{footer_text}"
            ),
            color=discord.Color.gold()
        )
        
        # Send reminder
        await channel.send(embed=embed)
        if is_past_due:
            logger.info(f"Sent past-due reminder for event: {event['eventid']}")
        else:
            logger.info(f"Sent reminder for event: {event['eventid']}")
        
        # Clear the reminder after sending
        await conn.execute(
            "UPDATE Events SET reminder = NULL WHERE eventID = $1",
            event['eventid']
        )
    except Exception as e:
        logger.error(f"Error processing reminder for event {event['eventid']}: {e}", exc_info=True) 