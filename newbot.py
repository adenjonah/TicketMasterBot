import discord
from discord.ext import tasks, commands
from config.db_pool import initialize_db_pool, close_db_pool
from tasks.notify_events import notify_events
from tasks.check_reminders import check_reminders
from handlers.reaction_handlers import handle_bell_reaction, handle_bell_reaction_remove, handle_x_reaction
from config.config import DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID, DISCORD_CHANNEL_ID_TWO, DATABASE_URL
from config.logging import logger
import asyncio
import os

# Update to include message_content intent (explicitly required for 2023+ API)
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.messages = True
intents.message_content = True  # Required for accessing message content
intents.reactions = True  # Required for reaction handlers

# Use basic Bot with command prefix
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await initialize_db_pool(DATABASE_URL)
    logger.info("Database pool initialized.")
    
    # Start tasks
    notify_events_task.start()
    check_reminders_task.start()

@bot.event
async def on_raw_reaction_add(payload):
    """Event handler for reactions added to messages"""
    # Handle based on emoji type
    emoji = str(payload.emoji)
    
    if emoji == "🔔":
        await handle_bell_reaction(bot, payload)
    elif emoji == "❌":
        await handle_x_reaction(bot, payload)

@bot.event
async def on_raw_reaction_remove(payload):
    """Event handler for reactions removed from messages"""
    # Check if the reaction is a bell emoji (🔔)
    if str(payload.emoji) != "🔔":
        return
    
    await handle_bell_reaction_remove(bot, payload)

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
    try:
        await check_reminders(bot, DISCORD_CHANNEL_ID, DISCORD_CHANNEL_ID_TWO)
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
        # Skip __init__.py and utils.py (they're not command cogs)
        if filename.endswith(".py") and filename not in ["__init__.py", "utils.py"]:
            try:
                await bot.load_extension(f"commands.{filename[:-3]}")
                logger.info(f"Loaded extension: commands.{filename[:-3]}")
            except Exception as e:
                logger.error(f"Failed to load extension {filename}: {e}", exc_info=True)
    await bot.start(DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Shutting down bot.")
    finally:
        asyncio.run(shutdown())