import discord
from discord.ext import tasks
from dbEditor import fetch_events, initialize_db
from notifier import notify_events
from commandHandler import bot
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
MAIN_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))  # Channel for notable artist events only
SECONDARY_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID_TWO'))  # Channel for all unsent events

async def initialize_bot():
    """Initialize the bot, including the database and loop tasks."""
    print("Initializing database...")
    await initialize_db()  # Assuming `initialize_db` is async

@tasks.loop(minutes=1)
async def fetch_and_notify_events():
    """Fetch events and send notifications to respective Discord channels."""
    print("Starting event fetch and notification process...")
    
    # Fetch unsent events
    print("Fetching events...")
    await fetch_events(bot)  
    print("Completed event fetch.")

    # Notify notable events
    print("Notifying MAIN_CHANNEL_ID (notable events)...")
    await notify_events(bot, MAIN_CHANNEL_ID, notable_only=True)
    print("Notified MAIN_CHANNEL_ID.")

    # Notify all unsent events
    print("Notifying SECONDARY_CHANNEL_ID (all unsent events)...")
    await notify_events(bot, SECONDARY_CHANNEL_ID, notable_only=False)
    print("Notified SECONDARY_CHANNEL_ID.")

@bot.event
async def on_ready():
    """Event triggered when the bot connects to Discord."""
    print("Bot is ready.")
    if not fetch_and_notify_events.is_running():
        print("Starting scheduled fetch_and_notify_events loop.")
        fetch_and_notify_events.start()

if __name__ == "__main__":
    # Run the bot
    try:
        print("Starting bot...")
        bot.run(DISCORD_BOT_TOKEN)
    except Exception as e:
        print(f"Failed to start bot: {e}")