import discord
from discord.ext import commands
from datetime import datetime
from config import db_pool
import zoneinfo

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.eastern = zoneinfo.ZoneInfo("America/New_York")
        self.utc = zoneinfo.ZoneInfo("UTC")

    @commands.command(name="status", help="Displays the status of all servers.")
    async def status_command(self, ctx):
        query = """
            SELECT ServerID, status, last_request, events_returned, new_events, error_messages
            FROM Server
        """
        async with db_pool.db_pool.acquire() as conn:
            rows = await conn.fetch(query)

        if not rows:
            await ctx.send("No server status information found.")
            return

        total_running = sum(1 for row in rows if row["status"] == "Running")
        total_events_returned = sum(row["events_returned"] for row in rows)
        total_new_events = sum(row["new_events"] for row in rows)
        current_time = datetime.now(self.utc).astimezone(self.eastern).strftime("%I:%M %p")

        # Build table header
        header = (
            f"{'Server':<10} | {'Status':<7} | {'Last Req':<8} | "
            f"{'Events':<7} | {'New':<4} | {'Errors':<20}"
        )

        # Build table rows
        table_lines = []
        for row in rows:
            server_id = row["serverid"].capitalize()
            status = row["status"]
            last_request = (
                row["last_request"].astimezone(self.eastern).strftime("%I:%M%p")
                if row["last_request"]
                else "N/A"
            )
            events_returned = row["events_returned"]
            new_events = row["new_events"]
            error_messages = row["error_messages"] or "None"

            line = (
                f"{server_id:<10} | {status:<7} | {last_request:<8} | "
                f"{str(events_returned):<7} | {str(new_events):<4} | {error_messages:<20}"
            )
            table_lines.append(line)

        # Build summary line
        summary = (
            f"Total: {total_running}/{len(rows)} Running | {current_time} | "
            f"{total_events_returned} | {total_new_events}"
        )

        # Send as a code block
        message = "```\n" + header + "\n" + "\n".join(table_lines) + "\n\n" + summary + "\n```"
        await ctx.send(message)

async def setup(bot):
    await bot.add_cog(Status(bot))