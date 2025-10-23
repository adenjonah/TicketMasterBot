import aiohttp
import asyncio
import sqlite3
import logging
import re
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
VF_CHECK_ENABLED = os.getenv('VF_CHECK_ENABLED', 'true').lower() == 'true'
VF_RECHECK_WINDOW_HOURS = int(os.getenv('VF_RECHECK_WINDOW_HOURS', '48'))

# Set up VF-specific logging
vf_logger = logging.getLogger("vfLogger")
vf_logger.setLevel(logging.INFO)
vf_handler = logging.FileHandler("logs/api_log.log")
vf_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
vf_logger.addHandler(vf_handler)

# Database connection
conn = sqlite3.connect('events.db', check_same_thread=False)
c = conn.cursor()

# Rate limiting and timeout settings
VF_REQUEST_TIMEOUT = 10  # seconds
VF_MAX_RETRIES = 2


def normalize_artist_slug(artist_name):
    """Generate candidate slugs from artist name."""
    if not artist_name:
        return []
    slugs = [re.sub(r'[^a-z0-9]', '', artist_name.lower())]
    if artist_name.lower().startswith('the '):
        alt_slug = re.sub(r'[^a-z0-9]', '', artist_name[4:].lower())
        if alt_slug and alt_slug != slugs[0]:
            slugs.append(alt_slug)
    return slugs[:3]


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
                vf_logger.info(f"Found VF link on event page: {vf_url}")
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
                    vf_logger.info(f"Found VF link via keyword context: {vf_url}")
                    return vf_url
            return None
    except asyncio.TimeoutError:
        vf_logger.warning(f"Timeout scanning event page: {event_url}")
        return None
    except Exception as e:
        vf_logger.error(f"Error scanning event page {event_url}: {e}")
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
                            vf_logger.info(f"Confirmed VF page via slug guess: {vf_url}")
                            return vf_url
            return None
    except asyncio.TimeoutError:
        vf_logger.warning(f"Timeout checking slug candidate: {vf_url}")
        return None
    except Exception as e:
        vf_logger.debug(f"Slug candidate {slug} not valid: {e}")
        return None


async def detect_vf(event_url, artist_name):
    """Detect VF signup for an event using multi-strategy approach. Returns (has_vf: bool, vf_url: str or None)"""
    if not VF_CHECK_ENABLED:
        return False, None
    async with aiohttp.ClientSession() as session:
        vf_url = await scan_event_page_for_vf(event_url, session)
        if vf_url:
            return True, vf_url
        for slug in normalize_artist_slug(artist_name):
            vf_url = await check_slug_candidate(slug, session)
            if vf_url:
                return True, vf_url
        vf_logger.debug(f"No VF detected for event: {event_url}")
        return False, None


async def queue_vf_detection(event_id, event_url, artist_name):
    """Queue VF detection for a specific event and update the database."""
    try:
        # Check if VF columns exist (backwards compatibility)
        c.execute("PRAGMA table_info(Events)")
        existing_columns = {row[1] for row in c.fetchall()}
        if 'hasVF' not in existing_columns or 'vfUrl' not in existing_columns:
            vf_logger.warning(f"VF columns not yet migrated, skipping VF detection for event {event_id}")
            return
        
        has_vf, vf_url = await detect_vf(event_url, artist_name)
        if has_vf and vf_url:
            c.execute('UPDATE Events SET hasVF = 1, vfUrl = ?, vfDetectedAt = ? WHERE eventID = ?',
                      (vf_url, datetime.now(timezone.utc).isoformat(), event_id))
            conn.commit()
            vf_logger.info(f"VF detected and saved for event {event_id}: {vf_url}")
        else:
            c.execute('UPDATE Events SET hasVF = 0, vfDetectedAt = ? WHERE eventID = ?',
                      (datetime.now(timezone.utc).isoformat(), event_id))
            conn.commit()
    except Exception as e:
        vf_logger.error(f"Failed to process VF detection for event {event_id}: {e}")


def schedule_vf_check_for_new_event(event_id, event_url, artist_name):
    """Schedule VF detection for a newly stored event (called from store_event)."""
    if not VF_CHECK_ENABLED:
        return
    try:
        asyncio.create_task(queue_vf_detection(event_id, event_url, artist_name or ""))
    except Exception as e:
        vf_logger.error(f"Failed to schedule VF detection for event {event_id}: {e}")


async def recheck_recent_events():
    """Periodically recheck recent events for VF signups that may have been added later."""
    if not VF_CHECK_ENABLED:
        return
    
    try:
        # Check if VF columns exist (backwards compatibility)
        c.execute("PRAGMA table_info(Events)")
        existing_columns = {row[1] for row in c.fetchall()}
        if 'hasVF' not in existing_columns or 'vfUrl' not in existing_columns:
            vf_logger.debug("VF columns not yet migrated, skipping recheck")
            return
        
        # Find events from the last VF_RECHECK_WINDOW_HOURS hours where:
        # - hasVF is 0 or NULL
        # - ticketOnsaleStart is in the future
        # - either never checked (vfDetectedAt IS NULL) or checked more than 6 hours ago
        query = '''
            SELECT eventID, url, Artists.name
            FROM Events
            LEFT JOIN Artists ON Events.artistID = Artists.artistID
            WHERE (Events.hasVF = 0 OR Events.hasVF IS NULL)
              AND datetime(Events.ticketOnsaleStart) > datetime('now')
              AND datetime(Events.ticketOnsaleStart) < datetime('now', '+' || ? || ' hours')
              AND (Events.vfDetectedAt IS NULL 
                   OR datetime(Events.vfDetectedAt) < datetime('now', '-6 hours'))
            LIMIT 50
        '''
        
        c.execute(query, (VF_RECHECK_WINDOW_HOURS,))
        events_to_check = c.fetchall()
        
        if events_to_check:
            vf_logger.info(f"Rechecking {len(events_to_check)} events for VF signups")
            
            # Process in batches to avoid overwhelming the system
            for event_id, event_url, artist_name in events_to_check:
                await queue_vf_detection(event_id, event_url, artist_name or "")
                await asyncio.sleep(0.5)  # Small delay between checks
                
    except Exception as e:
        vf_logger.error(f"Error during VF recheck: {e}")

