"""
Utility functions for command handling and slash command conversion
"""
import discord
from discord import app_commands
from typing import Optional, Union, Callable, Awaitable, List, Dict, Any

# Type hint for a context-like object
ContextLike = Union[discord.Interaction, discord.ext.commands.Context]

async def respond_to_context(
    ctx_or_interaction: ContextLike, 
    content: Optional[str] = None, 
    embed: Optional[discord.Embed] = None,
    ephemeral: bool = False
) -> None:
    """
    Sends a response to either a Context or Interaction, handling the differences.
    
    Args:
        ctx_or_interaction: Either a Context or Interaction to respond to
        content: Optional message content
        embed: Optional embed to send
        ephemeral: Whether to make the response ephemeral (only works with Interactions)
    """
    if isinstance(ctx_or_interaction, discord.Interaction):
        if ctx_or_interaction.response.is_done():
            # If we've already responded, use followup
            await ctx_or_interaction.followup.send(
                content=content, 
                embed=embed, 
                ephemeral=ephemeral
            )
        else:
            # First response to an interaction
            await ctx_or_interaction.response.send_message(
                content=content, 
                embed=embed, 
                ephemeral=ephemeral
            )
    else:
        # Regular context from a prefix command
        await ctx_or_interaction.send(content=content, embed=embed)

def get_channel_id(ctx_or_interaction: ContextLike) -> int:
    """Gets the channel ID regardless of whether this is a Context or Interaction"""
    if isinstance(ctx_or_interaction, discord.Interaction):
        return ctx_or_interaction.channel_id
    else:
        return ctx_or_interaction.channel.id

def register_commands(bot) -> None:
    """
    Register all slash commands with the bot.
    This should be called after all cogs are loaded.
    """
    try:
        # Force sync - this is a good practice when testing,
        # but in production you might want to sync only when command definitions change
        bot.tree.clear_commands(guild=None)
        
        # You could add guild-specific commands here if needed
        # Example: bot.tree.add_command(some_command, guild=discord.Object(id=GUILD_ID))
    except Exception as e:
        print(f"Failed to register commands: {e}") 