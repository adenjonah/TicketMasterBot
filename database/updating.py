import discord
from discord.ext import commands
import asyncio
import requests
from config.config import DATABASE_URL, TICKETMASTER_API_KEY, DISCORD_CHANNEL_ID
from database.queries import artist_exists


async def mark_artist_notable(artist_id, artist_name):
    from config.db_pool import db_pool
    
    try:
        async with db_pool.acquire() as conn:
            # Check if artist exists
            if not await artist_exists(conn, artist_id):
                # Insert new artist if not exists
                await conn.execute(
                    '''
                    INSERT INTO Artists (artistID, name, notable)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (artistID) DO NOTHING
                    ''',
                    artist_id, artist_name, True
                )
            else:
                # Update existing artist to mark as notable
                await conn.execute(
                    """
                    UPDATE Artists
                    SET notable = TRUE
                    WHERE artistID = $1
                    """,
                    artist_id
                )
            
            # Return True to indicate successful operation
            return True
    
    except Exception as e:
        # Log the error (you might want to add proper logging)
        print(f"Error marking artist as notable: {e}")
        return False
    
async def mark_artist_notnotable(artist_id, artist_name):
    from config.db_pool import db_pool
    
    try:
        async with db_pool.acquire() as conn:
            # Check if artist exists
            if not await artist_exists(conn, artist_id):
                # Insert new artist if not exists
                await conn.execute(
                    '''
                    INSERT INTO Artists (artistID, name, notable)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (artistID) DO NOTHING
                    ''',
                    artist_id, artist_name, False
                )
            else:
                # Update existing artist to mark as notable
                await conn.execute(
                    """
                    UPDATE Artists
                    SET notable = FALSE
                    WHERE artistID = $1
                    """,
                    artist_id
                )
            
            # Return True to indicate successful operation
            return True
    
    except Exception as e:
        # Log the error (you might want to add proper logging)
        print(f"Error marking artist as notable: {e}")
        return False