import asyncpg
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

async def check_database_schema():
    """Connects to the database and checks the data types of the Events table columns."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        query = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'events'
        ORDER BY ordinal_position;
        """
        rows = await conn.fetch(query)
        print("Columns in 'Events' table and their data types:")
        for row in rows:
            print(f"{row['column_name']}: {row['data_type']}")
    except Exception as e:
        print(f"Error checking database schema: {e}")
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(check_database_schema())