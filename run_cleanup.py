import asyncio
from database.cleanup import main as cleanup_main

if __name__ == "__main__":
    print("Starting database cleanup...")
    asyncio.run(cleanup_main())
    print("Database cleanup completed.") 