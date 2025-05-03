import discord
from discord.ext import commands
from .base import BaseStats
from database.analytics import get_region_activity_by_day, get_notable_events_by_day
from .visualization import create_day_plot

class DailyStats(BaseStats):
    """Commands for analyzing daily statistics."""
    
    @commands.command(name="region_days", help="Shows daily activity for a region")
    async def region_days_command(self, ctx, region: str = None, days: int = 30):
        """Display daily event activity for a specific region or all regions."""
        days = await self._validate_days(days)
        region_str = await self._get_region_string(region)
        
        # Let user know we're working on it
        status_msg = await self._send_status_message(
            ctx, f"Fetching daily stats for {region_str} over the past {days} days...")
        
        try:
            async with await self._acquire_db_connection() as conn:
                # Get the data
                data = await get_region_activity_by_day(conn, region, days)
                
                if not data:
                    await self._handle_no_data(ctx, status_msg, region_str, days, "daily activity")
                    return
                
                # Create the improved plot
                fig = create_day_plot(
                    data,
                    f"Total New Events by Day of Week (Past {days} Days)",
                    days,
                    self.day_names,
                    region
                )
                
                # Send the plot
                await self._send_plot(
                    ctx, 
                    fig, 
                    "region_days.png",
                    f"Daily activity for {region_str} over the past {days} days:",
                    status_msg
                )
        except Exception as e:
            await self._handle_stats_error(ctx, status_msg, e, "daily")
    
    @commands.command(name="notable_days", help="Shows daily activity for notable artist events")
    async def notable_days_command(self, ctx, region: str = None, days: int = 30):
        """Display daily notable event activity for a specific region or all regions."""
        days = await self._validate_days(days)
        region_str = await self._get_region_string(region)
        
        # Let user know we're working on it
        status_msg = await self._send_status_message(
            ctx, f"Fetching daily notable events stats for {region_str} over the past {days} days...")
        
        try:
            async with await self._acquire_db_connection() as conn:
                # Get the data
                data = await get_notable_events_by_day(conn, region, days)
                
                if not data:
                    await self._handle_no_data(ctx, status_msg, region_str, days, "notable daily events")
                    return
                
                # Create the improved plot
                fig = create_day_plot(
                    data,
                    f"Total New Notable Events by Day of Week (Past {days} Days)",
                    days,
                    self.day_names,
                    region
                )
                
                # Send the plot
                await self._send_plot(
                    ctx, 
                    fig, 
                    "notable_days.png",
                    f"Daily notable artist activity for {region_str} over the past {days} days:",
                    status_msg
                )
        except Exception as e:
            await self._handle_stats_error(ctx, status_msg, e, "notable daily")
            
    async def _generate_region_days(self, ctx, region=None, days=30):
        """Helper function to generate region days graph for all_stats_command."""
        region_str = await self._get_region_string(region)
        
        try:
            async with await self._acquire_db_connection() as conn:
                # Get the data
                data = await get_region_activity_by_day(conn, region, days)
                
                if not data:
                    await ctx.send(f"⚠️ No daily data available for {region_str} in the past {days} days.")
                    return False
                
                # Create the improved plot
                fig = create_day_plot(
                    data,
                    f"Total New Events by Day of Week (Past {days} Days)",
                    days,
                    self.day_names,
                    region
                )
                
                # Send the plot
                await self._send_plot(
                    ctx, 
                    fig, 
                    "region_days.png",
                    f"Daily activity for {region_str} over the past {days} days:"
                )
                return True
        except Exception as e:
            await self._handle_stats_error(ctx, None, e, "daily")
            return False
            
    async def _generate_notable_days(self, ctx, region=None, days=30):
        """Helper function to generate notable days graph for all_stats_command."""
        region_str = await self._get_region_string(region)
        
        try:
            async with await self._acquire_db_connection() as conn:
                # Get the data
                data = await get_notable_events_by_day(conn, region, days)
                
                if not data:
                    await ctx.send(f"⚠️ No notable daily data available for {region_str} in the past {days} days.")
                    return False
                
                # Create the improved plot
                fig = create_day_plot(
                    data,
                    f"Total New Notable Events by Day of Week (Past {days} Days)",
                    days,
                    self.day_names,
                    region
                )
                
                # Send the plot
                await self._send_plot(
                    ctx, 
                    fig, 
                    "notable_days.png",
                    f"Daily notable artist activity for {region_str} over the past {days} days:"
                )
                return True
        except Exception as e:
            await self._handle_stats_error(ctx, None, e, "notable daily")
            return False 