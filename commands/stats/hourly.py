import discord
from discord.ext import commands
from .base import BaseStats
from database.analytics import get_region_activity_by_hour, get_notable_events_by_hour
from .visualization import create_hour_plot

class HourlyStats(BaseStats):
    """Commands for analyzing hourly statistics."""
    
    @commands.command(name="region_hours", help="Shows hourly activity for a region")
    async def region_hours_command(self, ctx, region: str = None, days: int = 30):
        """Display hourly event activity for a specific region or all regions."""
        days = await self._validate_days(days)
        region_str = await self._get_region_string(region)
        
        # Let user know we're working on it
        status_msg = await self._send_status_message(
            ctx, f"Fetching hourly stats for {region_str} over the past {days} days...")
        
        try:
            async with await self._acquire_db_connection() as conn:
                # Get the data
                data = await get_region_activity_by_hour(conn, region, days)
                
                if not data:
                    await self._handle_no_data(ctx, status_msg, region_str, days, "hourly activity")
                    return
                
                # Create the improved plot
                fig = create_hour_plot(
                    data,
                    f"Total New Events by Hour of Day (Past {days} Days)",
                    days,
                    region
                )
                
                # Send the plot
                await self._send_plot(
                    ctx, 
                    fig, 
                    "region_hours.png",
                    f"Hourly activity for {region_str} over the past {days} days:",
                    status_msg
                )
        except Exception as e:
            await self._handle_stats_error(ctx, status_msg, e, "hourly")
    
    @commands.command(name="notable_hours", help="Shows hourly activity for notable artist events")
    async def notable_hours_command(self, ctx, region: str = None, days: int = 30):
        """Display hourly notable event activity for a specific region or all regions."""
        days = await self._validate_days(days)
        region_str = await self._get_region_string(region)
        
        # Let user know we're working on it
        status_msg = await self._send_status_message(
            ctx, f"Fetching hourly notable events stats for {region_str} over the past {days} days...")
        
        try:
            async with await self._acquire_db_connection() as conn:
                # Get the data
                data = await get_notable_events_by_hour(conn, region, days)
                
                if not data:
                    await self._handle_no_data(ctx, status_msg, region_str, days, "notable events")
                    return
                
                # Create the improved plot
                fig = create_hour_plot(
                    data,
                    f"Total New Notable Events by Hour of Day (Past {days} Days)",
                    days,
                    region
                )
                
                # Send the plot
                await self._send_plot(
                    ctx, 
                    fig, 
                    "notable_hours.png",
                    f"Hourly notable artist activity for {region_str} over the past {days} days:",
                    status_msg
                )
        except Exception as e:
            await self._handle_stats_error(ctx, status_msg, e, "notable hourly")
            
    async def _generate_region_hours(self, ctx, region=None, days=30):
        """Helper function to generate region hours graph for all_stats_command."""
        region_str = await self._get_region_string(region)
        
        try:
            async with await self._acquire_db_connection() as conn:
                # Get the data
                data = await get_region_activity_by_hour(conn, region, days)
                
                if not data:
                    await ctx.send(f"⚠️ No hourly data available for {region_str} in the past {days} days.")
                    return False
                
                # Create the improved plot
                fig = create_hour_plot(
                    data,
                    f"Total New Events by Hour of Day (Past {days} Days)",
                    days,
                    region
                )
                
                # Send the plot
                await self._send_plot(
                    ctx, 
                    fig, 
                    "region_hours.png",
                    f"Hourly activity for {region_str} over the past {days} days:"
                )
                return True
        except Exception as e:
            await self._handle_stats_error(ctx, None, e, "hourly")
            return False
            
    async def _generate_notable_hours(self, ctx, region=None, days=30):
        """Helper function to generate notable hours graph for all_stats_command."""
        region_str = await self._get_region_string(region)
        
        try:
            async with await self._acquire_db_connection() as conn:
                # Get the data
                data = await get_notable_events_by_hour(conn, region, days)
                
                if not data:
                    await ctx.send(f"⚠️ No notable hourly data available for {region_str} in the past {days} days.")
                    return False
                
                # Create the improved plot
                fig = create_hour_plot(
                    data,
                    f"Total New Notable Events by Hour of Day (Past {days} Days)",
                    days,
                    region
                )
                
                # Send the plot
                await self._send_plot(
                    ctx, 
                    fig, 
                    "notable_hours.png",
                    f"Hourly notable artist activity for {region_str} over the past {days} days:"
                )
                return True
        except Exception as e:
            await self._handle_stats_error(ctx, None, e, "notable hourly")
            return False 