"""
Verified Fan (VF) Signup Detection Module

This module provides async functionality to detect Ticketmaster Verified Fan signup pages
for events. It uses a multi-strategy approach:
1. Scrape the event page for VF signup links
2. Fallback to slug guessing based on artist names

All detection is non-blocking and designed for low resource usage.
"""

import aiohttp
import asyncio
import re
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from config.logging import logger

# Load environment variables
load_dotenv()
VF_CHECK_ENABLED = os.getenv('VF_CHECK_ENABLED', 'true').lower() == 'true'
VF_RECHECK_WINDOW_HOURS = int(os.getenv('VF_RECHECK_WINDOW_HOURS', '48'))

# Rate limiting and timeout settings
VF_REQUEST_TIMEOUT = 10  # seconds
VF_MAX_RETRIES = 2


def normalize_artist_slug(artist_name):
    """Generate candidate slugs from artist name for VF URL guessing."""
    if not artist_name:
        return []
    
    slugs = [re.sub(r'[^a-z0-9]', '', artist_name.lower())]
    
    # Alternative: remove leading "the"
    if artist_name.lower().startswith('the '):
        alt_slug = re.sub(r'[^a-z0-9]', '', artist_name[4:].lower())
        if alt_slug and alt_slug != slugs[0]:
            slugs.append(alt_slug)
    
    return slugs[:3]  # Cap at 3 candidates


async def scan_event_page_for_vf(event_url, session):
    """Scan the Ticketmaster event page for VF signup links."""
    try:
        async with session.get(event_url, timeout=aiohttp.ClientTimeout(total=VF_REQUEST_TIMEOUT)) as response:
            if response.status != 200:
                return None
            
            html = await response.text()
            
            # Look for signup.ticketmaster.com links
            signup_match = re.search(r'href=["\']([^"\']*signup\.ticketmaster\.com/[^"\']+)["\']', html, re.IGNORECASE)
            if signup_match:
                vf_url = signup_match.group(1)
                if not vf_url.startswith('http'):
                    vf_url = 'https://' + vf_url.lstrip('/')
                logger.info(f"Found VF link on event page: {vf_url}")
                return vf_url
            
            # Look for "Verified Fan" keywords near links
            vf_keyword_match = re.search(r'verified\s*fan', html, re.IGNORECASE)
            if vf_keyword_match:
                context_start, context_end = max(0, vf_keyword_match.start() - 500), min(len(html), vf_keyword_match.end() + 500)
                context = html[context_start:context_end]
                link_match = re.search(r'href=["\']([^"\']*signup\.ticketmaster\.com/[^"\']+)["\']', context, re.IGNORECASE)
                if link_match:
                    vf_url = link_match.group(1)
                    if not vf_url.startswith('http'):
                        vf_url = 'https://' + vf_url.lstrip('/')
                    logger.info(f"Found VF link via keyword context: {vf_url}")
                    return vf_url
            
            return None
            
    except asyncio.TimeoutError:
        logger.warning(f"Timeout scanning event page: {event_url}")
        return None
    except Exception as e:
        logger.debug(f"Error scanning event page {event_url}: {e}")
        return None


async def check_slug_candidate(slug, session):
    """Check if a candidate slug exists as a VF signup page."""
    vf_url = f"https://signup.ticketmaster.com/{slug}"
    
    try:
        async with session.head(vf_url, timeout=aiohttp.ClientTimeout(total=VF_REQUEST_TIMEOUT), allow_redirects=True) as response:
            if response.status == 200:
                async with session.get(vf_url, timeout=aiohttp.ClientTimeout(total=VF_REQUEST_TIMEOUT)) as get_response:
                    if get_response.status == 200:
                        html = await get_response.text()
                        if re.search(r'verified\s*fan|signup|presale', html, re.IGNORECASE):
                            logger.info(f"Confirmed VF page via slug guess: {vf_url}")
                            return vf_url
            return None
            
    except asyncio.TimeoutError:
        logger.debug(f"Timeout checking slug candidate: {vf_url}")
        return None
    except Exception as e:
        logger.debug(f"Slug candidate {slug} not valid: {e}")
        return None


async def detect_vf(event_url, artist_name):
    """
    Detect VF signup for an event using multi-strategy approach.
    Returns (has_vf: bool, vf_url: str or None)
    """
    if not VF_CHECK_ENABLED:
        return False, None
    
    async with aiohttp.ClientSession() as session:
        # Strategy 1: Scan the event page
        vf_url = await scan_event_page_for_vf(event_url, session)
        if vf_url:
            return True, vf_url
        
        # Strategy 2: Try slug guessing (fallback)
        for slug in normalize_artist_slug(artist_name):
            vf_url = await check_slug_candidate(slug, session)
            if vf_url:
                return True, vf_url
        
        logger.debug(f"No VF detected for event: {event_url}")
        return False, None


async def queue_vf_detection(event_id, event_url, artist_name):
    """Queue VF detection for a specific event and update the database."""
    from config.db_pool import db_pool
    
    try:
        # Check if VF columns exist (backwards compatibility)
        async with db_pool.acquire() as conn:
            has_vf_columns = await conn.fetchval('''
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'events'
                    AND column_name = 'hasvf'
                )
            ''')
            
            if not has_vf_columns:
                logger.debug(f"VF columns not yet migrated, skipping VF detection for event {event_id}")
                return
            
            has_vf, vf_url = await detect_vf(event_url, artist_name)
            
            if has_vf and vf_url:
                await conn.execute('''
                    UPDATE Events 
                    SET hasVF = TRUE, vfUrl = $1, vfDetectedAt = $2
                    WHERE eventID = $3
                ''', vf_url, datetime.now(timezone.utc), event_id)
                logger.info(f"VF detected and saved for event {event_id}: {vf_url}")
            else:
                await conn.execute('''
                    UPDATE Events 
                    SET hasVF = FALSE, vfDetectedAt = $1
                    WHERE eventID = $2
                ''', datetime.now(timezone.utc), event_id)
                
    except Exception as e:
        logger.error(f"Failed to process VF detection for event {event_id}: {e}")


def schedule_vf_check_for_new_event(event_id, event_url, artist_name):
    """Schedule VF detection for a newly stored event (called from store_event)."""
    if not VF_CHECK_ENABLED:
        return
    
    try:
        asyncio.create_task(queue_vf_detection(event_id, event_url, artist_name or ""))
    except Exception as e:
        logger.error(f"Failed to schedule VF detection for event {event_id}: {e}")


async def recheck_recent_events():
    """Periodically recheck recent events for VF signups that may have been added later."""
    from config.db_pool import db_pool
    
    if not VF_CHECK_ENABLED:
        return
    
    try:
        async with db_pool.acquire() as conn:
            # Check if VF columns exist (backwards compatibility)
            has_vf_columns = await conn.fetchval('''
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'events'
                    AND column_name = 'hasvf'
                )
            ''')
            
            if not has_vf_columns:
                logger.debug("VF columns not yet migrated, skipping recheck")
                return
            
            # Find events from the last VF_RECHECK_WINDOW_HOURS hours where:
            # - hasVF is FALSE or NULL
            # - ticketOnsaleStart is in the future
            # - either never checked (vfDetectedAt IS NULL) or checked more than 6 hours ago
            query = '''
                SELECT Events.eventID, Events.url, Artists.name
                FROM Events
                LEFT JOIN Artists ON Events.artistID = Artists.artistID
                WHERE (Events.hasVF = FALSE OR Events.hasVF IS NULL)
                  AND Events.ticketOnsaleStart > NOW()
                  AND Events.ticketOnsaleStart < NOW() + INTERVAL '%s hours'
                  AND (Events.vfDetectedAt IS NULL 
                       OR Events.vfDetectedAt < NOW() - INTERVAL '6 hours')
                LIMIT 50
            ''' % VF_RECHECK_WINDOW_HOURS
            
            events_to_check = await conn.fetch(query)
            
            if events_to_check:
                logger.info(f"Rechecking {len(events_to_check)} events for VF signups")
                
                # Process in batches to avoid overwhelming the system
                for event in events_to_check:
                    await queue_vf_detection(event['eventid'], event['url'], event['name'] or "")
                    await asyncio.sleep(0.5)  # Small delay between checks
                    
    except Exception as e:
        logger.error(f"Error during VF recheck: {e}")

