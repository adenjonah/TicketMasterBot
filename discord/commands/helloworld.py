from discord.ext import commands

class HelloWorld(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="hello")
    async def hello_command(self, ctx):
        await ctx.send("Hello world!")

async def setup(bot):
    await bot.add_cog(HelloWorld(bot))