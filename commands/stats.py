import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
import numpy as np
from config import db_pool
from database.analytics import (
    get_region_activity_by_hour,
    get_region_activity_by_day,
    get_region_trending_data,
    get_hourly_heatmap_data,
    get_notable_events_by_hour,
    get_notable_events_by_day,
    compare_notable_vs_all_events
)
from config.logging import logger

class RegionStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="stats", help="Generates all stats and graphs at once")
    async def all_stats_command(self, ctx, region: str = None, days: int = 30):
        """Generate and send all statistics graphs for the specified region or all regions."""
        days = min(days, 90)  # Limit to 90 days max for performance
        
        # Initial message to let user know we're working on it
        msg = await ctx.send(f"🔍 Generating all stats for {region or 'all regions'} over the past {days} days...\nThis might take a minute, please wait.")
        
        try:
            # Create a list to track successful and failed stats
            successful = []
            failed = []
            
            # 1. Region Hours
            try:
                await self._generate_region_hours(ctx, region, days)
                successful.append("Region Hours")
            except Exception as e:
                logger.error(f"Error generating region hours: {e}", exc_info=True)
                failed.append("Region Hours")
                
            # 2. Region Days
            try:
                await self._generate_region_days(ctx, region, days)
                successful.append("Region Days")
            except Exception as e:
                logger.error(f"Error generating region days: {e}", exc_info=True)
                failed.append("Region Days")
                
            # 3. Region Heatmap
            try:
                await self._generate_region_heatmap(ctx, days)
                successful.append("Region Heatmap")
            except Exception as e:
                logger.error(f"Error generating region heatmap: {e}", exc_info=True)
                failed.append("Region Heatmap")
                
            # 4. Region Trends
            try:
                await self._generate_region_trends(ctx, days)
                successful.append("Region Trends")
            except Exception as e:
                logger.error(f"Error generating region trends: {e}", exc_info=True)
                failed.append("Region Trends")
                
            # 5. Notable Hours
            try:
                await self._generate_notable_hours(ctx, region, days)
                successful.append("Notable Hours")
            except Exception as e:
                logger.error(f"Error generating notable hours: {e}", exc_info=True)
                failed.append("Notable Hours")
                
            # 6. Notable Days
            try:
                await self._generate_notable_days(ctx, region, days)
                successful.append("Notable Days")
            except Exception as e:
                logger.error(f"Error generating notable days: {e}", exc_info=True)
                failed.append("Notable Days")
                
            # 7. Notable Comparison
            try:
                await self._generate_notable_comparison(ctx, region, days)
                successful.append("Notable Comparison")
            except Exception as e:
                logger.error(f"Error generating notable comparison: {e}", exc_info=True)
                failed.append("Notable Comparison")
            
            # Update the initial message with completion status
            status = "✅ All stats generated successfully!" if not failed else "⚠️ Some stats couldn't be generated."
            generated = f"Generated: {', '.join(successful)}" if successful else "No stats could be generated."
            failed_msg = f"Failed: {', '.join(failed)}" if failed else ""
            
            await msg.edit(content=f"{status}\n{generated}\n{failed_msg}")
            
        except Exception as e:
            logger.error(f"Error in all_stats_command: {e}", exc_info=True)
            await msg.edit(content=f"❌ An error occurred while generating stats: {str(e)[:100]}...")

    @commands.command(name="region_hours", help="Shows hourly activity for a region")
    async def region_hours_command(self, ctx, region: str = None, days: int = 30):
        """Display hourly event activity for a specific region or all regions."""
        days = min(days, 90)  # Limit to 90 days max for performance
        
        # Let user know we're working on it
        msg = await ctx.send(f"Fetching hourly stats for {region or 'all regions'} over the past {days} days...")
        
        try:
            async with db_pool.db_pool.acquire() as conn:
                # Get the data
                data = await get_region_activity_by_hour(conn, region, days)
                
                if not data:
                    await msg.edit(content=f"No data available for {region or 'all regions'} in the past {days} days.")
                    return
                
                # Create a plot
                fig, ax = plt.subplots(figsize=(10, 6))
                
                # Group by region
                regions = set(item['serverid'] for item in data)
                for r in regions:
                    region_data = [item for item in data if item['serverid'] == r]
                    hours = [item['hour_of_day'] for item in region_data]
                    new_events = [item['total_new_events'] for item in region_data]
                    ax.plot(hours, new_events, 'o-', label=r)
                
                # Format the plot
                ax.set_title(f"Total New Events by Hour of Day (Past {days} Days)")
                ax.set_xlabel("Hour of Day (UTC)")
                ax.set_ylabel("Total New Events")
                ax.set_xticks(range(0, 24))
                ax.grid(True, linestyle='--', alpha=0.7)
                ax.legend()
                
                # Save the plot to a buffer
                buf = io.BytesIO()
                plt.tight_layout()
                fig.savefig(buf, format='png')
                buf.seek(0)
                
                # Send the plot
                file = discord.File(buf, filename="region_hours.png")
                await msg.delete()
                await ctx.send(
                    f"Hourly activity for {region or 'all regions'} over the past {days} days:", 
                    file=file
                )
                plt.close(fig)
        except Exception as e:
            logger.error(f"Error in region_hours_command: {e}", exc_info=True)
            await msg.edit(content=f"An error occurred while generating hourly stats.")

    @commands.command(name="region_days", help="Shows daily activity for a region")
    async def region_days_command(self, ctx, region: str = None, days: int = 30):
        """Display daily event activity for a specific region or all regions."""
        days = min(days, 90)  # Limit to 90 days max for performance
        
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        # Let user know we're working on it
        msg = await ctx.send(f"Fetching daily stats for {region or 'all regions'} over the past {days} days...")
        
        try:
            async with db_pool.db_pool.acquire() as conn:
                # Get the data
                data = await get_region_activity_by_day(conn, region, days)
                
                if not data:
                    await msg.edit(content=f"No data available for {region or 'all regions'} in the past {days} days.")
                    return
                
                # Create a plot
                fig, ax = plt.subplots(figsize=(10, 6))
                
                # Group by region
                regions = set(item['serverid'] for item in data)
                for r in regions:
                    region_data = [item for item in data if item['serverid'] == r]
                    # Sort by day of week (0 = Monday, 6 = Sunday)
                    region_data.sort(key=lambda x: x['day_of_week'])
                    days_of_week = [item['day_of_week'] for item in region_data]
                    new_events = [item['total_new_events'] for item in region_data]
                    
                    # Convert day numbers to day names for x-axis
                    day_labels = [day_names[d] for d in days_of_week]
                    
                    ax.plot(day_labels, new_events, 'o-', label=r)
                
                # Format the plot
                ax.set_title(f"Total New Events by Day of Week (Past {days} Days)")
                ax.set_xlabel("Day of Week")
                ax.set_ylabel("Total New Events")
                ax.grid(True, linestyle='--', alpha=0.7)
                ax.legend()
                
                # Save the plot to a buffer
                buf = io.BytesIO()
                plt.tight_layout()
                fig.savefig(buf, format='png')
                buf.seek(0)
                
                # Send the plot
                file = discord.File(buf, filename="region_days.png")
                await msg.delete()
                await ctx.send(
                    f"Daily activity for {region or 'all regions'} over the past {days} days:", 
                    file=file
                )
                plt.close(fig)
        except Exception as e:
            logger.error(f"Error in region_days_command: {e}", exc_info=True)
            await msg.edit(content=f"An error occurred while generating daily stats.")

    @commands.command(name="region_heatmap", help="Shows a heatmap of regional activity")
    async def region_heatmap_command(self, ctx, days: int = 30):
        """Display a heatmap of regional activity by hour."""
        days = min(days, 90)  # Limit to 90 days max for performance
        
        # Let user know we're working on it
        msg = await ctx.send(f"Generating activity heatmap for all regions over the past {days} days...")
        
        try:
            async with db_pool.db_pool.acquire() as conn:
                # Get the data
                data = await get_hourly_heatmap_data(conn, days)
                
                if not data:
                    await msg.edit(content=f"No data available for heatmap in the past {days} days.")
                    return
                
                # Reshape data for heatmap
                regions = sorted(list(set(item['serverid'] for item in data)))
                hours = list(range(24))
                
                # Create a matrix for the heatmap
                heatmap_data = np.zeros((len(regions), 24))
                
                # Fill in the data
                for item in data:
                    region_idx = regions.index(item['serverid'])
                    hour = item['hour_of_day']
                    total_events = item['total_new_events']
                    heatmap_data[region_idx, hour] = total_events
                
                # Create a plot
                fig, ax = plt.subplots(figsize=(12, 8))
                
                # Create the heatmap
                im = ax.imshow(heatmap_data, cmap='viridis')
                
                # Add colorbar
                cbar = ax.figure.colorbar(im, ax=ax)
                cbar.ax.set_ylabel("Total New Events", rotation=-90, va="bottom")
                
                # Set ticks and labels
                ax.set_xticks(np.arange(24))
                ax.set_xticklabels(hours)
                ax.set_yticks(np.arange(len(regions)))
                ax.set_yticklabels(regions)
                
                # Label the chart
                ax.set_title(f"Total New Event Activity Heatmap by Region and Hour (Past {days} Days)")
                ax.set_xlabel("Hour of Day (UTC)")
                ax.set_ylabel("Region")
                
                # Loop over data dimensions and create text annotations
                for i in range(len(regions)):
                    for j in range(24):
                        text = ax.text(j, i, f"{heatmap_data[i, j]:.1f}",
                                    ha="center", va="center", color="w" if heatmap_data[i, j] > np.max(heatmap_data)/2 else "black")
                
                # Save the plot to a buffer
                buf = io.BytesIO()
                plt.tight_layout()
                fig.savefig(buf, format='png')
                buf.seek(0)
                
                # Send the plot
                file = discord.File(buf, filename="region_heatmap.png")
                await msg.delete()
                await ctx.send(
                    f"Regional activity heatmap for the past {days} days:", 
                    file=file
                )
                plt.close(fig)
        except Exception as e:
            logger.error(f"Error in region_heatmap_command: {e}", exc_info=True)
            await msg.edit(content=f"An error occurred while generating the heatmap.")

    @commands.command(name="region_trends", help="Shows trending activity for regions")
    async def region_trends_command(self, ctx, days: int = 14):
        """Display trending activity data comparing recent vs past periods."""
        days = min(days, 90)  # Limit to 90 days max for performance
        
        # Let user know we're working on it
        msg = await ctx.send(f"Analyzing regional trends over the past {days} days...")
        
        try:
            async with db_pool.db_pool.acquire() as conn:
                # Get the data
                trend_data = await get_region_trending_data(conn, None, days)
                
                if not trend_data:
                    await msg.edit(content=f"No trend data available for the past {days} days.")
                    return
                
                # Create an embed to display the trend data
                embed = discord.Embed(
                    title=f"Regional Activity Trends (Past {days} Days)",
                    description=f"Comparing recent {days//2} days vs previous {days//2} days",
                    color=discord.Color.blue()
                )
                
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
                    
                    # Add field for this region
                    embed.add_field(
                        name=f"{region} {indicator}",
                        value=(
                            f"**All Events:** {recent_events} (was {past_events}, {events_change})\n"
                            f"**New Events:** {recent_new} (was {past_new}, {new_change})"
                        ),
                        inline=False
                    )
                
                # Add timestamp
                embed.timestamp = datetime.now(timezone.utc)
                
                # Send the embed
                await msg.delete()
                await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in region_trends_command: {e}", exc_info=True)
            await msg.edit(content=f"An error occurred while generating trend data.")

    @commands.command(name="notable_hours", help="Shows hourly activity for notable artist events")
    async def notable_hours_command(self, ctx, region: str = None, days: int = 30):
        """Display hourly notable event activity for a specific region or all regions."""
        days = min(days, 90)  # Limit to 90 days max for performance
        
        # Let user know we're working on it
        msg = await ctx.send(f"Fetching hourly notable events stats for {region or 'all regions'} over the past {days} days...")
        
        try:
            async with db_pool.db_pool.acquire() as conn:
                # Get the data
                data = await get_notable_events_by_hour(conn, region, days)
                
                if not data:
                    await msg.edit(content=f"No notable events data available for {region or 'all regions'} in the past {days} days.")
                    return
                
                # Create a plot
                fig, ax = plt.subplots(figsize=(10, 6))
                
                # Group by region
                regions = set(item['region'] for item in data)
                for r in regions:
                    region_data = [item for item in data if item['region'] == r]
                    hours = [item['hour_of_day'] for item in region_data]
                    new_events = [item['total_new_events'] for item in region_data]
                    ax.plot(hours, new_events, 'o-', label=r)
                
                # Format the plot
                ax.set_title(f"Total New Notable Events by Hour of Day (Past {days} Days)")
                ax.set_xlabel("Hour of Day (UTC)")
                ax.set_ylabel("Total New Notable Events")
                ax.set_xticks(range(0, 24))
                ax.grid(True, linestyle='--', alpha=0.7)
                ax.legend()
                
                # Save the plot to a buffer
                buf = io.BytesIO()
                plt.tight_layout()
                fig.savefig(buf, format='png')
                buf.seek(0)
                
                # Send the plot
                file = discord.File(buf, filename="notable_hours.png")
                await msg.delete()
                await ctx.send(
                    f"Hourly notable artist activity for {region or 'all regions'} over the past {days} days:", 
                    file=file
                )
                plt.close(fig)
        except Exception as e:
            logger.error(f"Error in notable_hours_command: {e}", exc_info=True)
            await msg.edit(content=f"An error occurred while generating notable hourly stats.")

    @commands.command(name="notable_days", help="Shows daily activity for notable artist events")
    async def notable_days_command(self, ctx, region: str = None, days: int = 30):
        """Display daily notable event activity for a specific region or all regions."""
        days = min(days, 90)  # Limit to 90 days max for performance
        
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        # Let user know we're working on it
        msg = await ctx.send(f"Fetching daily notable events stats for {region or 'all regions'} over the past {days} days...")
        
        try:
            async with db_pool.db_pool.acquire() as conn:
                # Get the data
                data = await get_notable_events_by_day(conn, region, days)
                
                if not data:
                    await msg.edit(content=f"No notable events data available for {region or 'all regions'} in the past {days} days.")
                    return
                
                # Create a plot
                fig, ax = plt.subplots(figsize=(10, 6))
                
                # Group by region
                regions = set(item['region'] for item in data)
                for r in regions:
                    region_data = [item for item in data if item['region'] == r]
                    # Sort by day of week (0 = Monday, 6 = Sunday)
                    region_data.sort(key=lambda x: x['day_of_week'])
                    days_of_week = [item['day_of_week'] for item in region_data]
                    new_events = [item['total_new_events'] for item in region_data]
                    
                    # Convert day numbers to day names for x-axis
                    day_labels = [day_names[d] for d in days_of_week]
                    
                    ax.plot(day_labels, new_events, 'o-', label=r)
                
                # Format the plot
                ax.set_title(f"Total New Notable Events by Day of Week (Past {days} Days)")
                ax.set_xlabel("Day of Week")
                ax.set_ylabel("Total New Notable Events")
                ax.grid(True, linestyle='--', alpha=0.7)
                ax.legend()
                
                # Save the plot to a buffer
                buf = io.BytesIO()
                plt.tight_layout()
                fig.savefig(buf, format='png')
                buf.seek(0)
                
                # Send the plot
                file = discord.File(buf, filename="notable_days.png")
                await msg.delete()
                await ctx.send(
                    f"Daily notable artist activity for {region or 'all regions'} over the past {days} days:", 
                    file=file
                )
                plt.close(fig)
        except Exception as e:
            logger.error(f"Error in notable_days_command: {e}", exc_info=True)
            await msg.edit(content=f"An error occurred while generating notable daily stats.")

    @commands.command(name="notable_comparison", help="Shows comparison between notable and all events")
    async def notable_comparison_command(self, ctx, region: str = None, days: int = 30):
        """Display comparison between notable and all events for a specific region or all regions."""
        days = min(days, 90)  # Limit to 90 days max for performance
        
        # Let user know we're working on it
        msg = await ctx.send(f"Analyzing notable vs all events for {region or 'all regions'} over the past {days} days...")
        
        try:
            async with db_pool.db_pool.acquire() as conn:
                # Get the data
                comparison_data = await compare_notable_vs_all_events(conn, region, days)
                
                if not comparison_data:
                    await msg.edit(content=f"No comparison data available for {region or 'all regions'} in the past {days} days.")
                    return
                
                # Create an embed to display the comparison data
                embed = discord.Embed(
                    title=f"Notable vs All Events Comparison (Past {days} Days)",
                    description=f"Percentage of events that are from notable artists",
                    color=discord.Color.gold()
                )
                
                # Add comparison data for each region
                for region, data in comparison_data.items():
                    # Format the data
                    total_events = f"{data['total_events']}"
                    notable_events = f"{data['notable_events']}"
                    percentage = f"{data['percentage_notable']:.1f}%"
                    
                    # Add field for this region
                    embed.add_field(
                        name=f"{region}",
                        value=(
                            f"**Total Events:** {total_events}\n"
                            f"**Notable Events:** {notable_events}\n"
                            f"**Percentage Notable:** {percentage}"
                        ),
                        inline=False
                    )
                
                # Add timestamp
                embed.timestamp = datetime.now(timezone.utc)
                
                # Send the embed
                await msg.delete()
                await ctx.send(embed=embed)
                
                # Create a bar chart showing the percentage of notable events by region
                fig, ax = plt.subplots(figsize=(10, 6))
                
                regions = list(comparison_data.keys())
                percentages = [comparison_data[r]['percentage_notable'] for r in regions]
                
                ax.bar(regions, percentages, color='gold')
                
                # Format the plot
                ax.set_title(f"Percentage of Notable Events by Region (Past {days} Days)")
                ax.set_xlabel("Region")
                ax.set_ylabel("Percentage of Notable Events")
                ax.set_ylim(0, max(100, max(percentages) * 1.1))  # Set y limit to max 100% or slightly above max value
                
                # Add percentage labels above bars
                for i, v in enumerate(percentages):
                    ax.text(i, v + 1, f"{v:.1f}%", ha='center')
                
                # Save the plot to a buffer
                buf = io.BytesIO()
                plt.tight_layout()
                fig.savefig(buf, format='png')
                buf.seek(0)
                
                # Send the plot
                file = discord.File(buf, filename="notable_comparison.png")
                await ctx.send(file=file)
                plt.close(fig)
        except Exception as e:
            logger.error(f"Error in notable_comparison_command: {e}", exc_info=True)
            await msg.edit(content=f"An error occurred while generating comparison data.")

    async def _generate_region_hours(self, ctx, region=None, days=30):
        """Helper function to generate region hours graph without status messages."""
        async with db_pool.db_pool.acquire() as conn:
            # Get the data
            data = await get_region_activity_by_hour(conn, region, days)
            
            if not data:
                await ctx.send(f"No hourly data available for {region or 'all regions'} in the past {days} days.")
                return
            
            # Create a plot
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Group by region
            regions = set(item['serverid'] for item in data)
            for r in regions:
                region_data = [item for item in data if item['serverid'] == r]
                hours = [item['hour_of_day'] for item in region_data]
                new_events = [item['total_new_events'] for item in region_data]
                ax.plot(hours, new_events, 'o-', label=r)
            
            # Format the plot
            ax.set_title(f"Total New Events by Hour of Day (Past {days} Days)")
            ax.set_xlabel("Hour of Day (UTC)")
            ax.set_ylabel("Total New Events")
            ax.set_xticks(range(0, 24))
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend()
            
            # Save the plot to a buffer
            buf = io.BytesIO()
            plt.tight_layout()
            fig.savefig(buf, format='png')
            buf.seek(0)
            
            # Send the plot
            file = discord.File(buf, filename="region_hours.png")
            await ctx.send(
                f"**Hourly activity for {region or 'all regions'} over the past {days} days:**", 
                file=file
            )
            plt.close(fig)

    async def _generate_region_days(self, ctx, region=None, days=30):
        """Helper function to generate region days graph without status messages."""
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        async with db_pool.db_pool.acquire() as conn:
            # Get the data
            data = await get_region_activity_by_day(conn, region, days)
            
            if not data:
                await ctx.send(f"No daily data available for {region or 'all regions'} in the past {days} days.")
                return
            
            # Create a plot
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Group by region
            regions = set(item['serverid'] for item in data)
            for r in regions:
                region_data = [item for item in data if item['serverid'] == r]
                # Sort by day of week (0 = Monday, 6 = Sunday)
                region_data.sort(key=lambda x: x['day_of_week'])
                days_of_week = [item['day_of_week'] for item in region_data]
                new_events = [item['total_new_events'] for item in region_data]
                
                # Convert day numbers to day names for x-axis
                day_labels = [day_names[d] for d in days_of_week]
                
                ax.plot(day_labels, new_events, 'o-', label=r)
            
            # Format the plot
            ax.set_title(f"Total New Events by Day of Week (Past {days} Days)")
            ax.set_xlabel("Day of Week")
            ax.set_ylabel("Total New Events")
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend()
            
            # Save the plot to a buffer
            buf = io.BytesIO()
            plt.tight_layout()
            fig.savefig(buf, format='png')
            buf.seek(0)
            
            # Send the plot
            file = discord.File(buf, filename="region_days.png")
            await ctx.send(
                f"**Daily activity for {region or 'all regions'} over the past {days} days:**", 
                file=file
            )
            plt.close(fig)

    async def _generate_region_heatmap(self, ctx, days=30):
        """Helper function to generate region heatmap without status messages."""
        async with db_pool.db_pool.acquire() as conn:
            # Get the data
            data = await get_hourly_heatmap_data(conn, days)
            
            if not data:
                await ctx.send(f"No data available for heatmap in the past {days} days.")
                return
            
            # Reshape data for heatmap
            regions = sorted(list(set(item['serverid'] for item in data)))
            hours = list(range(24))
            
            # Create a matrix for the heatmap
            heatmap_data = np.zeros((len(regions), 24))
            
            # Fill in the data
            for item in data:
                region_idx = regions.index(item['serverid'])
                hour = item['hour_of_day']
                total_events = item['total_new_events']
                heatmap_data[region_idx, hour] = total_events
            
            # Create a plot
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Create the heatmap
            im = ax.imshow(heatmap_data, cmap='viridis')
            
            # Add colorbar
            cbar = ax.figure.colorbar(im, ax=ax)
            cbar.ax.set_ylabel("Total New Events", rotation=-90, va="bottom")
            
            # Set ticks and labels
            ax.set_xticks(np.arange(24))
            ax.set_xticklabels(hours)
            ax.set_yticks(np.arange(len(regions)))
            ax.set_yticklabels(regions)
            
            # Label the chart
            ax.set_title(f"Total New Event Activity Heatmap by Region and Hour (Past {days} Days)")
            ax.set_xlabel("Hour of Day (UTC)")
            ax.set_ylabel("Region")
            
            # Loop over data dimensions and create text annotations
            for i in range(len(regions)):
                for j in range(24):
                    text = ax.text(j, i, f"{heatmap_data[i, j]:.1f}",
                                ha="center", va="center", color="w" if heatmap_data[i, j] > np.max(heatmap_data)/2 else "black")
            
            # Save the plot to a buffer
            buf = io.BytesIO()
            plt.tight_layout()
            fig.savefig(buf, format='png')
            buf.seek(0)
            
            # Send the plot
            file = discord.File(buf, filename="region_heatmap.png")
            await ctx.send(
                f"**Regional activity heatmap for the past {days} days:**", 
                file=file
            )
            plt.close(fig)

    async def _generate_region_trends(self, ctx, days=14):
        """Helper function to generate region trends without status messages."""
        async with db_pool.db_pool.acquire() as conn:
            # Get the data
            trend_data = await get_region_trending_data(conn, None, days)
            
            if not trend_data:
                await ctx.send(f"No trend data available for the past {days} days.")
                return
            
            # Create an embed to display the trend data
            embed = discord.Embed(
                title=f"Regional Activity Trends (Past {days} Days)",
                description=f"Comparing recent {days//2} days vs previous {days//2} days",
                color=discord.Color.blue()
            )
            
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
                
                # Add field for this region
                embed.add_field(
                    name=f"{region} {indicator}",
                    value=(
                        f"**All Events:** {recent_events} (was {past_events}, {events_change})\n"
                        f"**New Events:** {recent_new} (was {past_new}, {new_change})"
                    ),
                    inline=False
                )
            
            # Add timestamp
            embed.timestamp = datetime.now(timezone.utc)
            
            # Send the embed
            await ctx.send(embed=embed)

    async def _generate_notable_hours(self, ctx, region=None, days=30):
        """Helper function to generate notable hours graph without status messages."""
        async with db_pool.db_pool.acquire() as conn:
            # Get the data
            data = await get_notable_events_by_hour(conn, region, days)
            
            if not data:
                await ctx.send(f"No notable events data available for {region or 'all regions'} in the past {days} days.")
                return
            
            # Create a plot
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Group by region
            regions = set(item['region'] for item in data)
            for r in regions:
                region_data = [item for item in data if item['region'] == r]
                hours = [item['hour_of_day'] for item in region_data]
                new_events = [item['total_new_events'] for item in region_data]
                ax.plot(hours, new_events, 'o-', label=r)
            
            # Format the plot
            ax.set_title(f"Total New Notable Events by Hour of Day (Past {days} Days)")
            ax.set_xlabel("Hour of Day (UTC)")
            ax.set_ylabel("Total New Notable Events")
            ax.set_xticks(range(0, 24))
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend()
            
            # Save the plot to a buffer
            buf = io.BytesIO()
            plt.tight_layout()
            fig.savefig(buf, format='png')
            buf.seek(0)
            
            # Send the plot
            file = discord.File(buf, filename="notable_hours.png")
            await ctx.send(
                f"**Hourly notable artist activity for {region or 'all regions'} over the past {days} days:**", 
                file=file
            )
            plt.close(fig)

    async def _generate_notable_days(self, ctx, region=None, days=30):
        """Helper function to generate notable days graph without status messages."""
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        async with db_pool.db_pool.acquire() as conn:
            # Get the data
            data = await get_notable_events_by_day(conn, region, days)
            
            if not data:
                await ctx.send(f"No notable events data available for {region or 'all regions'} in the past {days} days.")
                return
            
            # Create a plot
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Group by region
            regions = set(item['region'] for item in data)
            for r in regions:
                region_data = [item for item in data if item['region'] == r]
                # Sort by day of week (0 = Monday, 6 = Sunday)
                region_data.sort(key=lambda x: x['day_of_week'])
                days_of_week = [item['day_of_week'] for item in region_data]
                new_events = [item['total_new_events'] for item in region_data]
                
                # Convert day numbers to day names for x-axis
                day_labels = [day_names[d] for d in days_of_week]
                
                ax.plot(day_labels, new_events, 'o-', label=r)
            
            # Format the plot
            ax.set_title(f"Total New Notable Events by Day of Week (Past {days} Days)")
            ax.set_xlabel("Day of Week")
            ax.set_ylabel("Total New Notable Events")
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend()
            
            # Save the plot to a buffer
            buf = io.BytesIO()
            plt.tight_layout()
            fig.savefig(buf, format='png')
            buf.seek(0)
            
            # Send the plot
            file = discord.File(buf, filename="notable_days.png")
            await ctx.send(
                f"**Daily notable artist activity for {region or 'all regions'} over the past {days} days:**", 
                file=file
            )
            plt.close(fig)

    async def _generate_notable_comparison(self, ctx, region=None, days=30):
        """Helper function to generate notable comparison without status messages."""
        async with db_pool.db_pool.acquire() as conn:
            # Get the data
            comparison_data = await compare_notable_vs_all_events(conn, region, days)
            
            if not comparison_data:
                await ctx.send(f"No comparison data available for {region or 'all regions'} in the past {days} days.")
                return
            
            # Create an embed to display the comparison data
            embed = discord.Embed(
                title=f"Notable vs All Events Comparison (Past {days} Days)",
                description=f"Percentage of events that are from notable artists",
                color=discord.Color.gold()
            )
            
            # Add comparison data for each region
            for region, data in comparison_data.items():
                # Format the data
                total_events = f"{data['total_events']}"
                notable_events = f"{data['notable_events']}"
                percentage = f"{data['percentage_notable']:.1f}%"
                
                # Add field for this region
                embed.add_field(
                    name=f"{region}",
                    value=(
                        f"**Total Events:** {total_events}\n"
                        f"**Notable Events:** {notable_events}\n"
                        f"**Percentage Notable:** {percentage}"
                    ),
                    inline=False
                )
            
            # Add timestamp
            embed.timestamp = datetime.now(timezone.utc)
            
            # Send the embed
            await ctx.send(embed=embed)
            
            # Create a bar chart showing the percentage of notable events by region
            fig, ax = plt.subplots(figsize=(10, 6))
            
            regions = list(comparison_data.keys())
            percentages = [comparison_data[r]['percentage_notable'] for r in regions]
            
            ax.bar(regions, percentages, color='gold')
            
            # Format the plot
            ax.set_title(f"Percentage of Notable Events by Region (Past {days} Days)")
            ax.set_xlabel("Region")
            ax.set_ylabel("Percentage of Notable Events")
            ax.set_ylim(0, max(100, max(percentages) * 1.1))  # Set y limit to max 100% or slightly above max value
            
            # Add percentage labels above bars
            for i, v in enumerate(percentages):
                ax.text(i, v + 1, f"{v:.1f}%", ha='center')
            
            # Save the plot to a buffer
            buf = io.BytesIO()
            plt.tight_layout()
            fig.savefig(buf, format='png')
            buf.seek(0)
            
            # Send the plot
            file = discord.File(buf, filename="notable_comparison.png")
            await ctx.send(file=file)
            plt.close(fig)

async def setup(bot):
    await bot.add_cog(RegionStats(bot)) 