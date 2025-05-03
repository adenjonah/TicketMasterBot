import discord
from discord.ext import commands
from datetime import datetime, timezone
from .base import BaseStats
from database.analytics import get_hourly_heatmap_data, get_region_trending_data
from .visualization import create_heatmap

class RegionalStats(BaseStats):
    """Commands for analyzing regional statistics."""
    
    @commands.command(name="region_heatmap", help="Shows a heatmap of regional activity")
    async def region_heatmap_command(self, ctx, days: int = 30):
        """Display a heatmap of regional activity by hour."""
        days = await self._validate_days(days)
        
        # Let user know we're working on it
        status_msg = await self._send_status_message(
            ctx, f"Generating activity heatmap for all regions over the past {days} days...")
        
        try:
            async with await self._acquire_db_connection() as conn:
                # Get the data
                data = await get_hourly_heatmap_data(conn, days)
                
                if not data:
                    await self._handle_no_data(ctx, status_msg, "all regions", days, "heatmap")
                    return
                
                # Reshape data for heatmap
                regions = sorted(list(set(item['serverid'] for item in data)))
                hours = list(range(24))
                
                # Create the improved heatmap
                fig = create_heatmap(
                    data,
                    regions,
                    hours,
                    f"Event Activity Heatmap by Region and Hour (Past {days} Days)",
                    days
                )
                
                # Send the plot
                await self._send_plot(
                    ctx, 
                    fig, 
                    "region_heatmap.png",
                    f"Regional activity heatmap for the past {days} days:",
                    status_msg
                )
        except Exception as e:
            await self._handle_stats_error(ctx, status_msg, e, "heatmap")
    
    @commands.command(name="region_trends", help="Shows trending activity for regions")
    async def region_trends_command(self, ctx, days: int = 14):
        """Display trending activity data comparing recent vs past periods."""
        days = await self._validate_days(days)
        
        # Let user know we're working on it
        status_msg = await self._send_status_message(
            ctx, f"Analyzing regional trends over the past {days} days...")
        
        try:
            async with await self._acquire_db_connection() as conn:
                # Get the data
                trend_data = await get_region_trending_data(conn, None, days)
                
                if not trend_data:
                    await self._handle_no_data(ctx, status_msg, "all regions", days, "trend")
                    return
                
                # Create an embed to display the trend data
                data_fields = []
                
                # Add trend data for each region
                for region, data in trend_data.items():
                    # Format the trend data
                    recent_events = f"{data['recent_avg_events']:.1f}"
                    past_events = f"{data['past_avg_events']:.1f}"
                    events_change = f"{data['events_percent_change']:.1f}%"
                    
                    recent_new = f"{data['recent_avg_new_events']:.1f}"
                    past_new = f"{data['past_avg_new_events']:.1f}"
                    new_change = f"{data['new_events_percent_change']:.1f}%"
                    
                    # Add trending indicator
                    indicator = "📈" if data['is_trending_up'] else "📉"
                    
                    # Calculate emoji based on trend strength
                    if data['new_events_percent_change'] > 50:
                        emoji = "🔥" # Hot/major increase
                    elif data['new_events_percent_change'] > 20:
                        emoji = "📈" # Significant increase
                    elif data['new_events_percent_change'] < -50:
                        emoji = "❄️" # Cold/major decrease
                    elif data['new_events_percent_change'] < -20:
                        emoji = "📉" # Significant decrease
                    else:
                        emoji = "➖" # Relatively stable
                    
                    data_fields.append({
                        "name": f"{region} {indicator} {emoji}",
                        "value": (
                            f"**All Events:** {recent_events}/day (was {past_events}, {events_change})\n"
                            f"**New Events:** {recent_new}/day (was {past_new}, {new_change})"
                        ),
                        "inline": False
                    })
                
                # Generate the embed
                embed = await self._generate_embed_report(
                    title=f"Regional Activity Trends (Past {days} Days)",
                    description=f"Comparing recent {days//2} days vs previous {days//2} days",
                    data_fields=data_fields,
                    color=discord.Color.blue()
                )
                
                # Send the embed
                if status_msg:
                    await status_msg.delete()
                await ctx.send(embed=embed)
        except Exception as e:
            await self._handle_stats_error(ctx, status_msg, e, "trends")
    
    async def _generate_region_heatmap(self, ctx, days=30):
        """Helper function to generate region heatmap for all_stats_command."""
        try:
            async with await self._acquire_db_connection() as conn:
                # Get the data
                data = await get_hourly_heatmap_data(conn, days)
                
                if not data:
                    await ctx.send(f"⚠️ No data available for heatmap in the past {days} days.")
                    return False
                
                # Reshape data for heatmap
                regions = sorted(list(set(item['serverid'] for item in data)))
                hours = list(range(24))
                
                # Create the improved heatmap
                fig = create_heatmap(
                    data,
                    regions,
                    hours,
                    f"Event Activity Heatmap by Region and Hour (Past {days} Days)",
                    days
                )
                
                # Send the plot
                await self._send_plot(
                    ctx, 
                    fig, 
                    "region_heatmap.png",
                    f"Regional activity heatmap for the past {days} days:"
                )
                return True
        except Exception as e:
            await self._handle_stats_error(ctx, None, e, "heatmap")
            return False
    
    async def _generate_region_trends(self, ctx, days=14):
        """Helper function to generate region trends for all_stats_command."""
        try:
            async with await self._acquire_db_connection() as conn:
                # Get the data
                trend_data = await get_region_trending_data(conn, None, days)
                
                if not trend_data:
                    await ctx.send(f"⚠️ No trend data available for the past {days} days.")
                    return False
                
                # Create an embed to display the trend data
                data_fields = []
                
                # Add trend data for each region
                for region, data in trend_data.items():
                    # Format the trend data
                    recent_events = f"{data['recent_avg_events']:.1f}"
                    past_events = f"{data['past_avg_events']:.1f}"
                    events_change = f"{data['events_percent_change']:.1f}%"
                    
                    recent_new = f"{data['recent_avg_new_events']:.1f}"
                    past_new = f"{data['past_avg_new_events']:.1f}"
                    new_change = f"{data['new_events_percent_change']:.1f}%"
                    
                    # Add trending indicator
                    indicator = "📈" if data['is_trending_up'] else "📉"
                    
                    # Calculate emoji based on trend strength
                    if data['new_events_percent_change'] > 50:
                        emoji = "🔥" # Hot/major increase
                    elif data['new_events_percent_change'] > 20:
                        emoji = "📈" # Significant increase
                    elif data['new_events_percent_change'] < -50:
                        emoji = "❄️" # Cold/major decrease
                    elif data['new_events_percent_change'] < -20:
                        emoji = "📉" # Significant decrease
                    else:
                        emoji = "➖" # Relatively stable
                    
                    data_fields.append({
                        "name": f"{region} {indicator} {emoji}",
                        "value": (
                            f"**All Events:** {recent_events}/day (was {past_events}, {events_change})\n"
                            f"**New Events:** {recent_new}/day (was {past_new}, {new_change})"
                        ),
                        "inline": False
                    })
                
                # Generate the embed
                embed = await self._generate_embed_report(
                    title=f"Regional Activity Trends (Past {days} Days)",
                    description=f"Comparing recent {days//2} days vs previous {days//2} days",
                    data_fields=data_fields,
                    color=discord.Color.blue()
                )
                
                # Send the embed
                await ctx.send(embed=embed)
                return True
        except Exception as e:
            await self._handle_stats_error(ctx, None, e, "trends")
            return False 