import discord
from discord.ext import commands
from discord import app_commands
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
from commands.utils import respond_to_context, ContextLike

class RegionStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="region_hours", help="Shows hourly activity for a region")
    async def region_hours_command(self, ctx, region: str = None, days: int = 30):
        """Display hourly event activity for a specific region or all regions."""
        await self.show_region_hours(ctx, region, days)
    
    @app_commands.command(name="region_hours", description="Shows hourly activity for a region")
    @app_commands.describe(
        region="Region to show (leave empty for all regions)",
        days="Number of days to look back (max 90)"
    )
    async def region_hours_slash(self, interaction: discord.Interaction, region: str = None, days: int = 30):
        await self.show_region_hours(interaction, region, days)
        
    async def show_region_hours(self, ctx_or_interaction: ContextLike, region: str = None, days: int = 30):
        """Display hourly event activity for a specific region or all regions."""
        days = min(days, 90)  # Limit to 90 days max for performance
        
        # Show "thinking" indicator for slash commands
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.defer(thinking=True)
            
        async with db_pool.db_pool.acquire() as conn:
            # Get the data
            data = await get_region_activity_by_hour(conn, region, days)
            
            if not data:
                message = f"No data available for {region or 'all regions'} in the past {days} days."
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(content=message)
                else:
                    await ctx_or_interaction.send(message)
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
            message = f"Hourly activity for {region or 'all regions'} over the past {days} days:"
            
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(content=message, file=file)
            else:
                await ctx_or_interaction.send(content=message, file=file)
                
            plt.close(fig)
    
    @commands.command(name="region_days", help="Shows daily activity for a region")
    async def region_days_command(self, ctx, region: str = None, days: int = 30):
        """Display daily event activity for a specific region or all regions."""
        await self.show_region_days(ctx, region, days)
    
    @app_commands.command(name="region_days", description="Shows daily activity for a region")
    @app_commands.describe(
        region="Region to show (leave empty for all regions)",
        days="Number of days to look back (max 90)"
    )
    async def region_days_slash(self, interaction: discord.Interaction, region: str = None, days: int = 30):
        await self.show_region_days(interaction, region, days)
    
    async def show_region_days(self, ctx_or_interaction: ContextLike, region: str = None, days: int = 30):
        """Display daily event activity for a specific region or all regions."""
        days = min(days, 90)  # Limit to 90 days max for performance
        
        # Show "thinking" indicator for slash commands
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.defer(thinking=True)
        
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        async with db_pool.db_pool.acquire() as conn:
            # Get the data
            data = await get_region_activity_by_day(conn, region, days)
            
            if not data:
                message = f"No data available for {region or 'all regions'} in the past {days} days."
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(content=message)
                else:
                    await ctx_or_interaction.send(message)
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
            message = f"Daily activity for {region or 'all regions'} over the past {days} days:"
            
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(content=message, file=file)
            else:
                await ctx_or_interaction.send(content=message, file=file)
                
            plt.close(fig)
    
    @commands.command(name="region_heatmap", help="Shows a heatmap of regional activity")
    async def region_heatmap_command(self, ctx, days: int = 30):
        """Display a heatmap of regional activity by hour."""
        await self.show_region_heatmap(ctx, days)
    
    @app_commands.command(name="region_heatmap", description="Shows a heatmap of regional activity")
    @app_commands.describe(days="Number of days to look back (max 90)")
    async def region_heatmap_slash(self, interaction: discord.Interaction, days: int = 30):
        await self.show_region_heatmap(interaction, days)
    
    async def show_region_heatmap(self, ctx_or_interaction: ContextLike, days: int = 30):
        """Display a heatmap of regional activity by hour."""
        days = min(days, 90)  # Limit to 90 days max for performance
        
        # Show "thinking" indicator for slash commands
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.defer(thinking=True)
        
        async with db_pool.db_pool.acquire() as conn:
            # Get the data
            data = await get_hourly_heatmap_data(conn, days)
            
            if not data:
                message = f"No data available for heatmap in the past {days} days."
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(content=message)
                else:
                    await ctx_or_interaction.send(message)
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
                avg_events = item['total_new_events']
                heatmap_data[region_idx, hour] = avg_events
            
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
            message = f"Regional activity heatmap for the past {days} days:"
            
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(content=message, file=file)
            else:
                await ctx_or_interaction.send(content=message, file=file)
                
            plt.close(fig)
    
    @commands.command(name="region_trends", help="Shows trending activity for regions")
    async def region_trends_command(self, ctx, days: int = 14):
        """Display trending activity data comparing recent vs past periods."""
        await self.show_region_trends(ctx, days)
    
    @app_commands.command(name="region_trends", description="Shows trending activity for regions")
    @app_commands.describe(days="Number of days to analyze (max 90)")
    async def region_trends_slash(self, interaction: discord.Interaction, days: int = 14):
        await self.show_region_trends(interaction, days)
    
    async def show_region_trends(self, ctx_or_interaction: ContextLike, days: int = 14):
        """Display trending activity data comparing recent vs past periods."""
        days = min(days, 90)  # Limit to 90 days max for performance
        
        # Show "thinking" indicator for slash commands
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.defer(thinking=True)
        
        async with db_pool.db_pool.acquire() as conn:
            # Get the data
            trend_data = await get_region_trending_data(conn, None, days)
            
            if not trend_data:
                message = f"No trend data available for the past {days} days."
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(content=message)
                else:
                    await ctx_or_interaction.send(message)
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
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
    
    @commands.command(name="notable_hours", help="Shows hourly activity for notable artist events")
    async def notable_hours_command(self, ctx, region: str = None, days: int = 30):
        """Display hourly notable event activity for a specific region or all regions."""
        await self.show_notable_hours(ctx, region, days)
        
    @app_commands.command(name="notable_hours", description="Shows hourly activity for notable artist events")
    @app_commands.describe(
        region="Region to show (leave empty for all regions)",
        days="Number of days to look back (max 90)"
    )
    async def notable_hours_slash(self, interaction: discord.Interaction, region: str = None, days: int = 30):
        await self.show_notable_hours(interaction, region, days)
    
    async def show_notable_hours(self, ctx_or_interaction: ContextLike, region: str = None, days: int = 30):
        """Display hourly notable event activity for a specific region or all regions."""
        days = min(days, 90)  # Limit to 90 days max for performance
        
        # Show "thinking" indicator for slash commands
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.defer(thinking=True)
        
        async with db_pool.db_pool.acquire() as conn:
            # Get the data
            data = await get_notable_events_by_hour(conn, region, days)
            
            if not data:
                message = f"No notable events data available for {region or 'all regions'} in the past {days} days."
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(content=message)
                else:
                    await ctx_or_interaction.send(message)
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
            message = f"Hourly notable artist activity for {region or 'all regions'} over the past {days} days:"
            
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(content=message, file=file)
            else:
                await ctx_or_interaction.send(content=message, file=file)
                
            plt.close(fig)
    
    @commands.command(name="notable_days", help="Shows daily activity for notable artist events")
    async def notable_days_command(self, ctx, region: str = None, days: int = 30):
        """Display daily notable event activity for a specific region or all regions."""
        await self.show_notable_days(ctx, region, days)
        
    @app_commands.command(name="notable_days", description="Shows daily activity for notable artist events")
    @app_commands.describe(
        region="Region to show (leave empty for all regions)",
        days="Number of days to look back (max 90)"
    )
    async def notable_days_slash(self, interaction: discord.Interaction, region: str = None, days: int = 30):
        await self.show_notable_days(interaction, region, days)
    
    async def show_notable_days(self, ctx_or_interaction: ContextLike, region: str = None, days: int = 30):
        """Display daily notable event activity for a specific region or all regions."""
        days = min(days, 90)  # Limit to 90 days max for performance
        
        # Show "thinking" indicator for slash commands
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.defer(thinking=True)
        
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        async with db_pool.db_pool.acquire() as conn:
            # Get the data
            data = await get_notable_events_by_day(conn, region, days)
            
            if not data:
                message = f"No notable events data available for {region or 'all regions'} in the past {days} days."
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(content=message)
                else:
                    await ctx_or_interaction.send(message)
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
            message = f"Daily notable artist activity for {region or 'all regions'} over the past {days} days:"
            
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(content=message, file=file)
            else:
                await ctx_or_interaction.send(content=message, file=file)
                
            plt.close(fig)
    
    @commands.command(name="notable_comparison", help="Shows comparison between notable and all events")
    async def notable_comparison_command(self, ctx, region: str = None, days: int = 30):
        """Display comparison between notable and all events for a specific region or all regions."""
        await self.show_notable_comparison(ctx, region, days)
        
    @app_commands.command(name="notable_comparison", description="Shows comparison between notable and all events")
    @app_commands.describe(
        region="Region to show (leave empty for all regions)",
        days="Number of days to look back (max 90)"
    )
    async def notable_comparison_slash(self, interaction: discord.Interaction, region: str = None, days: int = 30):
        await self.show_notable_comparison(interaction, region, days)
    
    async def show_notable_comparison(self, ctx_or_interaction: ContextLike, region: str = None, days: int = 30):
        """Display comparison between notable and all events for a specific region or all regions."""
        days = min(days, 90)  # Limit to 90 days max for performance
        
        # Show "thinking" indicator for slash commands
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.defer(thinking=True)
        
        async with db_pool.db_pool.acquire() as conn:
            # Get the data
            comparison_data = await compare_notable_vs_all_events(conn, region, days)
            
            if not comparison_data:
                message = f"No comparison data available for {region or 'all regions'} in the past {days} days."
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.followup.send(content=message)
                else:
                    await ctx_or_interaction.send(message)
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
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
            
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
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(file=file)
            else:
                await ctx_or_interaction.send(file=file)
                
            plt.close(fig)

async def setup(bot):
    await bot.add_cog(RegionStats(bot))
    
    # Register the stats command group
    stats_group = app_commands.Group(name="stats", description="Statistics and analytics commands")
    
    # Add the commands to the stats group
    # We could add them individually here if we wanted custom groups
    # But the individual commands are already registered
    
    # Add the group to the bot's command tree
    bot.tree.add_command(stats_group) 