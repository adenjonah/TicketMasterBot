from discord.ext import commands
import asyncio
import psycopg2
import requests
from config.config import DATABASE_URL, TICKETMASTER_API_KEY, DISCORD_CHANNEL_ID

async def find_artist_and_id(kw):
    def blocking_request():
        url = f"https://app.ticketmaster.com/discovery/v2/attractions?apikey={TICKETMASTER_API_KEY}&keyword={kw}&locale=*"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Get all attractions
        attractions = data.get("_embedded", {}).get("attractions", [])
        if not attractions:
            return None
        
        # Find the most exact match
        exact_matches = [
            artist for artist in attractions 
            if artist['name'].lower() == kw.lower()
        ]
        
        # If exact match found, return first result
        if exact_matches:
            return [exact_matches[0]["id"], exact_matches[0]["name"]]
        
        # If no exact match, return first result (previous behavior)
        return [attractions[0]["id"], attractions[0]["name"]]
    
    return await asyncio.to_thread(blocking_request)