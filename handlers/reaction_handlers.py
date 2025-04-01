import discord
from config.logging import logger
from datetime import timedelta
import pytz
import json
from dateutil import parser

async def handle_bell_reaction(bot, payload):
    """Handle bell emoji reactions to set reminders for events"""
    # Get the channel and message
    channel = bot.get_channel(payload.channel_id)
    if not channel:
        return
    
    try:
        message = await channel.fetch_message(payload.message_id)
        
        # Check if the message is from our bot and has embeds
        if message.author.id != bot.user.id or not message.embeds:
            return
            
        # Extract the URL from the embed
        embed = message.embeds[0]
        event_url = embed.url
        
        if not event_url:
            logger.warning(f"No URL found in message {message.id}")
            return
            
        # Find the event in the database and set a reminder
        from config.db_pool import db_pool
        
        async with db_pool.acquire() as conn:
            # Get the event based on URL
            event = await conn.fetchrow(
                "SELECT eventID, ticketOnsaleStart, presaleData FROM Events WHERE url = $1",
                event_url
            )
            
            if not event:
                logger.warning(f"No event found with URL: {event_url}")
                return
                
            # Calculate reminder time based on the type of message
            # Check if this is a reaction to a reminder message (title starts with 🔔 REMINDER:)
            is_reminder_message = embed.title and embed.title.startswith("🔔 REMINDER:")
            
            reminder_time = None
            reminder_text = ""
            
            if is_reminder_message:
                # For reactions to reminder messages, set a reminder for 1 hour before sale
                reminder_time = event['ticketonsalestart'] - timedelta(hours=1)
                reminder_text = "1 hour before general sale"
                logger.info(f"Setting 1-hour reminder for event {event['eventid']}")
            else:
                # Check if there's presale data
                if event['presaledata'] and event['presaledata'] != '[]':
                    try:
                        presales = json.loads(event['presaledata'])
                        if presales:
                            # Sort presales by start datetime to find the earliest presale
                            presales.sort(key=lambda x: parser.parse(x['startDateTime']))
                            # Get the earliest presale
                            earliest_presale = presales[0]
                            
                            presale_start_utc = parser.parse(earliest_presale['startDateTime'])
                            
                            # Set reminder for 12 hours before the earliest presale
                            reminder_time = presale_start_utc - timedelta(hours=12)
                            reminder_text = f"12 hours before {earliest_presale['name']} presale"
                            logger.info(f"Setting 12-hour reminder before presale for event {event['eventid']}")
                    except Exception as e:
                        logger.error(f"Error processing presale data: {e}", exc_info=True)
                        # Fall back to general sale if presale processing fails
                        reminder_time = event['ticketonsalestart'] - timedelta(hours=12)
                        reminder_text = "12 hours before general sale"
                        logger.info(f"Setting 12-hour reminder before general sale for event {event['eventid']} (fallback)")
                
                # If no presale data, use general sale
                if not reminder_time:
                    reminder_time = event['ticketonsalestart'] - timedelta(hours=12)
                    reminder_text = "12 hours before general sale"
                    logger.info(f"Setting 12-hour reminder before general sale for event {event['eventid']}")
            
            # Set the reminder - explicitly cast to TIMESTAMPTZ to avoid type issues
            await conn.execute(
                "UPDATE Events SET reminder = $1::TIMESTAMPTZ WHERE eventID = $2",
                reminder_time, event['eventid']
            )
            
            # Format the reminder time for display
            est_tz = pytz.timezone('America/New_York')
            reminder_time_est = reminder_time.astimezone(est_tz)
            reminder_time_str = reminder_time_est.strftime("%B %d, %Y at %I:%M %p EST")
            
            # Edit the original embed to include reminder info
            original_embed = message.embeds[0]
            description = original_embed.description
            
            # Check if the description already has a reminder note
            if "**Reminder set**" not in description:
                # Add the reminder note to the description
                if description.endswith('\n\n'):
                    new_description = f"{description}**Reminder set for {reminder_text}: {reminder_time_str}**"
                else:
                    new_description = f"{description}\n\n**Reminder set for {reminder_text}: {reminder_time_str}**"
                
                # Create a new embed with the updated description
                new_embed = discord.Embed(
                    title=original_embed.title,
                    url=original_embed.url,
                    description=new_description,
                    color=original_embed.color
                )
                
                # Copy the image if it exists
                if original_embed.image:
                    new_embed.set_image(url=original_embed.image.url)
                
                # Update the message with the new embed
                await message.edit(embed=new_embed)
            
            logger.info(f"Reminder set for event {event['eventid']} at {reminder_time}")
            
            # React to the user's reaction to confirm
            await message.add_reaction("✅")
            
    except Exception as e:
        logger.error(f"Error processing reaction: {e}", exc_info=True)

async def handle_bell_reaction_remove(bot, payload):
    """Handle when bell emoji reactions are removed from events"""
    # Get the channel and message
    channel = bot.get_channel(payload.channel_id)
    if not channel:
        return
    
    try:
        message = await channel.fetch_message(payload.message_id)
        
        # Check if the message is from our bot and has embeds
        if message.author.id != bot.user.id or not message.embeds:
            return
        
        # Check if there are any bell reactions left
        has_bell_reactions = any(str(reaction.emoji) == "🔔" for reaction in message.reactions)
        
        # If there are still bell reactions, don't cancel the reminder
        if has_bell_reactions:
            logger.debug(f"Bell reaction removed, but others remain for message {message.id}")
            return
            
        # Extract the URL from the embed
        embed = message.embeds[0]
        event_url = embed.url
        
        if not event_url:
            logger.warning(f"No URL found in message {message.id}")
            return
            
        # Find the event in the database
        from config.db_pool import db_pool
        
        async with db_pool.acquire() as conn:
            # Get the event based on URL
            event = await conn.fetchrow(
                "SELECT eventID FROM Events WHERE url = $1",
                event_url
            )
            
            if not event:
                logger.warning(f"No event found with URL: {event_url}")
                return
            
            # Clear the reminder
            await conn.execute(
                "UPDATE Events SET reminder = NULL WHERE eventID = $1",
                event['eventid']
            )
            
            logger.info(f"Cleared reminder for event {event['eventid']} (all bell reactions removed)")
            
            # Edit the message to remove the reminder info
            original_embed = message.embeds[0]
            description = original_embed.description
            
            # Remove the reminder line from the description
            if "**Reminder set for" in description:
                # Find where the reminder text starts
                reminder_index = description.find("**Reminder set for")
                
                # Find where description ends before the reminder text
                if "\n\n**Reminder set for" in description:
                    # Split at the double newline before the reminder text
                    new_description = description.split("\n\n**Reminder set for")[0]
                else:
                    # Just take the text before the reminder
                    new_description = description[:reminder_index]
                
                # Create a new embed without the reminder text
                new_embed = discord.Embed(
                    title=original_embed.title,
                    url=original_embed.url,
                    description=new_description,
                    color=original_embed.color
                )
                
                # Copy the image if it exists
                if original_embed.image:
                    new_embed.set_image(url=original_embed.image.url)
                
                # Update the message with the new embed
                await message.edit(embed=new_embed)
                
                # Remove checkmark reaction if it exists
                for reaction in message.reactions:
                    if str(reaction.emoji) == "✅":
                        async for user in reaction.users():
                            if user.id == bot.user.id:
                                await message.remove_reaction("✅", bot.user)
                                break
            
    except Exception as e:
        logger.error(f"Error processing reaction removal: {e}", exc_info=True)

async def handle_trash_reaction(bot, payload):
    """Handle trash emoji reactions to delete bot messages"""
    # Get the channel and message
    channel = bot.get_channel(payload.channel_id)
    if not channel:
        return
    
    try:
        message = await channel.fetch_message(payload.message_id)
        
        # Check if the message is from our bot
        if message.author.id != bot.user.id:
            return
            
        # Check if the user is not the bot itself (prevent bot from deleting its own messages)
        if payload.user_id != bot.user.id:
            # Delete the message
            await message.delete()
            logger.info(f"Deleted message {message.id} in response to trash emoji reaction")
            
    except Exception as e:
        logger.error(f"Error processing reaction removal: {e}", exc_info=True) 