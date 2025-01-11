import logging
from datetime import datetime, timezone

now = datetime.now(timezone.utc)

# Configure logging
logger = logging.getLogger(__name__)

async def initialize_db():
    """Create tables if they do not exist and ensure schema compatibility."""
    logger.info("Initializing the database...")

    # Import db_pool here to ensure it is initialized
    from config.db_pool import db_pool  # Defer the import until runtime

    async with db_pool.acquire() as conn:  # Use the connection pool
        try:
            # Create tables with correct data types
            logger.info("Creating tables if they do not exist...")
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS Events (
                eventID TEXT PRIMARY KEY,
                name TEXT,
                artistID TEXT,
                venueID TEXT,
                eventDate TIMESTAMPTZ,
                ticketOnsaleStart TIMESTAMPTZ,
                url TEXT,
                image_url TEXT,
                sentToDiscord BOOLEAN DEFAULT FALSE,
                lastUpdated TIMESTAMPTZ
            )''')
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS Venues (
                venueID TEXT PRIMARY KEY,
                name TEXT,
                city TEXT,
                state TEXT
            )''')
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS Artists (
                artistID TEXT PRIMARY KEY,
                name TEXT,
                notable BOOLEAN DEFAULT FALSE
            )''')
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS Server (
                ServerID TEXT PRIMARY KEY,
                status TEXT,
                last_request TIMESTAMPTZ,
                events_returned INTEGER DEFAULT 0,
                new_events INTEGER DEFAULT 0,
                error_messages TEXT
            )''')
            logger.info("Tables created successfully.")
            
            logger.info("Initializing Server table with default ServerIDs...")
            await conn.execute('''
            INSERT INTO Server (ServerID) VALUES
            ('north'),
            ('east'),
            ('south'),
            ('west'),
            ('comedy')
            ON CONFLICT (ServerID) DO NOTHING
            ''')
            logger.info("Server table initialized with default ServerIDs.")

            # Alter existing columns to TIMESTAMPTZ if necessary
            logger.info("Altering Events table columns to TIMESTAMPTZ if necessary...")
            await conn.execute('''
            ALTER TABLE Events
            ALTER COLUMN eventDate TYPE TIMESTAMPTZ USING eventDate AT TIME ZONE 'UTC',
            ALTER COLUMN ticketOnsaleStart TYPE TIMESTAMPTZ USING ticketOnsaleStart AT TIME ZONE 'UTC',
            ALTER COLUMN lastUpdated TYPE TIMESTAMPTZ USING lastUpdated AT TIME ZONE 'UTC';
            ''')
            logger.info("Database schema updated successfully.")

        except Exception as e:
            logger.error(f"Error during database initialization: {e}", exc_info=True)