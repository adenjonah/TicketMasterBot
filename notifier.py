import sqlite3
import discord
import logging
from datetime import datetime, timezone

# Set up message-specific logging
message_logger = logging.getLogger("messageLogger")
message_logger.setLevel(logging.INFO)
message_handler = logging.FileHandler("logs/message_log.log")
message_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
message_logger.addHandler(message_handler)

# Database connection
conn = sqlite3.connect('events.db', check_same_thread=False)
c = conn.cursor()

def format_date_human_readable(date_str):
    """Converts a date string from the database to a human-readable format."""
    try:
        # Attempt to parse full datetime format with time
        date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        # Fallback to parse date-only format (YYYY-MM-DD) if time is missing
        date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    
    # Format the day with an ordinal suffix
    day = date.day
    suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    
    # Manually format the hour to remove leading zero
    hour = date.strftime("%I").lstrip("0")  # Removes leading zero from 12-hour format hour
    formatted_time = f"{hour}:{date.strftime('%M %p')} UTC"
    
    return date.strftime(f"%B {day}{suffix}, %Y at ") + formatted_time

async def notify_events(bot, channel_id, notable_only=False):
    """Notifies Discord about unsent events. If notable_only is True, only notifies about notable artist events."""
    
    # Check if VF columns exist (backwards compatibility)
    c.execute("PRAGMA table_info(Events)")
    existing_columns = {row[1] for row in c.fetchall()}
    has_vf_columns = 'hasVF' in existing_columns and 'vfUrl' in existing_columns
    
    # Build query based on notable_only flag and column availability
    if has_vf_columns:
        query = '''
        SELECT Events.eventID, Events.name, Events.ticketOnsaleStart, Events.eventDate, Events.url, 
               Venues.city, Venues.state, Events.image_url, Artists.name, Events.hasVF, Events.vfUrl
        FROM Events
        LEFT JOIN Venues ON Events.venueID = Venues.venueID
        LEFT JOIN Artists ON Events.artistID = Artists.artistID
        WHERE Events.sentToDiscord = 0
        '''
    else:
        # Fallback for backwards compatibility (old DB schema)
        query = '''
        SELECT Events.eventID, Events.name, Events.ticketOnsaleStart, Events.eventDate, Events.url, 
               Venues.city, Venues.state, Events.image_url, Artists.name
        FROM Events
        LEFT JOIN Venues ON Events.venueID = Venues.venueID
        LEFT JOIN Artists ON Events.artistID = Artists.artistID
        WHERE Events.sentToDiscord = 0
        '''
    
    if notable_only:
        query += " AND Artists.notable = 1"

    # Execute the query and fetch results
    c.execute(query)
    events_to_notify = c.fetchall()
    
    # Get the specified channel
    channel = bot.get_channel(channel_id)

    # Check if there are events to notify and if the channel exists
    if events_to_notify and channel:
        for event in events_to_notify:
            # Format dates to be human-readable
            onsale_start = format_date_human_readable(event[2]) if event[2] else "TBA"
            event_date = format_date_human_readable(event[3]) if event[3] else "TBA"

            # Build description with VF info if available
            description = f"**Location**: {event[5]}, {event[6]}\n**Event Date**: {event_date}\n**Sale Start**: {onsale_start}"
            
            # Add Verified Fan link if available (backwards compatible)
            if has_vf_columns and len(event) >= 11 and event[9] and event[10]:
                description += f"\n**Verified Fan**: {event[10]}"

            # Create an embed message with event details
            embed = discord.Embed(
                title=f"{event[8]} - {event[1]}",  # Adding artist's name to the title for context
                url=event[4],
                description=description,
                color=discord.Color.blue()
            )
            if event[7]:  # Set image if available
                embed.set_image(url=event[7])
            
            # Send the embed to the Discord channel
            await channel.send(embed=embed)
            message_logger.info(f"Notified Discord about event: {event[1]} by {event[8]}")

            # Mark event as sent in the database
            c.execute("UPDATE Events SET sentToDiscord = 1 WHERE eventID = ?", (event[0],))
            conn.commit()  # Commit after each update to ensure it's saved

        # Commit all updates in batch after the loop
        conn.commit()
    else:
        if not events_to_notify:
            message_logger.info("No new events to notify.")
        if not channel:
            message_logger.error(f"Discord channel with ID {channel_id} not found.")
