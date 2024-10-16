import discord
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve Discord token and channel ID from environment variables
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))  # Ensure this is an integer

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    
    # Find the channel by ID
    channel = client.get_channel(CHANNEL_ID)
    
    # Check if the channel exists
    if channel:
        print(f"Channel found: {channel.name} (ID: {CHANNEL_ID})")
        await channel.send("Bot has connected to this channel!")
    else:
        print(f"Error: Could not find channel with ID {CHANNEL_ID}. Make sure the bot has access to this channel and the ID is correct.")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content == 'ping':
        await message.channel.send('pong')

# Run the bot
client.run(TOKEN)