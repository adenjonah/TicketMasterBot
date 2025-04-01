import discord
from discord.ext import commands
from discord import app_commands
from config.config import DISCORD_CHANNEL_ID
from api.find_artist_and_ID import find_artist_and_id
from database.updating import mark_artist_notable

class AddArtist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Keep the traditional command for backward compatibility
    @commands.command(name="addartist", help="Marks artists as notable by using comma-separated keywords.")
    async def add_artist_command(self, ctx, *, keywords: str):
        await self.process_add_artist(ctx, keywords)

    # Add slash command support
    @app_commands.command(name="addartist", description="Marks artists as notable using comma-separated keywords")
    @app_commands.describe(keywords="Comma-separated list of artist names or keywords to search")
    async def add_artist_slash(self, interaction: discord.Interaction, keywords: str):
        # Create a context-like object for compatibility with the existing code
        ctx = await self.bot.get_context(interaction.message) if interaction.message else interaction.channel
        await self.process_add_artist(ctx, keywords, interaction)

    async def process_add_artist(self, ctx, keywords: str, interaction: discord.Interaction = None):
        keywords_list = [k.strip() for k in keywords.split(",")]
        successful = []
        failed = []

        # Show "thinking" indicator for slash commands since artist lookup might take time
        if interaction and not interaction.response.is_done():
            await interaction.response.defer(thinking=True)

        for kw in keywords_list:
            artist_info = await find_artist_and_id(kw)
            if artist_info:
                artist_id, artist_name = artist_info
                await mark_artist_notable(artist_id, artist_name)
                successful.append(f"{artist_name} (ID: `{artist_id}`)")
            else:
                failed.append(f"`{kw}`")

        # Create the embed
        embed = discord.Embed(title="Add Artist Results")

        if successful:
            embed.add_field(
                name="Successful Artists",
                value="\n".join(successful),
                inline=False
            )
        if failed:
            embed.add_field(
                name="Failed Artists",
                value="\n".join(failed),
                inline=False
            )

        # Set embed color based on results
        if successful and not failed:
            embed.colour = discord.Colour.green()
        elif successful and failed:
            embed.colour = discord.Colour.orange()
        else:
            embed.colour = discord.Colour.red()

        # Send the embed
        if interaction and interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AddArtist(bot))