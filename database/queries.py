
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