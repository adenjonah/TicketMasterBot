import discord
from discord.ext import commands
from datetime import datetime, timezone
from .base import BaseStats
from database.analytics import compare_notable_vs_all_events
from .visualization import create_comparison_bar_chart

class ComparisonStats(BaseStats):
    """Commands for comparing statistics between different types of events."""
    
    @commands.command(name="notable_comparison", help="Shows comparison between notable and all events")
    async def notable_comparison_command(self, ctx, region: str = None, days: int = 30):
        """Display comparison between notable and all events for a specific region or all regions."""
        days = await self._validate_days(days)
        region_str = await self._get_region_string(region)
        
        # Let user know we're working on it
        status_msg = await self._send_status_message(
            ctx, f"Analyzing notable vs all events for {region_str} over the past {days} days...")
        
        try:
            async with await self._acquire_db_connection() as conn:
                # Get the data
                comparison_data = await compare_notable_vs_all_events(conn, region, days)
                
                if not comparison_data:
                    await self._handle_no_data(ctx, status_msg, region_str, days, "comparison")
                    return
                
                # Create an embed to display the comparison data
                data_fields = []
                
                # Add comparison data for each region
                for r, data in comparison_data.items():
                    # Format the data with more context
                    total_events = f"{data['total_events']}"
                    notable_events = f"{data['notable_events']}"
                    percentage = f"{data['percentage_notable']:.1f}%"
                    
                    # Create a visual representation of the percentage
                    bar_length = 20
                    filled = int(data['percentage_notable'] / 100 * bar_length)
                    bar = '█' * filled + '░' * (bar_length - filled)
                    
                    data_fields.append({
                        "name": f"{r}",
                        "value": (
                            f"**Total Events:** {total_events}\n"
                            f"**Notable Events:** {notable_events}\n"
                            f"**Percentage Notable:** {percentage}\n"
                            f"**Visualization:** {bar}"
                        ),
                        "inline": False
                    })
                
                # Generate the embed
                embed = await self._generate_embed_report(
                    title=f"Notable vs All Events Comparison (Past {days} Days)",
                    description=f"Percentage of events that are from notable artists",
                    data_fields=data_fields,
                    color=discord.Color.gold()
                )
                
                # Send the embed
                if status_msg:
                    await status_msg.delete()
                await ctx.send(embed=embed)
                
                # Create a bar chart showing the comparison
                fig = create_comparison_bar_chart(
                    comparison_data,
                    f"Notable vs All Events by Region (Past {days} Days)", 
                    days,
                    region
                )
                
                # Send the plot
                await self._send_plot(
                    ctx, 
                    fig, 
                    "notable_comparison.png",
                    f"Visual comparison of notable vs all events:"
                )
        except Exception as e:
            await self._handle_stats_error(ctx, status_msg, e, "comparison")
    
    async def _generate_notable_comparison(self, ctx, region=None, days=30):
        """Helper function to generate notable comparison for all_stats_command."""
        region_str = await self._get_region_string(region)
        
        try:
            async with await self._acquire_db_connection() as conn:
                # Get the data
                comparison_data = await compare_notable_vs_all_events(conn, region, days)
                
                if not comparison_data:
                    await ctx.send(f"⚠️ No comparison data available for {region_str} in the past {days} days.")
                    return False
                
                # Create an embed to display the comparison data
                data_fields = []
                
                # Add comparison data for each region
                for r, data in comparison_data.items():
                    # Format the data
                    total_events = f"{data['total_events']}"
                    notable_events = f"{data['notable_events']}"
                    percentage = f"{data['percentage_notable']:.1f}%"
                    
                    # Create a visual representation of the percentage
                    bar_length = 20
                    filled = int(data['percentage_notable'] / 100 * bar_length)
                    bar = '█' * filled + '░' * (bar_length - filled)
                    
                    data_fields.append({
                        "name": f"{r}",
                        "value": (
                            f"**Total Events:** {total_events}\n"
                            f"**Notable Events:** {notable_events}\n"
                            f"**Percentage Notable:** {percentage}\n"
                            f"**Visualization:** {bar}"
                        ),
                        "inline": False
                    })
                
                # Generate the embed
                embed = await self._generate_embed_report(
                    title=f"Notable vs All Events Comparison (Past {days} Days)",
                    description=f"Percentage of events that are from notable artists",
                    data_fields=data_fields,
                    color=discord.Color.gold()
                )
                
                # Send the embed
                await ctx.send(embed=embed)
                
                # Create a bar chart showing the comparison
                fig = create_comparison_bar_chart(
                    comparison_data,
                    f"Notable vs All Events by Region (Past {days} Days)",
                    days,
                    region
                )
                
                # Send the plot
                await self._send_plot(
                    ctx, 
                    fig, 
                    "notable_comparison.png",
                    f"Visual comparison of notable vs all events:"
                )
                return True
        except Exception as e:
            await self._handle_stats_error(ctx, None, e, "comparison")
            return False 