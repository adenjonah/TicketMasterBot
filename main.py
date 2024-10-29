import discord
from discord.ext import tasks
import logging
from dbEditor import fetch_today_events
from query import notify_events
from commandHandler import bot
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

# Set up logging
logging.basicConfig(level=logging.INFO, filename="event_log.log", filemode="a",
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("main")

@tasks.loop(minutes=1)
async def fetch_and_notify_events():
    """Task to fetch events from the Ticketmaster API and notify Discord of unsent events."""
    fetch_today_events()
    logger.info("Fetched today's events.")
    await notify_events(bot, CHANNEL_ID)

@bot.event
async def on_ready():
    fetch_and_notify_events.start()
    logger.info("Bot connected and task started.")

if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)
