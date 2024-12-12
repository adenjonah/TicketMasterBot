import discord
from discord.ext import commands
from config.config import DISCORD_CHANNEL_ID
from datetime import datetime
from config import db_pool
import zoneinfo

class NextEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.eastern = zoneinfo.ZoneInfo("America/New_York")
        self.utc = zoneinfo.ZoneInfo("UTC")

    @commands.command(name="next", help="Shows a list of the next notable events with ticket sales starting soon.")
    async def next_events_command(self, ctx, number: int = 5):
        number = min(number, 50)
        notable_only = ctx.channel.id == DISCORD_CHANNEL_ID

        query = '''
            SELECT DISTINCT e.eventID, e.name, e.ticketOnsaleStart, e.eventDate, e.url, 
                            v.city, v.state, a.name AS artist_name
            FROM Events e
            LEFT JOIN Venues v ON e.venueID = v.venueID
            LEFT JOIN Artists a ON e.artistID = a.artistID
            WHERE e.ticketOnsaleStart >= NOW()
        '''
        if notable_only:
            query += " AND a.notable = TRUE"
        query += " ORDER BY e.ticketOnsaleStart ASC LIMIT $1"

        async with db_pool.db_pool.acquire() as conn:
            rows = await conn.fetch(query, number)

        if not rows:
            message = ("No upcoming notable events with ticket sales starting soon."
                       if notable_only 
                       else "No upcoming events with ticket sales starting soon.")
            await ctx.send(message)
            return

        message_lines = []
        for idx, event in enumerate(rows, start=1):
            utc_time = event['ticketonsalestart'].replace(tzinfo=self.utc)
            eastern_time = utc_time.astimezone(self.eastern)

            # Manually format time to remove leading zero from hour and exclude seconds
            hour = int(eastern_time.strftime("%I"))  # convert to int to remove leading zero
            minute = eastern_time.strftime("%M")
            ampm = eastern_time.strftime("%p")
            date_str = eastern_time.strftime("%Y-%m-%d")
            time_str = f"{date_str} {hour}:{minute} {ampm} EST"

            event_line = f"{idx}. [{event['name']}]({event['url']}) sale starts {time_str}\n"
            message_lines.append(event_line)

        embed = discord.Embed(
            title="Next Events",
            description="".join(message_lines),
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(NextEvents(bot))