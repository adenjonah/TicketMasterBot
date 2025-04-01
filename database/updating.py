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
                    INSERT INTO Artists (artistID, name, notable, reminder)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (artistID) DO NOTHING
                    ''',
                    artist_id, artist_name, True, False
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
                    INSERT INTO Artists (artistID, name, notable, reminder)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (artistID) DO NOTHING
                    ''',
                    artist_id, artist_name, False, False
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

async def set_artist_reminder(artist_id, artist_name):
    from config.db_pool import db_pool
    from config.logging import logger
    
    try:
        async with db_pool.acquire() as conn:
            # Check if the artist has any active events
            active_events = await conn.fetch(
                """
                SELECT COUNT(*) as event_count
                FROM Events
                WHERE artistID = $1 AND eventDate > NOW()
                """,
                artist_id
            )
            
            has_active_events = active_events and active_events[0]['event_count'] > 0
            
            if not has_active_events:
                logger.warning(f"Artist {artist_name} (ID: {artist_id}) has no active events, but setting reminder anyway")
            
            # Check if artist exists
            if not await artist_exists(conn, artist_id):
                # Insert new artist if not exists
                await conn.execute(
                    '''
                    INSERT INTO Artists (artistID, name, notable, reminder)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (artistID) DO NOTHING
                    ''',
                    artist_id, artist_name, False, True
                )
                logger.info(f"Created new artist {artist_name} (ID: {artist_id}) with reminder set")
            else:
                # Update existing artist to set reminder flag
                await conn.execute(
                    """
                    UPDATE Artists
                    SET reminder = TRUE
                    WHERE artistID = $1
                    """,
                    artist_id
                )
                logger.info(f"Set reminder for existing artist {artist_name} (ID: {artist_id})")
            
            # Return True to indicate successful operation
            return True
    
    except Exception as e:
        # Use logger instead of print for consistent logging
        logger.error(f"Error setting artist reminder: {e}", exc_info=True)
        return False
    
async def clear_artist_reminder(artist_id, artist_name):
    from config.db_pool import db_pool
    from config.logging import logger
    
    try:
        async with db_pool.acquire() as conn:
            # Check if artist exists
            if not await artist_exists(conn, artist_id):
                # Insert new artist if not exists
                await conn.execute(
                    '''
                    INSERT INTO Artists (artistID, name, notable, reminder)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (artistID) DO NOTHING
                    ''',
                    artist_id, artist_name, False, False
                )
                logger.info(f"Created new artist {artist_name} (ID: {artist_id}) with reminder not set")
            else:
                # Update existing artist to clear reminder flag
                await conn.execute(
                    """
                    UPDATE Artists
                    SET reminder = FALSE
                    WHERE artistID = $1
                    """,
                    artist_id
                )
                logger.info(f"Cleared reminder for existing artist {artist_name} (ID: {artist_id})")
            
            # Return True to indicate successful operation
            return True
    
    except Exception as e:
        # Use logger instead of print for consistent logging
        logger.error(f"Error clearing artist reminder: {e}", exc_info=True)
        return False