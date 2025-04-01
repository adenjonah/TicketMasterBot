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
                notable BOOLEAN DEFAULT FALSE,
                reminder BOOLEAN DEFAULT FALSE
            )''')
            logger.info("Tables created successfully.")

            # Alter existing columns to TIMESTAMPTZ if necessary
            logger.info("Altering Events table columns to TIMESTAMPTZ if necessary...")
            await conn.execute('''
            ALTER TABLE Events
            ALTER COLUMN eventDate TYPE TIMESTAMPTZ USING eventDate AT TIME ZONE 'UTC',
            ALTER COLUMN ticketOnsaleStart TYPE TIMESTAMPTZ USING ticketOnsaleStart AT TIME ZONE 'UTC',
            ALTER COLUMN lastUpdated TYPE TIMESTAMPTZ USING lastUpdated AT TIME ZONE 'UTC';
            ''')
            
            # Check if reminder column exists in Artists table, add it if not
            logger.info("Checking if reminder column exists in Artists table...")
            try:
                await conn.execute('''
                ALTER TABLE Artists
                ADD COLUMN IF NOT EXISTS reminder BOOLEAN DEFAULT FALSE;
                ''')
                logger.info("Reminder column added to Artists table or already exists.")
            except Exception as e:
                logger.error(f"Error adding reminder column to Artists table: {e}", exc_info=True)
                
            logger.info("Database schema updated successfully.")

        except Exception as e:
            logger.error(f"Error during database initialization: {e}", exc_info=True)