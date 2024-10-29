import discord
from discord.ext import commands
import logging
from collections import deque

# Set up logging
logging.basicConfig(level=logging.INFO, filename="event_log.log", filemode="a",
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("commandHandler")

# Set up intents
intents = discord.Intents.default()
intents.message_content = True

# Initialize bot with intents
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.command(name="logs", help="Displays the last few lines of the log file")
async def logs(ctx):
    """Sends the last few lines of the log file as an embedded code block in Discord."""
    try:
        # Read the last 20 lines of the log file
        with open("event_log.log", "r") as file:
            log_tail = ''.join(deque(file, maxlen=20))

        # Send as an embedded message with code block formatting
        embed = discord.Embed(
            title="Recent Log Entries",
            description=f"```\n{log_tail}```",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        logger.info("Sent log tail to Discord.")
    except Exception as e:
        await ctx.send("Unable to retrieve log file.")
        logger.error(f"Failed to send log file: {e}")
