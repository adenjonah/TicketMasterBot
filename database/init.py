import logging
from datetime import datetime, timezone

now = datetime.now(timezone.utc)

# Configure logging
logger = logging.getLogger(__name__)

async def get_table_name(conn, table_base_name):
    """Find the actual table name with case sensitivity in mind."""
    tables = await conn.fetch("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
      AND table_name ILIKE $1
    """, table_base_name)
    
    if not tables:
        return None
        
    # Return the first matching table name
    return tables[0]['table_name']

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
            
            # Check if Server table exists with case-insensitive search
            server_table = await get_table_name(conn, 'server')
            
            if not server_table:
                # Create Server table if it doesn't exist
                logger.info("Creating Server table...")
                await conn.execute('''
                CREATE TABLE Server (
                    ServerID TEXT PRIMARY KEY,
                    status TEXT,
                    last_request TIMESTAMPTZ,
                    events_returned INTEGER DEFAULT 0,
                    new_events INTEGER DEFAULT 0,
                    error_messages TEXT
                )''')
                logger.info("Server table created.")
                
                # Set the server_table variable to the newly created table
                server_table = "Server"
                
            logger.info(f"Using Server table: {server_table}")
            
            # Initializing Server table with short IDs
            logger.info("Initializing Server table with default ServerIDs...")
            await conn.execute(f'''
            INSERT INTO {server_table} (ServerID) VALUES
            ('no'),
            ('ea'),
            ('so'),
            ('we'),
            ('eu'),
            ('co'),
            ('th')
            ON CONFLICT (ServerID) DO NOTHING
            ''')
            logger.info("Server table initialized with default ServerIDs.")
            
            # Check for and convert any legacy server IDs
            logger.info("Checking for legacy server IDs...")
            legacy_ids = {
                'north': 'no',
                'east': 'ea',
                'south': 'so',
                'west': 'we',
                'europe': 'eu',
                'comedy': 'co',
                'theater': 'th'
            }
            
            for legacy_id, short_id in legacy_ids.items():
                # Check if legacy ID exists
                legacy_exists = await conn.fetchval(
                    f"SELECT 1 FROM {server_table} WHERE LOWER(ServerID) = $1", 
                    legacy_id.lower()
                )
                
                if legacy_exists:
                    logger.info(f"Found legacy server ID: {legacy_id} - migrating to {short_id}")
                    
                    # Get legacy data
                    legacy_row = await conn.fetchrow(
                        f"SELECT * FROM {server_table} WHERE LOWER(ServerID) = $1",
                        legacy_id.lower()
                    )
                    
                    # Check if short ID exists
                    short_exists = await conn.fetchval(
                        f"SELECT 1 FROM {server_table} WHERE LOWER(ServerID) = $1", 
                        short_id.lower()
                    )
                    
                    if short_exists:
                        # Update short ID with legacy data if legacy has newer data
                        if legacy_row['last_request']:
                            short_row = await conn.fetchrow(
                                f"SELECT * FROM {server_table} WHERE LOWER(ServerID) = $1",
                                short_id.lower()
                            )
                            
                            if not short_row['last_request'] or legacy_row['last_request'] > short_row['last_request']:
                                await conn.execute(f"""
                                UPDATE {server_table}
                                SET status = $1, last_request = $2, events_returned = $3, new_events = $4, error_messages = $5
                                WHERE LOWER(ServerID) = $6
                                """,
                                legacy_row['status'],
                                legacy_row['last_request'],
                                legacy_row['events_returned'],
                                legacy_row['new_events'],
                                legacy_row['error_messages'],
                                short_id.lower())
                                
                                logger.info(f"Updated {short_id} with data from {legacy_id}")
                    else:
                        # Insert new short ID with legacy data
                        await conn.execute(f"""
                        INSERT INTO {server_table} (ServerID, status, last_request, events_returned, new_events, error_messages)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        short_id,
                        legacy_row['status'],
                        legacy_row['last_request'],
                        legacy_row['events_returned'],
                        legacy_row['new_events'],
                        legacy_row['error_messages'])
                        
                        logger.info(f"Created new entry {short_id} with data from {legacy_id}")
                    
                    # Delete legacy ID
                    await conn.execute(
                        f"DELETE FROM {server_table} WHERE LOWER(ServerID) = $1",
                        legacy_id.lower()
                    )
                    
                    logger.info(f"Removed legacy ID: {legacy_id}")
                    
                    # Update references in time series tables
                    time_series_table = await get_table_name(conn, 'servertimeseries')
                    if time_series_table:
                        await conn.execute(f"""
                        UPDATE {time_series_table}
                        SET ServerID = $1
                        WHERE LOWER(ServerID) = $2
                        """, short_id, legacy_id.lower())
                        
                    notable_table = await get_table_name(conn, 'notableeventstimeseries')
                    if notable_table:
                        await conn.execute(f"""
                        UPDATE {notable_table}
                        SET region = $1
                        WHERE LOWER(region) = $2
                        """, short_id, legacy_id.lower())
                        
                    logger.info(f"Updated references for {legacy_id} -> {short_id}")

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
            
            # Add notification tracking columns if they don't exist
            await conn.execute('''
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'events'
                    AND column_name = 'notification_attempts'
                ) THEN
                    ALTER TABLE Events ADD COLUMN notification_attempts INTEGER DEFAULT 0;
                    RAISE NOTICE 'Added notification_attempts column to Events table';
                END IF;
                
                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'events'
                    AND column_name = 'last_notification_attempt'
                ) THEN
                    ALTER TABLE Events ADD COLUMN last_notification_attempt TIMESTAMPTZ DEFAULT NULL;
                    RAISE NOTICE 'Added last_notification_attempt column to Events table';
                END IF;
                
                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'events'
                    AND column_name = 'notification_error'
                ) THEN
                    ALTER TABLE Events ADD COLUMN notification_error TEXT DEFAULT NULL;
                    RAISE NOTICE 'Added notification_error column to Events table';
                END IF;
            END $$;
            ''')
            
            # Add Verified Fan (VF) tracking columns if they don't exist
            await conn.execute('''
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'events'
                    AND column_name = 'hasvf'
                ) THEN
                    ALTER TABLE Events ADD COLUMN hasVF BOOLEAN DEFAULT FALSE;
                    RAISE NOTICE 'Added hasVF column to Events table';
                END IF;
                
                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'events'
                    AND column_name = 'vfurl'
                ) THEN
                    ALTER TABLE Events ADD COLUMN vfUrl TEXT DEFAULT NULL;
                    RAISE NOTICE 'Added vfUrl column to Events table';
                END IF;
                
                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'events'
                    AND column_name = 'vfdetectedat'
                ) THEN
                    ALTER TABLE Events ADD COLUMN vfDetectedAt TIMESTAMPTZ DEFAULT NULL;
                    RAISE NOTICE 'Added vfDetectedAt column to Events table';
                END IF;
            END $$;
            ''')
            
            # Create index on hasVF for efficient VF queries
            await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_events_hasvf ON Events(hasVF);
            ''')

        except Exception as e:
            logger.error(f"Error during database initialization: {e}", exc_info=True)