import discord
from discord.ext import commands
from config.config import DISCORD_CHANNEL_ID
from datetime import datetime
from config import db_pool
import zoneinfo
import json
from dateutil import parser
from config.logging import logger

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
                            e.presaleData, v.city, v.state, a.name AS artist_name
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
                event_name = event['name']
                artist_name = event['artist_name']
                
                # Format title based on whether artist name is available
                title = f"{event_name}" if artist_name is None else f"{artist_name} - {event_name}"
                
                # Format sale start time
                eastern_time = event['ticketonsalestart'].astimezone(self.eastern)
                
                # Manually format time to remove leading zero from hour and exclude seconds
                hour = int(eastern_time.strftime("%I"))  # convert to int to remove leading zero
                minute = eastern_time.strftime("%M")
                ampm = eastern_time.strftime("%p")
                date_str = eastern_time.strftime("%Y-%m-%d")
                time_str = f"{date_str} {hour}:{minute} {ampm} EST"
                
                # Add presale info if available
                presale_info = ""
                if event['presaledata']:
                    try:
                        presales = json.loads(event['presaledata'])
                        if presales:
                            # Sort presales by start datetime to find the earliest presale
                            presales.sort(key=lambda x: parser.parse(x['startDateTime']))
                            # Only use the earliest presale
                            earliest_presale = presales[0]
                            
                            presale_start_utc = parser.parse(earliest_presale['startDateTime'])
                            presale_start_est = presale_start_utc.astimezone(self.eastern)
                            
                            # Format presale time the same way
                            p_hour = int(presale_start_est.strftime("%I"))
                            p_minute = presale_start_est.strftime("%M")
                            p_ampm = presale_start_est.strftime("%p")
                            p_date_str = presale_start_est.strftime("%Y-%m-%d")
                            presale_time = f"{p_date_str} {p_hour}:{p_minute} {p_ampm} EST"
                            
                            presale_info = f" (Earliest presale: {earliest_presale['name']} - {presale_time})"
                    except Exception as e:
                        logger.error(f"Error processing presale data for event {event['eventID']}: {e}", exc_info=True)
                
                event_line = f"{idx}. [{title}]({event['url']}) sale starts {time_str}{presale_info}\n"
                message_lines.append(event_line)

            embed = discord.Embed(
                title="Next Events",
                description="".join(message_lines),
                color=discord.Color.blue()
            )
            
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(NextEvents(bot))