import discord
from discord.ext import commands
import asyncio
import psycopg2
import requests
from config.config import DATABASE_URL, TICKETMASTER_API_KEY, DISCORD_CHANNEL_ID
from api.find_artist_and_ID import find_artist_and_id
from database.updating import mark_artist_notable

class AddArtist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="addartist", help="Marks artists as notable by using comma-separated keywords.")
    async def add_artist_command(self, ctx, *, keywords: str):
        keywords_list = [k.strip() for k in keywords.split(",")]
        successful = []
        failed = []

        for kw in keywords_list:
            artist_info = await find_artist_and_id(kw)
            artist_id, artist_name = artist_info[0], artist_info[1]
            print(artist_id, artist_name)
            if artist_info:
                await mark_artist_notable(artist_id, artist_name)
                successful.append(f"\"{artist_name}\" (ID: {artist_id})")
            else:
                failed.append(kw)

        if successful and not failed:
            await ctx.send(f"Artist{"s" if len(successful) > 1 else ""} {', '.join(successful)} marked as notable.")
        elif successful and failed:
            await ctx.send(f"Artist{"s" if len(successful) > 1 else ""} {', '.join(successful)} marked as notable, but keyword(s) {', '.join(failed)} not found.")
        else:
            await ctx.send(f"No artists found for keyword(s): {', '.join(failed)}.")

async def setup(bot):
    await bot.add_cog(AddArtist(bot))