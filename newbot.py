import discord
from discord.ext import tasks, commands
from config.db_pool import initialize_db_pool, close_db_pool
from tasks.notify_events import notify_events
from config.config import DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID, DISCORD_CHANNEL_ID_TWO, DATABASE_URL
from config.logging import logger
import asyncio
import os

intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await initialize_db_pool(DATABASE_URL)
    logger.info("Database pool initialized.")
    notify_events_task.start()
    check_reminders_task.start()

@bot.event
async def on_raw_reaction_add(payload):
    """Event handler for reactions added to messages"""
    # Check if the reaction is a bell emoji (🔔)
    if str(payload.emoji) != "🔔":
        return
    
    # Get the channel and message
    channel = bot.get_channel(payload.channel_id)
    if not channel:
        return
    
    try:
        message = await channel.fetch_message(payload.message_id)
        
        # Check if the message is from our bot and has embeds
        if message.author.id != bot.user.id or not message.embeds:
            return
            
        # Extract the URL from the embed
        embed = message.embeds[0]
        event_url = embed.url
        
        if not event_url:
            logger.warning(f"No URL found in message {message.id}")
            return
            
        # Find the event in the database and set a reminder
        from config.db_pool import db_pool
        
        async with db_pool.acquire() as conn:
            # Get the event based on URL
            event = await conn.fetchrow(
                "SELECT eventID, ticketOnsaleStart FROM Events WHERE url = $1",
                event_url
            )
            
            if not event:
                logger.warning(f"No event found with URL: {event_url}")
                return
                
            # Calculate reminder time (12 hours before ticket sale)
            from datetime import timedelta
            reminder_time = event['ticketonsalestart'] - timedelta(hours=12)
            
            # Set the reminder
            await conn.execute(
                "UPDATE Events SET reminder = $1::TIMESTAMPTZ WHERE eventID = $2",
                reminder_time, event['eventid']
            )
            
            logger.info(f"Reminder set for event {event['eventid']} at {reminder_time}")
            
            # React to the user's reaction to confirm
            await message.add_reaction("✅")
            
    except Exception as e:
        logger.error(f"Error processing reaction: {e}", exc_info=True)

@tasks.loop(minutes=1)
async def notify_events_task():
    logger.info("Starting event notification process...")
    try:
        await notify_events(bot, DISCORD_CHANNEL_ID, notable_only=True)
        await notify_events(bot, DISCORD_CHANNEL_ID_TWO, notable_only=False)
    except Exception as e:
        logger.error(f"Error during event notification: {e}", exc_info=True)

@tasks.loop(minutes=5)
async def check_reminders_task():
    """Check for upcoming reminders and send notifications"""
    logger.info("Checking for upcoming reminders...")
    try:
        from config.db_pool import db_pool
        from datetime import datetime, timezone, timedelta
        import pytz
        
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
                # Get the appropriate channel based on whether the artist is notable
                is_notable = False
                if event['artist_name']:
                    is_notable = await conn.fetchval(
                        "SELECT notable FROM Artists WHERE name = $1",
                        event['artist_name']
                    )
                channel_id = DISCORD_CHANNEL_ID if is_notable else DISCORD_CHANNEL_ID_TWO
                
                channel = bot.get_channel(channel_id)
                if not channel:
                    logger.error(f"Discord channel with ID {channel_id} not found.")
                    continue
                
                # Format times
                est_tz = pytz.timezone('America/New_York')
                onsale_start_utc = event['ticketonsalestart']
                onsale_start_est = onsale_start_utc.astimezone(est_tz)
                onsale_start = onsale_start_est.strftime("%B %d, %Y at %I:%M %p EST")
                
                # Check if reminder is past-due
                is_past_due = event['reminder'] < now
                
                # Adjust message for past-due reminders
                reminder_text = "**Tickets go on sale in ~12 hours!**"
                if is_past_due:
                    # Calculate how many hours until ticket sale
                    hours_until_sale = (event['ticketonsalestart'] - now).total_seconds() / 3600
                    if hours_until_sale < 0:
                        reminder_text = "**Tickets are now on sale!**"
                    else:
                        reminder_text = f"**Tickets go on sale in ~{int(hours_until_sale)} hours!**"
                
                # Create reminder embed
                embed = discord.Embed(
                    title=f"🔔 REMINDER: {event['name'] if not event['artist_name'] else f"{event['artist_name']} - {event['name']}"}",
                    url=event['url'],
                    description=(
                        f"{reminder_text}\n"
                        f"**Location**: {event['city']}, {event['state']}\n"
                        f"**Sale Start**: {onsale_start}\n\n"
                        f"React with 🔔 to this message to receive another reminder."
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
        logger.error(f"Error checking reminders: {e}", exc_info=True)

async def shutdown():
    logger.info("Shutting down bot...")
    notify_events_task.stop()
    check_reminders_task.stop()
    await close_db_pool()

async def main():
    logger.info("Starting bot...")
    for filename in os.listdir("./commands"):
        if filename.endswith(".py") and filename != "__init__.py":
            await bot.load_extension(f"commands.{filename[:-3]}")
    await bot.start(DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Shutting down bot.")
    finally:
        asyncio.run(shutdown())