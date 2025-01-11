import discord
from discord.ext import commands
from datetime import datetime
from config import db_pool
import zoneinfo

class NextEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.eastern = zoneinfo.ZoneInfo("America/New_York")
        self.utc = zoneinfo.ZoneInfo("UTC")

    @commands.command(name="status", help="Displays the status of all servers.")
    async def status_command(self, ctx):
        query = '''
            SELECT ServerID, status, last_request, events_returned, new_events, error_messages
            FROM Server
        '''
        async with db_pool.db_pool.acquire() as conn:
            rows = await conn.fetch(query)

        if not rows:
            await ctx.send("No server status information found.")
            return

        total_running = sum(1 for row in rows if row['status'] == "Running")
        total_events_returned = sum(row['events_returned'] for row in rows)
        total_new_events = sum(row['new_events'] for row in rows)
        current_time = datetime.now(self.utc).astimezone(self.eastern).strftime("%I:%M %p EST")

        # Generate message content
        embed = discord.Embed(title="Server Status", color=discord.Color.blue())
        for row in rows:
            server_id = row['serverid'].capitalize()
            status = row['status']
            last_request = (
                row['last_request'].astimezone(self.eastern).strftime("%I:%M %p")
                if row['last_request'] else "N/A"
            )
            events_returned = row['events_returned']
            new_events = row['new_events']
            error_messages = row['error_messages'] or "None"

            embed.add_field(
                name=f"{server_id}: {status}",
                value=(
                    f"**Last request:** {last_request}\n"
                    f"**Events returned:** {events_returned}\n"
                    f"**New events:** {new_events}\n"
                    f"**Error messages:** {error_messages}"
                ),
                inline=False
            )

        # Add summary totals
        embed.add_field(
            name="Summary",
            value=(
                f"**Total Running:** {total_running}/{len(rows)}\n"
                f"**Last Updated:** {current_time}\n"
                f"**Total Events Returned:** {total_events_returned}\n"
                f"**Total New Events:** {total_new_events}"
            ),
            inline=False
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(NextEvents(bot))