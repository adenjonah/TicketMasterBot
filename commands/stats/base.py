import discord
from discord.ext import commands
from datetime import datetime, timezone
import asyncio
from config import db_pool
from config.logging import logger
from .visualization import create_discord_file

class BaseStats(commands.Cog):
    """Base class for all statistics commands."""
    
    def __init__(self, bot):
        self.bot = bot
        self.day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    async def _send_status_message(self, ctx, message):
        """Send or edit a status message with consistent formatting."""
        try:
            return await ctx.send(f"🔍 {message}")
        except Exception as e:
            logger.error(f"Error sending status message: {e}")
            return None
    
    async def _update_status(self, message, new_content):
        """Update a status message with new content."""
        if message:
            try:
                await message.edit(content=f"🔍 {new_content}")
            except Exception as e:
                logger.error(f"Error updating status message: {e}")
    
    async def _handle_no_data(self, ctx, status_msg, region, days, stat_type):
        """Handle the case when no data is available."""
        content = f"No {stat_type} data available for {region or 'all regions'} in the past {days} days."
        if status_msg:
            await status_msg.edit(content=f"⚠️ {content}")
        else:
            await ctx.send(f"⚠️ {content}")
    
    async def _send_plot(self, ctx, fig, filename, caption, status_msg=None):
        """Send a plot to the channel and clean up status message."""
        try:
            file = create_discord_file(fig, filename)
            if status_msg:
                await status_msg.delete()
            await ctx.send(f"**{caption}**", file=file)
            return True
        except Exception as e:
            logger.error(f"Error sending plot: {e}", exc_info=True)
            if status_msg:
                await status_msg.edit(content=f"❌ Error creating visualization: {str(e)[:100]}...")
            return False
    
    async def _validate_days(self, days):
        """Validate and limit the days parameter."""
        return min(max(1, days), 90)  # Between 1 and 90 days
    
    async def _acquire_db_connection(self):
        """Get a database connection from the pool."""
        try:
            return await db_pool.db_pool.acquire()
        except Exception as e:
            logger.error(f"Error acquiring database connection: {e}", exc_info=True)
            raise
    
    async def _generate_embed_report(self, title, description, data_fields, color=discord.Color.blue()):
        """Generate a consistent embed report format."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        
        for field in data_fields:
            embed.add_field(
                name=field["name"],
                value=field["value"],
                inline=field.get("inline", False)
            )
        
        # Add timestamp
        embed.timestamp = datetime.now(timezone.utc)
        embed.set_footer(text="Generated")
        
        return embed
    
    async def _handle_stats_error(self, ctx, status_msg, error, stat_type):
        """Handle errors consistently across stat commands."""
        error_msg = f"Error generating {stat_type} stats: {str(error)[:100]}..."
        logger.error(f"{error_msg}\n{error}", exc_info=True)
        
        if status_msg:
            await status_msg.edit(content=f"❌ {error_msg}")
        else:
            await ctx.send(f"❌ {error_msg}")
    
    async def _get_region_string(self, region):
        """Format region string for display."""
        if not region:
            return "all regions"
        return region 