import discord
from discord.ext import tasks, commands
from config.db_pool import initialize_db_pool, close_db_pool
from tasks.notify_events import notify_events
from config.config import DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID, DISCORD_CHANNEL_ID_TWO, DATABASE_URL
from config.logging import logger
import asyncio

# Define intents for the bot
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    """Event triggered when the bot is ready."""
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await initialize_db_pool(DATABASE_URL)
    logger.info("Database pool initialized.")
    notify_events_task.start()

@tasks.loop(minutes=1)
async def notify_events_task():
    """Periodic task to notify Discord about events."""
    logger.info("Starting event notification process...")
    try:
        await notify_events(bot, DISCORD_CHANNEL_ID, notable_only=True)
        await notify_events(bot, DISCORD_CHANNEL_ID_TWO, notable_only=False)
    except Exception as e:
        logger.error(f"Error during event notification: {e}", exc_info=True)

async def shutdown():
    """Shutdown function."""
    logger.info("Shutting down bot...")
    notify_events_task.stop()
    await close_db_pool()

if __name__ == "__main__":
    try:
        logger.info("Starting bot...")
        bot.run(DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        logger.warning("Shutting down bot.")
    finally:
        asyncio.run(shutdown())