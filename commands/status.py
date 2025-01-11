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
        total_count = len(rows)
        all_good = (total_running == total_count)
        color = discord.Color.green() if all_good else discord.Color.red()

        total_events_returned = sum(row["events_returned"] for row in rows)
        total_new_events = sum(row["new_events"] for row in rows)
        now_local = datetime.now(self.utc).astimezone(self.eastern)
        current_time = now_local.strftime("%H:%M")

        header = "  St Last Ev N"
        lines = []

        for row in rows:
            s_char = row["serverid"].capitalize()[0] if row["serverid"] else "?"
            stat_emoji = "👍" if row["status"] == "Running" else "👎"

            if row["last_request"]:
                local_req = row["last_request"].astimezone(self.eastern)
                last_str = local_req.strftime("%H:%M")
            else:
                last_str = "N/A"

            ev = str(row["events_returned"])
            n = str(row["new_events"])

            lines.append(f"{s_char} {stat_emoji} {last_str} {ev} {n}")
            emsg = row["error_messages"]
            if emsg and emsg.lower() != "none":
                lines.append(f"  E: {emsg}")

        summary = (
            f"Total Running: {total_running}/{total_count}\n"
            f"Last Updated: {current_time}\n"
            f"Total Events Returned: {total_events_returned}\n"
            f"New Events Added: {total_new_events}"
        )

        table = "```\n" + header + "\n" + "\n".join(lines) + "\n\n" + summary + "\n```"

        embed = discord.Embed(
            title="Server Statuses",
            description=table,
            color=color
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Status(bot))