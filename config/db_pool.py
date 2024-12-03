import asyncpg

db_pool = None  # Global database pool placeholder

async def initialize_db_pool(database_url, min_size=1, max_size=10):
    """Initialize and return the global database pool."""
    global db_pool
    if db_pool is None:  # Ensure the pool is created only once
        db_pool = await asyncpg.create_pool(
            database_url, min_size=min_size, max_size=max_size
        )
    return db_pool

async def close_db_pool():
    """Close the global database pool."""
    global db_pool
    if db_pool is not None:
        await db_pool.close()
        db_pool = None