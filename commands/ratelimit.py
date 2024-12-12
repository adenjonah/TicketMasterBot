import discord
from discord.ext import commands
import asyncio
import psycopg2
import requests
from config.config import DATABASE_URL, TICKETMASTER_API_KEY, DISCORD_CHANNEL_ID
from api.find_artist_and_ID import find_artist_and_id
from database.updating import mark_artist_notable
import aiohttp
from datetime import datetime, timezone

class RateLimit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ratelimit", help="Checks the current API rate limit status")
    async def ratelimit(self, ctx):
        """Checks the Ticketmaster API rate limit status and displays it."""
        url = f"https://app.ticketmaster.com/discovery/v2/events.json?apikey={TICKETMASTER_API_KEY}&size=1"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                # Retrieve response headers
                headers = response.headers
                
                # Extract rate limit details
                rate_limit = headers.get("Rate-Limit", "Unknown")
                rate_limit_available = headers.get("Rate-Limit-Available", "Unknown")
                rate_limit_reset = headers.get("Rate-Limit-Reset", "Unknown")
                
                # Convert the reset timestamp to a human-readable format if it's available
                reset_time = "Unknown"
                if rate_limit_reset.isdigit():
                    reset_time = datetime.fromtimestamp(int(rate_limit_reset) / 1000).strftime("%Y-%m-%d %H:%M:%S UTC")
                
                # Create and send an embedded message with rate limit info to Discord
                embed = discord.Embed(
                    # title="API Rate Limit Status",
                    title="Rate Limit Command Not Setup Yet",
                    color=discord.Color.blue()
                )
                await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(RateLimit(bot))