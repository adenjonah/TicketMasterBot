import discord
from discord.ext import tasks
import logging
from dbEditor import fetch_events, initialize_db
from query import notify_events
from commandHandler import bot
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

initialize_db()

# Set up general event logging
event_logger = logging.getLogger("eventLogger")
event_logger.setLevel(logging.INFO)
event_handler = logging.FileHandler("logs/event_log.log")
event_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
event_logger.addHandler(event_handler)

@tasks.loop(minutes=1)
async def fetch_and_notify_events():
    """Fetches events and notifies Discord of unsent events."""
    await fetch_events(bot, CHANNEL_ID)  # Pass bot and CHANNEL_ID
    event_logger.info("Fetched today's events.")
    await notify_events(bot, CHANNEL_ID)

@bot.event
async def on_ready():
    fetch_and_notify_events.start()
    event_logger.info("Bot connected and task started.")

if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)