from config.config import (
    DISCORD_BOT_TOKEN,
    DISCORD_CHANNEL_ID,
    DISCORD_CHANNEL_ID_TWO,
    TICKETMASTER_API_KEY,
    REDIRECT_URI,
    DATABASE_URL,
    DEBUG,
)

async def event_exists(conn, event_id):
    """
    Check if an event exists in the database.
    Args:
        conn: The database connection.
        event_id: The ID of the event to check.
    Returns:
        bool: True if the event exists, False otherwise.
    """
    return await conn.fetchval(
        '''
        SELECT 1 FROM Events WHERE eventID = $1
        ''',
        event_id
    )