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
        # Map shortened server IDs to full names
        self.server_names = {
            'no': 'North',
            'ea': 'East',
            'so': 'South',
            'we': 'West',
            'eu': 'Europe',
            'co': 'Comedy',
            'th': 'Theater'
        }

    async def get_table_name(self, conn, table_base_name):
        """Find the actual table name with case sensitivity in mind."""
        tables = await conn.fetch("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
          AND table_name ILIKE $1
        """, table_base_name)
        
        if not tables:
            return None
            
        # Return the first matching table name
        return tables[0]['table_name']

    @commands.command(name="status", help="Displays the status of all servers.")
    async def status_command(self, ctx):
        async with db_pool.db_pool.acquire() as conn:
            # Get the actual server table name
            server_table = await self.get_table_name(conn, 'server')
            if not server_table:
                await ctx.send("Server table not found in the database.")
                return
            
            query = f"""
                SELECT ServerID, status, last_request, events_returned, new_events, error_messages
                FROM {server_table}
            """
            rows = await conn.fetch(query)

        if not rows:
            await ctx.send("No server status information found.")
            return

        total_running = sum(1 for row in rows if row["status"] == "Running")
        total_count = len(rows)
        all_good = (total_running == total_count)
        color = discord.Color.green() if all_good else discord.Color.red()

        total_events_returned = sum(row["events_returned"] or 0 for row in rows)
        total_new_events = sum(row["new_events"] or 0 for row in rows)
        now_local = datetime.now(self.utc).astimezone(self.eastern)
        current_time = now_local.strftime("%H:%M")

        header = "  Server   Status  Last  Events New"
        lines = []

        for row in rows:
            server_id = row["serverid"].lower() if row["serverid"] else ""
            server_name = self.server_names.get(server_id, server_id.capitalize())
            stat_emoji = "  👍  " if row["status"] == "Running" else "  👎  "

            if row["last_request"]:
                local_req = row["last_request"].astimezone(self.eastern)
                last_str = local_req.strftime("%H:%M")
            else:
                last_str = "N/A"

            events_returned = row["events_returned"] or 0
            new_events = row["new_events"] or 0
            ev = "  " + str(events_returned) + "  "
            n = "  " + str(new_events)

            lines.append(f"{server_name[:6]}   {stat_emoji} {last_str} {ev} {n}")
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