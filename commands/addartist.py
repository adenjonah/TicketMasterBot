import discord
from discord.ext import commands
from config.config import DISCORD_CHANNEL_ID
from api.find_artist_and_ID import find_artist_and_id
from database.updating import mark_artist_notable

class AddArtist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="addartist", help="Marks artists as notable by using comma-separated keywords.")
    async def add_artist_command(self, ctx, *, keywords: str):
        keywords_list = [k.strip() for k in keywords.split(",")]
        successful = []
        failed = []

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
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AddArtist(bot))