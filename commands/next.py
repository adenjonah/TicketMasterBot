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

            # Fetch each event's information and create a Discord embed
            for event in rows:
                event_id = event['eventid']
                event_name = event['name']
                artist_name = event['artist_name']
                
                # Format title based on whether artist name is available
                title = f"{event_name}" if artist_name is None else f"{artist_name} - {event_name}"
                
                # Get location details
                location = f"{event['city']}, {event['state']}"
                
                # Format dates in human-readable format for eastern time
                event_date_est = event['eventdate'].astimezone(self.eastern)
                event_date_str = event_date_est.strftime("%B %d, %Y at %I:%M %p EST")
                
                onsale_start_est = event['ticketonsalestart'].astimezone(self.eastern)
                onsale_start_str = onsale_start_est.strftime("%B %d, %Y at %I:%M %p EST")
                
                # Create embed
                embed = discord.Embed(
                    title=title,
                    url=event['url'],
                    color=discord.Color.blue()
                )
                
                # Add event details
                embed.add_field(name="📍 Location", value=location, inline=True)
                embed.add_field(name="📅 Event Date", value=event_date_str, inline=True)
                embed.add_field(name="🎫 Public Sale", value=onsale_start_str, inline=True)
                
                # Process presale information if available
                if event['presaledata']:
                    try:
                        presales = json.loads(event['presaledata'])
                        if presales:
                            presale_info = []
                            for presale in presales:
                                presale_start_utc = parser.parse(presale['startDateTime'])
                                presale_start_est = presale_start_utc.astimezone(self.eastern)
                                presale_start_str = presale_start_est.strftime("%b %d, %I:%M %p")
                                
                                presale_end_utc = parser.parse(presale['endDateTime'])
                                presale_end_est = presale_end_utc.astimezone(self.eastern)
                                presale_end_str = presale_end_est.strftime("%b %d, %I:%M %p")
                                
                                presale_info.append(f"**{presale['name']}**: {presale_start_str} - {presale_end_str}")
                            
                            embed.add_field(name="🔑 Presales", value="\n".join(presale_info), inline=False)
                    except Exception as e:
                        logger.error(f"Error processing presale data for event {event_id}: {e}", exc_info=True)
                
                await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(NextEvents(bot))