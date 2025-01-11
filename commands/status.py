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
        now_local = datetime.now(self.utc).astimezone(self.eastern)
        current_time = f"{now_local.hour}:{now_local.minute}"  # Drop leading zero/AM/PM

        header = f"{'S':<1} {'St':<2} {'Last':<5} {'Ev':>3} {'N':>3} {'E':<10}"
        lines = []

        for row in rows:
            s_char = row["serverid"].capitalize()[0] if row["serverid"] else "?"
            stat_emoji = "👍" if row["status"] == "Running" else "👎"

            if row["last_request"]:
                local_req = row["last_request"].astimezone(self.eastern)
                h = local_req.hour % 12 or 12
                m = local_req.minute
                last_str = f"{h}:{m}"
            else:
                last_str = "N/A"

            ev = row["events_returned"]
            n = row["new_events"]
            emsg = row["error_messages"] or "None"
            emsg = emsg[:10]  # Truncate to fit

            line = f"{s_char:<1} {stat_emoji:<2} {last_str:<5} {ev:>3} {n:>3} {emsg:<10}"
            lines.append(line)

        summary = (
            f"Tot:{total_running}/{len(rows)} {current_time} "
            f"Ev:{total_events_returned} N:{total_new_events}"
        )

        table = "```\n" + header + "\n" + "\n".join(lines) + "\n\n" + summary + "\n```"
        await ctx.send(table)

async def setup(bot):
    await bot.add_cog(Status(bot))