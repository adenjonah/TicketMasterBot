import aiohttp  # For async HTTP requests
import psycopg2
import discord
from psycopg2.extras import DictCursor
import logging
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
import asyncpg
from dateutil import parser
import asyncio

now = datetime.now(timezone.utc)

from config.config import (
    DISCORD_BOT_TOKEN,
    DISCORD_CHANNEL_ID,
    DISCORD_CHANNEL_ID_TWO,
    TICKETMASTER_API_KEY,
    REDIRECT_URI,
    DATABASE_URL,
    DEBUG,
)

async def initialize_db():
    """Create tables if they do not exist and ensure schema compatibility."""
    print("Initializing the database...")

    # Import db_pool here to ensure it is initialized
    from config.db_pool import db_pool  # Defer the import until runtime

    async with db_pool.acquire() as conn:  # Use the connection pool
        try:
            # Create tables with correct data types
            print("Creating tables if they do not exist...")
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
            print("Tables created successfully.")

            # Alter existing columns to TIMESTAMPTZ if necessary
            print("Altering Events table columns to TIMESTAMPTZ if necessary...")
            await conn.execute('''
            ALTER TABLE Events
            ALTER COLUMN eventDate TYPE TIMESTAMPTZ USING eventDate AT TIME ZONE 'UTC',
            ALTER COLUMN ticketOnsaleStart TYPE TIMESTAMPTZ USING ticketOnsaleStart AT TIME ZONE 'UTC',
            ALTER COLUMN lastUpdated TYPE TIMESTAMPTZ USING lastUpdated AT TIME ZONE 'UTC';
            ''')
            print("Database schema updated successfully.")

            # Load notable artist IDs from artist_ids.txt
            # ... rest of your existing code ...

        except Exception as e:
            print(f"Error during database initialization: {e}")