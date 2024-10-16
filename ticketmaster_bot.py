import discord
from discord.ext import commands, tasks
import requests
import os
import asyncio
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve API keys from environment variables
TICKETMASTER_API_KEY = os.getenv('TICKETMASTER_API_KEY')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

if not TICKETMASTER_API_KEY or not DISCORD_BOT_TOKEN or not CHANNEL_ID:
    raise ValueError("Missing environment variables. Please check your .env file.")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

known_events = set()

def get_events(start_date, end_date):
    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {
        "apikey": TICKETMASTER_API_KEY,
        "startDateTime": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDateTime": end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "size": 200
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get("_embedded", {}).get("events", [])
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return []

@tasks.loop(minutes=1)
async def check_for_new_events():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f"Error: Could not find channel with ID {CHANNEL_ID}")
        return

    now = datetime.now(timezone.utc)
    end_date = now + timedelta(days=30)
    
    events = get_events(now, end_date)
    new_events = []
    
    for event in events:
        event_id = event['id']
        if event_id not in known_events:
            known_events.add(event_id)
            new_events.append(event)
    
    if new_events:
        for event in new_events:
            embed = discord.Embed(
                title=event['name'],
                url=event['url'],
                description=f"Date: {event['dates']['start']['localDate']}",
                color=discord.Color.blue()
            )
            if 'images' in event and event['images']:
                embed.set_thumbnail(url=event['images'][0]['url'])
            await channel.send(embed=embed)
    else:
        print("No new events found.")

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    check_for_new_events.start()

@bot.command(name='events')
async def list_events(ctx):
    now = datetime.now(timezone.utc)
    end_date = now + timedelta(days=30)
    events = get_events(now, end_date)
    
    if not events:
        await ctx.send("No upcoming events found.")
        return

    for event in events[:5]:  # Limit to 5 events to avoid flooding the channel
        embed = discord.Embed(
            title=event['name'],
            url=event['url'],
            description=f"Date: {event['dates']['start']['localDate']}",
            color=discord.Color.green()
        )
        if 'images' in event and event['images']:
            embed.set_thumbnail(url=event['images'][0]['url'])
        await ctx.send(embed=embed)

    if len(events) > 5:
        await ctx.send(f"And {len(events) - 5} more events...")

if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)