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
    get_hourly_heatmap_data
)
from config.logging import logger

class RegionStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="region_hours", help="Shows hourly activity for a region")
    async def region_hours_command(self, ctx, region: str = None, days: int = 30):
        """Display hourly event activity for a specific region or all regions."""
        days = min(days, 90)  # Limit to 90 days max for performance
        
        async with db_pool.db_pool.acquire() as conn:
            # Let the user know we're working on it
            msg = await ctx.send(f"Fetching hourly stats for {region or 'all regions'} over the past {days} days...")
            
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
                new_events = [item['avg_new_events'] for item in region_data]
                ax.plot(hours, new_events, 'o-', label=r)
            
            # Format the plot
            ax.set_title(f"Average New Events by Hour of Day (Past {days} Days)")
            ax.set_xlabel("Hour of Day (UTC)")
            ax.set_ylabel("Average New Events")
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
    
    @commands.command(name="region_days", help="Shows daily activity for a region")
    async def region_days_command(self, ctx, region: str = None, days: int = 30):
        """Display daily event activity for a specific region or all regions."""
        days = min(days, 90)  # Limit to 90 days max for performance
        
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        async with db_pool.db_pool.acquire() as conn:
            # Let the user know we're working on it
            msg = await ctx.send(f"Fetching daily stats for {region or 'all regions'} over the past {days} days...")
            
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
                new_events = [item['avg_new_events'] for item in region_data]
                
                # Convert day numbers to day names for x-axis
                day_labels = [day_names[d] for d in days_of_week]
                
                ax.plot(day_labels, new_events, 'o-', label=r)
            
            # Format the plot
            ax.set_title(f"Average New Events by Day of Week (Past {days} Days)")
            ax.set_xlabel("Day of Week")
            ax.set_ylabel("Average New Events")
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
    
    @commands.command(name="region_heatmap", help="Shows a heatmap of regional activity")
    async def region_heatmap_command(self, ctx, days: int = 30):
        """Display a heatmap of regional activity by hour."""
        days = min(days, 90)  # Limit to 90 days max for performance
        
        async with db_pool.db_pool.acquire() as conn:
            # Let the user know we're working on it
            msg = await ctx.send(f"Generating activity heatmap for all regions over the past {days} days...")
            
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
                avg_events = item['avg_new_events']
                heatmap_data[region_idx, hour] = avg_events
            
            # Create a plot
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Create the heatmap
            im = ax.imshow(heatmap_data, cmap='viridis')
            
            # Add colorbar
            cbar = ax.figure.colorbar(im, ax=ax)
            cbar.ax.set_ylabel("Average New Events", rotation=-90, va="bottom")
            
            # Set ticks and labels
            ax.set_xticks(np.arange(24))
            ax.set_xticklabels(hours)
            ax.set_yticks(np.arange(len(regions)))
            ax.set_yticklabels(regions)
            
            # Label the chart
            ax.set_title(f"New Event Activity Heatmap by Region and Hour (Past {days} Days)")
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
    
    @commands.command(name="region_trends", help="Shows trending activity for regions")
    async def region_trends_command(self, ctx, days: int = 14):
        """Display trending activity data comparing recent vs past periods."""
        days = min(days, 90)  # Limit to 90 days max for performance
        
        async with db_pool.db_pool.acquire() as conn:
            # Let the user know we're working on it
            msg = await ctx.send(f"Analyzing regional trends over the past {days} days...")
            
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

async def setup(bot):
    await bot.add_cog(RegionStats(bot)) 