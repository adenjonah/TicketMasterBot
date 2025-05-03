import discord
from config.logging import logger
from datetime import datetime, timezone, timedelta
import pytz

async def check_reminders(bot, channel_id_notable, channel_id_regular, channel_id_european=None, channel_id_european_regular=None):
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
                    Events.region,
                    Venues.city, 
                    Venues.state,
                    Artists.name AS artist_name,
                    Artists.notable
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
                await process_reminder(bot, conn, event, channel_id_notable, channel_id_regular, channel_id_european, channel_id_european_regular, now)
                
    except Exception as e:
        logger.error(f"Error checking reminders: {e}", exc_info=True)

async def process_reminder(bot, conn, event, channel_id_notable, channel_id_regular, channel_id_european, channel_id_european_regular, now):
    """Process and send a reminder for a specific event"""
    try:
        # Determine which channel to use based on event region and artist notability
        is_notable = event['notable'] if event['notable'] is not None else False
        is_european = event['region'] == 'eu'
        
        # Get appropriate channel ID based on region and notability
        if is_european:
            if is_notable:
                # Notable European event -> EU1 (if available, otherwise US1)
                channel_id = channel_id_european if channel_id_european else channel_id_notable
            else:
                # Non-notable European event -> EU2 (if available, otherwise US2)
                channel_id = channel_id_european_regular if channel_id_european_regular else channel_id_regular
        else:
            if is_notable:
                # Notable non-European event -> US1
                channel_id = channel_id_notable
            else:
                # Non-notable non-European event -> US2
                channel_id = channel_id_regular
        
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
            
        # Set appropriate color based on region
        embed_color = discord.Color.gold()  # Default reminder color
        if event['region'] == 'eu':
            embed_color = discord.Color.purple()  # European events get a different color
        
        # Add region text to the footer
        region_text = ""
        if event['region'] == 'eu':
            region_text = " | Region: Europe"
        elif event['region'] == 'no':
            region_text = " | Region: North"
        elif event['region'] == 'ea':
            region_text = " | Region: East"
        elif event['region'] == 'so':
            region_text = " | Region: South"
        elif event['region'] == 'we':
            region_text = " | Region: West"
        elif event['region'] == 'co':
            region_text = " | Region: Comedy"
        elif event['region'] == 'th':
            region_text = " | Region: Theater"
        elif event['region'] == 'fi':
            region_text = " | Region: Film"
        
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
        
        # Create reminder embed
        embed = discord.Embed(
            title=f"🔔 REMINDER: {event['name'] if not event['artist_name'] else f"{event['artist_name']} - {event['name']}"}",
            url=event['url'],
            description=(
                f"{reminder_text}\n"
                f"**Location**: {location_text}\n"
                f"**Sale Start**: {onsale_start}{footer_text}"
            ),
            color=embed_color
        )
        
        # Set footer with region information
        embed.set_footer(text=f"Ticket sale reminder{region_text}")
        
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