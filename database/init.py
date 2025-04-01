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
                lastUpdated TIMESTAMPTZ,
                reminder TIMESTAMPTZ DEFAULT NULL,
                presaleData JSONB DEFAULT NULL
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
            
            # Create a time series table for server status metrics
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS ServerTimeSeries (
                id SERIAL PRIMARY KEY,
                ServerID TEXT NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL,
                status TEXT,
                events_returned INTEGER DEFAULT 0,
                new_events INTEGER DEFAULT 0,
                hour_of_day INTEGER,
                day_of_week INTEGER,
                error_messages TEXT,
                CONSTRAINT fk_server
                    FOREIGN KEY(ServerID)
                    REFERENCES Server(ServerID)
            )''')
            
            # Create index on ServerID and timestamp for efficient time-based queries
            await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_server_timeseries_serverid_timestamp
            ON ServerTimeSeries (ServerID, timestamp);
            ''')
            
            # Create index on hour_of_day for time pattern analysis
            await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_server_timeseries_hour
            ON ServerTimeSeries (hour_of_day);
            ''')
            
            # Create a time series table for notable artist events
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS NotableEventsTimeSeries (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ NOT NULL,
                hour_of_day INTEGER,
                day_of_week INTEGER,
                total_events INTEGER DEFAULT 0,
                new_events INTEGER DEFAULT 0,
                region TEXT
            )''')
            
            # Create indexes for the notable events time series table
            await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_notable_timeseries_timestamp
            ON NotableEventsTimeSeries (timestamp);
            ''')
            
            await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_notable_timeseries_hour
            ON NotableEventsTimeSeries (hour_of_day);
            ''')
            
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

            # Drop and recreate reminder column if it exists with the wrong type
            logger.info("Ensuring reminder column has the correct type...")
            await conn.execute('''
            DO $$
            BEGIN
                -- Check if reminder column exists and is boolean type
                IF EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'events' 
                    AND column_name = 'reminder'
                    AND data_type = 'boolean'
                ) THEN
                    -- Drop the existing boolean column
                    ALTER TABLE Events DROP COLUMN reminder;
                    -- Add it back with the correct type
                    ALTER TABLE Events ADD COLUMN reminder TIMESTAMPTZ DEFAULT NULL;
                    RAISE NOTICE 'Dropped and recreated reminder column with TIMESTAMPTZ type';
                ELSIF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'events'
                    AND column_name = 'reminder'
                ) THEN
                    -- Add the column if it doesn't exist
                    ALTER TABLE Events ADD COLUMN reminder TIMESTAMPTZ DEFAULT NULL;
                    RAISE NOTICE 'Added reminder column with TIMESTAMPTZ type';
                END IF;
            END $$;
            ''')
            logger.info("Reminder column type corrected.")

            # Drop EventPresales table if it exists
            await conn.execute('''
            DROP TABLE IF EXISTS EventPresales CASCADE;
            ''')
            
            # Add presaleData column to Events table if it doesn't exist
            await conn.execute('''
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'events'
                    AND column_name = 'presaledata'
                ) THEN
                    ALTER TABLE Events ADD COLUMN presaleData JSONB DEFAULT NULL;
                    RAISE NOTICE 'Added presaleData column to Events table';
                END IF;
            END $$;
            ''')

        except Exception as e:
            logger.error(f"Error during database initialization: {e}", exc_info=True)