from config.config import (
    DISCORD_BOT_TOKEN,
    DISCORD_CHANNEL_ID,
    DISCORD_CHANNEL_ID_TWO,
    TICKETMASTER_API_KEY,
    REDIRECT_URI,
    DATABASE_URL,
    DEBUG,
)

import psycopg2
from psycopg2.extras import DictCursor
import discord
from datetime import datetime, timezone
import os

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    """Establish and return a PostgreSQL connection."""
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def format_date_human_readable(date_input):
    """Converts a date string or datetime object to a human-readable format."""
    if isinstance(date_input, datetime):
        # If it's already a datetime object, ensure it's in UTC
        date = date_input.astimezone(timezone.utc)
    else:
        # Parse the string into a datetime object
        try:
            date = datetime.strptime(date_input, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                date = datetime.strptime(date_input, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError as e:
                raise ValueError(f"Invalid date format: {date_input}") from e

    # Format the day with an ordinal suffix
    day = date.day
    suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

    # Format the time in 12-hour format with UTC timezone
    formatted_time = date.strftime(f"%B {day}{suffix}, %Y at %-I:%M %p UTC")

    return formatted_time

async def notify_events(bot, channel_id, notable_only=False):
    """Notifies Discord about unsent events. If notable_only is True, only notifies about notable artist events."""
    
    # Build query based on notable_only flag
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

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    try:
        # Execute the query and fetch results
        cur.execute(query)
        events_to_notify = cur.fetchall()
        
        # Get the specified channel
        channel = bot.get_channel(channel_id)

        # Check if there are events to notify and if the channel exists
        if events_to_notify and channel:
            for event in events_to_notify:
                # Format dates to be human-readable
                onsale_start = format_date_human_readable(event['ticketonsalestart']) if event['ticketonsalestart'] else "TBA"
                event_date = format_date_human_readable(event['eventdate']) if event['eventdate'] else "TBA"

                # Create an embed message with event details
                embed = discord.Embed(
                    title=f"{event['name']} - {event['name']}",  # Adding artist's name to the title for context
                    url=event['url'],
                    description=f"**Location**: {event['city']}, {event['state']}\n**Event Date**: {event_date}\n**Sale Start**: {onsale_start}",
                    color=discord.Color.blue()
                )
                if event['image_url']:  # Set image if available
                    embed.set_image(url=event['image_url'])
                
                # Send the embed to the Discord channel
                await channel.send(embed=embed)

                # Mark event as sent in the database
                cur.execute("UPDATE Events SET sentToDiscord = TRUE WHERE eventID = %s", (event['eventid'],))
                conn.commit()  # Commit after each update to ensure it's saved

    except Exception as e:
        print(f"Error notifying events: {e}")
    finally:
        cur.close()
        conn.close()