import discord
from discord.ext import commands
from .hourly import HourlyStats
from .daily import DailyStats
from .regional import RegionalStats
from .comparison import ComparisonStats
from config.logging import logger

class StatsCommands(HourlyStats, DailyStats, RegionalStats, ComparisonStats):
    """Main stats commands that combines all statistics functionality."""

    @commands.command(name="stats", help="Generates all stats and graphs at once")
    async def all_stats_command(self, ctx, region: str = None, days: int = 30):
        """Generate and send all statistics graphs for the specified region or all regions."""
        days = await self._validate_days(days)
        region_str = await self._get_region_string(region)
        
        # Initial message to let user know we're working on it
        msg = await self._send_status_message(
            ctx, f"Generating all stats for {region_str} over the past {days} days...\nThis might take a minute, please wait.")
        
        try:
            # Create a list to track successful and failed stats
            successful = []
            failed = []
            
            # 1. Region Hours
            await self._update_status(msg, "Generating hourly activity stats...")
            try:
                if await self._generate_region_hours(ctx, region, days):
                    successful.append("Region Hours")
                else:
                    failed.append("Region Hours")
            except Exception as e:
                logger.error(f"Error generating region hours: {e}", exc_info=True)
                failed.append("Region Hours")
                
            # 2. Region Days
            await self._update_status(msg, "Generating daily activity stats...")
            try:
                if await self._generate_region_days(ctx, region, days):
                    successful.append("Region Days")
                else:
                    failed.append("Region Days")
            except Exception as e:
                logger.error(f"Error generating region days: {e}", exc_info=True)
                failed.append("Region Days")
                
            # 3. Region Heatmap
            await self._update_status(msg, "Generating activity heatmap...")
            try:
                if await self._generate_region_heatmap(ctx, days):
                    successful.append("Region Heatmap")
                else:
                    failed.append("Region Heatmap")
            except Exception as e:
                logger.error(f"Error generating region heatmap: {e}", exc_info=True)
                failed.append("Region Heatmap")
                
            # 4. Region Trends
            await self._update_status(msg, "Analyzing regional trends...")
            try:
                if await self._generate_region_trends(ctx, days):
                    successful.append("Region Trends")
                else:
                    failed.append("Region Trends")
            except Exception as e:
                logger.error(f"Error generating region trends: {e}", exc_info=True)
                failed.append("Region Trends")
                
            # 5. Notable Hours
            await self._update_status(msg, "Generating notable hourly stats...")
            try:
                if await self._generate_notable_hours(ctx, region, days):
                    successful.append("Notable Hours")
                else:
                    failed.append("Notable Hours")
            except Exception as e:
                logger.error(f"Error generating notable hours: {e}", exc_info=True)
                failed.append("Notable Hours")
                
            # 6. Notable Days
            await self._update_status(msg, "Generating notable daily stats...")
            try:
                if await self._generate_notable_days(ctx, region, days):
                    successful.append("Notable Days")
                else:
                    failed.append("Notable Days")
            except Exception as e:
                logger.error(f"Error generating notable days: {e}", exc_info=True)
                failed.append("Notable Days")
                
            # 7. Notable Comparison
            await self._update_status(msg, "Comparing notable vs all events...")
            try:
                if await self._generate_notable_comparison(ctx, region, days):
                    successful.append("Notable Comparison")
                else:
                    failed.append("Notable Comparison")
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

async def setup(bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(StatsCommands(bot)) 