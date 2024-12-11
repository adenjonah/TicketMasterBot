import discord
from discord.ext import commands
import asyncio
import psycopg2
import requests
from config.config import DATABASE_URL, TICKETMASTER_API_KEY, DISCORD_CHANNEL_ID

class AddArtist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def find_artist_id(self, keyword):
        def blocking_request():
            url = f"https://app.ticketmaster.com/discovery/v2/attractions?apikey={TICKETMASTER_API_KEY}&keyword={keyword}&locale=*"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            attractions = data.get("_embedded", {}).get("attractions", [])
            if not attractions:
                return None
            return attractions[0]["id"]
        return await asyncio.to_thread(blocking_request)

    async def mark_artist_notable(self, artist_id):
        def blocking_db_op():
            conn = psycopg2.connect(DATABASE_URL)
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE Artists
                        SET notable = TRUE
                        WHERE artistID = %s
                        """,
                        (artist_id,)
                    )
                conn.commit()
            finally:
                conn.close()
        return await asyncio.to_thread(blocking_db_op)

    @commands.command(name="addartist", help="Marks artists as notable by using comma-separated keywords.")
    async def add_artist_command(self, ctx, *, keywords: str):
        keywords_list = [k.strip() for k in keywords.split(",")]
        successful = []
        failed = []

        for kw in keywords_list:
            artist_id = await self.find_artist_id(kw)
            if artist_id:
                await self.mark_artist_notable(artist_id)
                successful.append(artist_id)
            else:
                failed.append(kw)

        if successful and not failed:
            await ctx.send(f"Artist ID(s) {', '.join(successful)} marked as notable.")
        elif successful and failed:
            await ctx.send(f"Artist ID(s) {', '.join(successful)} marked as notable, but keyword(s) {', '.join(failed)} not found.")
        else:
            await ctx.send(f"No artists found for keyword(s): {', '.join(failed)}.")

async def setup(bot):
    await bot.add_cog(AddArtist(bot))