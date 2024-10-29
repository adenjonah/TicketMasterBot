import sqlite3
import discord
import logging
from datetime import datetime, timezone, timedelta

# Set up message-specific logging
message_logger = logging.getLogger("messageLogger")
message_logger.setLevel(logging.INFO)
message_handler = logging.FileHandler("message_log.log")
message_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
message_logger.addHandler(message_handler)

conn = sqlite3.connect('events.db')
c = conn.cursor()

async def notify_events(bot, channel_id):
    """Notifies Discord about unsent events whose ticket sale start is within the next minute."""
    now = datetime.now(timezone.utc)
    minute_ahead = now + timedelta(minutes=1)

    c.execute('''
    SELECT Events.eventID, Events.name, Events.ticketOnsaleStart, Events.eventDate, Events.url, Venues.city, Venues.state, Events.image_url, Artists.name
    FROM Events
    LEFT JOIN Venues ON Events.venueID = Venues.venueID
    LEFT JOIN Artists ON Events.artistID = Artists.artistID
    WHERE Events.sentToDiscord = 0 AND Events.ticketOnsaleStart <= ?
    ''', (minute_ahead.isoformat(),))

    events_to_notify = c.fetchall()
    channel = bot.get_channel(channel_id)

    if events_to_notify and channel:
        for event in events_to_notify:
            embed = discord.Embed(
                title=event[1], 
                url=event[4], 
                description=f"**Location**: {event[5]}, {event[6]}\n**Event Date**: {event[3]}\n**Sale Start**: {event[2]}"
            )
            if event[7]:
                embed.set_image(url=event[7])
            await channel.send(embed=embed)
            message_logger.info(f"Notified Discord about event: {event[1]}")

            c.execute("UPDATE Events SET sentToDiscord = 1 WHERE eventID = ?", (event[0],))
            conn.commit()