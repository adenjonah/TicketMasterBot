#!/usr/bin/env python3
"""
Utility script to check for events with notification failures.
This helps diagnose why events aren't being sent to Discord.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.db_pool import initialize_db_pool, close_db_pool
from config.config import DATABASE_URL
from config.logging import logger

async def check_notification_failures():
    """Check for events that have failed to send to Discord."""
    await initialize_db_pool(DATABASE_URL)
    
    try:
        from config.db_pool import db_pool
        
        async with db_pool.acquire() as conn:
            print("=== NOTIFICATION FAILURE ANALYSIS ===\n")
            
            # Check events that have never been sent and have no attempts
            print("1. Events never attempted to be sent:")
            never_attempted = await conn.fetch('''
                SELECT eventID, name, region, notification_attempts, notification_error
                FROM Events 
                WHERE sentToDiscord = FALSE 
                AND (notification_attempts IS NULL OR notification_attempts = 0)
                ORDER BY region, name
                LIMIT 10
            ''')
            
            if never_attempted:
                for event in never_attempted:
                    print(f"   - {event['eventid']}: {event['name']} (region: {event['region']})")
            else:
                print("   No events found")
            
            print(f"\nTotal never attempted: {len(never_attempted)}")
            
            # Check events with failed attempts
            print("\n2. Events with failed notification attempts:")
            failed_attempts = await conn.fetch('''
                SELECT eventID, name, region, notification_attempts, notification_error, last_notification_attempt
                FROM Events 
                WHERE sentToDiscord = FALSE 
                AND notification_attempts > 0
                ORDER BY notification_attempts DESC, last_notification_attempt DESC
                LIMIT 10
            ''')
            
            if failed_attempts:
                for event in failed_attempts:
                    print(f"   - {event['eventid']}: {event['name']}")
                    print(f"     Region: {event['region']}, Attempts: {event['notification_attempts']}")
                    print(f"     Last error: {event['notification_error']}")
                    print(f"     Last attempt: {event['last_notification_attempt']}")
                    print()
            else:
                print("   No events with failed attempts found")
            
            # Check events that have reached max attempts
            print("3. Events that have reached max attempts (3+):")
            max_attempts = await conn.fetch('''
                SELECT eventID, name, region, notification_attempts, notification_error
                FROM Events 
                WHERE sentToDiscord = FALSE 
                AND notification_attempts >= 3
                ORDER BY notification_attempts DESC
                LIMIT 10
            ''')
            
            if max_attempts:
                for event in max_attempts:
                    print(f"   - {event['eventid']}: {event['name']} (attempts: {event['notification_attempts']})")
                    print(f"     Error: {event['notification_error']}")
            else:
                print("   No events at max attempts")
            
            # Summary by region
            print("\n4. Summary by region:")
            summary = await conn.fetch('''
                SELECT 
                    region,
                    COUNT(*) as total_unsent,
                    COUNT(CASE WHEN notification_attempts > 0 THEN 1 END) as attempted,
                    COUNT(CASE WHEN notification_attempts >= 3 THEN 1 END) as max_attempts,
                    COUNT(CASE WHEN notification_attempts IS NULL OR notification_attempts = 0 THEN 1 END) as never_attempted
                FROM Events 
                WHERE sentToDiscord = FALSE
                GROUP BY region
                ORDER BY total_unsent DESC
            ''')
            
            if summary:
                print(f"{'Region':<10} {'Total':<8} {'Attempted':<10} {'Max Attempts':<12} {'Never Tried':<12}")
                print("-" * 55)
                for row in summary:
                    print(f"{row['region'] or 'NULL':<10} {row['total_unsent']:<8} {row['attempted']:<10} {row['max_attempts']:<12} {row['never_attempted']:<12}")
            
            # Error types
            print("\n5. Common error types:")
            error_types = await conn.fetch('''
                SELECT 
                    notification_error,
                    COUNT(*) as count
                FROM Events 
                WHERE sentToDiscord = FALSE 
                AND notification_error IS NOT NULL
                GROUP BY notification_error
                ORDER BY count DESC
                LIMIT 5
            ''')
            
            if error_types:
                for error in error_types:
                    print(f"   - {error['notification_error']}: {error['count']} events")
            else:
                print("   No error data found")
                
    except Exception as e:
        logger.error(f"Error checking notification failures: {e}")
    finally:
        await close_db_pool()

if __name__ == "__main__":
    asyncio.run(check_notification_failures())
