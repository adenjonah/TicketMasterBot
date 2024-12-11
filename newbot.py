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

@tasks.loop(minutes=1)
async def notify_events_task():
    logger.info("Starting event notification process...")
    try:
        await notify_events(bot, DISCORD_CHANNEL_ID, notable_only=True)
        await notify_events(bot, DISCORD_CHANNEL_ID_TWO, notable_only=False)
    except Exception as e:
        logger.error(f"Error during event notification: {e}", exc_info=True)

async def shutdown():
    logger.info("Shutting down bot...")
    notify_events_task.stop()
    await close_db_pool()

async def main():
    logger.info("Starting bot...")
    for filename in os.listdir("./discord/commands"):
        if filename.endswith(".py") and filename != "__init__.py":
            await bot.load_extension(f"discord.commands.{filename[:-3]}")
    await bot.start(DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Shutting down bot.")
    finally:
        asyncio.run(shutdown())