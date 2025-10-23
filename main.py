import discord
from discord.ext import tasks
import logging
from dbEditor import fetch_events, initialize_db
from notifier import notify_events
from commandHandler import bot
import os
from dotenv import load_dotenv

# Import VF checker if available (backwards compatible)
try:
    from vf_checker import recheck_recent_events
    VF_CHECKER_AVAILABLE = True
except ImportError:
    VF_CHECKER_AVAILABLE = False
    recheck_recent_events = None

# Load environment variables
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
MAIN_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))  # Channel for notable artist events only
SECONDARY_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID_TWO'))  # Channel for all unsent events

# Clear log files on startup
def clear_log_files():
    log_files = ["logs/event_log.log", "logs/db_log.log", "logs/message_log.log", "logs/api_log.log"]
    for log_file in log_files:
        with open(log_file, 'w'):
            pass  # Open in write mode to clear the file

clear_log_files()  # Clear logs

# Initialize database
initialize_db()

# Set up general event logging
event_logger = logging.getLogger("eventLogger")
event_logger.setLevel(logging.INFO)
event_handler = logging.FileHandler("logs/event_log.log")
event_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
event_logger.addHandler(event_handler)

@tasks.loop(minutes=1)
async def fetch_and_notify_events():
    """Fetches events and notifies Discord of unsent events, differentiating by channel."""
    
    # Fetch all events, unsent notable events, and send to respective channels
    await fetch_events(bot)  # Pass bot and MAIN_CHANNEL_ID for fetching notable events
    event_logger.info("Fetched events.")

    # Notify notable events to MAIN_CHANNEL_ID
    await notify_events(bot, MAIN_CHANNEL_ID, notable_only=True)
    
    # Notify all unsent events to SECONDARY_CHANNEL_ID
    await notify_events(bot, SECONDARY_CHANNEL_ID, notable_only=False)

@tasks.loop(minutes=10)
async def recheck_vf_signups():
    """Periodically recheck recent events for VF signups that may have been added later."""
    if not VF_CHECKER_AVAILABLE:
        return
    try:
        await recheck_recent_events()
        event_logger.info("Completed VF recheck for recent events.")
    except Exception as e:
        event_logger.error(f"Error during VF recheck: {e}")

@bot.event
async def on_ready():
    # Check if the task is already running
    if not fetch_and_notify_events.is_running():
        fetch_and_notify_events.start()
        event_logger.info("Bot connected and task started.")
    else:
        event_logger.info("Bot reconnected; fetch_and_notify_events task is already running.")
    
    # Start VF recheck task (if available)
    if VF_CHECKER_AVAILABLE:
        if not recheck_vf_signups.is_running():
            recheck_vf_signups.start()
            event_logger.info("VF recheck task started.")
        else:
            event_logger.info("VF recheck task is already running.")
    else:
        event_logger.info("VF checker module not available, VF recheck task skipped.")

if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)