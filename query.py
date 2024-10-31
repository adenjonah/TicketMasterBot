import sqlite3
import discord
import logging
from datetime import datetime, timezone

# Set up message-specific logging
message_logger = logging.getLogger("messageLogger")
message_logger.setLevel(logging.INFO)
message_handler = logging.FileHandler("message_log.log")
message_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
message_logger.addHandler(message_handler)

# Database connection
conn = sqlite3.connect('events.db')
c = conn.cursor()

async def notify_events(bot, channel_id):
    """Notifies Discord about unsent events associated with notable artists in the database."""
    # Select unsent events with notable artists only
    c.execute('''
    SELECT Events.eventID, Events.name, Events.ticketOnsaleStart, Events.eventDate, Events.url, 
           Venues.city, Venues.state, Events.image_url, Artists.name
    FROM Events
    LEFT JOIN Venues ON Events.venueID = Venues.venueID
    LEFT JOIN Artists ON Events.artistID = Artists.artistID
    WHERE Events.sentToDiscord = 0 AND Artists.notable = 1
    ''')

    events_to_notify = c.fetchall()
    channel = bot.get_channel(channel_id)

    if events_to_notify and channel:
        for event in events_to_notify:
            # Creating an embed message with event details
            embed = discord.Embed(
                title=f"{event[8]} - {event[1]}",  # Adding artist's name to the title for context
                url=event[4],
                description=f"**Location**: {event[5]}, {event[6]}\n**Event Date**: {event[3]}\n**Sale Start**: {event[2]}"
            )
            if event[7]:  # Set image if available
                embed.set_image(url=event[7])
            
            # Send the embed to the Discord channel
            await channel.send(embed=embed)
            message_logger.info(f"Notified Discord about notable event: {event[1]} by {event[8]}")

            # Mark event as sent in the database (collect eventIDs to mark later in batch)
            c.execute("UPDATE Events SET sentToDiscord = 1 WHERE eventID = ?", (event[0],))

        # Commit all sent updates in batch after looping
        conn.commit()
    else:
        if not events_to_notify:
            message_logger.info("No new notable events to notify.")
        if not channel:
            message_logger.error(f"Discord channel with ID {channel_id} not found.")
