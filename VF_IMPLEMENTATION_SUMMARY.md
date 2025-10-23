# Verified Fan (VF) Signup Detection - Implementation Summary

## ✅ Implementation Complete

All components of the VF detection feature have been successfully implemented and all files comply with the <200 line requirement.

### File Line Counts
- **dbEditor.py**: 199 lines ✓
- **vf_checker.py**: 194 lines ✓
- **notifier.py**: 113 lines ✓
- **main.py**: 88 lines ✓

### ✅ Backwards Compatibility
All changes are **100% backwards compatible**. See `BACKWARDS_COMPATIBILITY.md` for detailed analysis.

## Changes Made

### 1. Database Schema (`dbEditor.py`)
- Added three new columns to the `Events` table:
  - `hasVF` (INTEGER DEFAULT 0): Flag indicating if VF signup exists
  - `vfUrl` (TEXT): URL to the VF signup page
  - `vfDetectedAt` (TEXT): ISO8601 timestamp of when VF was detected
- Added index `idx_events_hasVF` for efficient VF queries
- Migration is safe and guarded with `PRAGMA table_info` checks
- Integrated VF detection queueing in `store_event()` for new events

### 2. VF Detection Module (`vf_checker.py` - NEW FILE)
**Core Functions:**
- `normalize_artist_slug()`: Generates candidate URL slugs from artist names
- `scan_event_page_for_vf()`: Scrapes Ticketmaster event pages for VF signup links
- `check_slug_candidate()`: Validates guessed VF URLs via HEAD/GET requests
- `detect_vf()`: Multi-strategy detection (page scan → slug guessing)
- `queue_vf_detection()`: Async detection and database update
- `schedule_vf_check_for_new_event()`: Entry point called from `store_event()`
- `recheck_recent_events()`: Periodic batch recheck of recent events

**Detection Strategy:**
1. **Primary**: Scan event page HTML for `signup.ticketmaster.com` links or "Verified Fan" keywords
2. **Fallback**: Generate slug candidates (e.g., "Cardi B" → "cardib") and validate via HTTP requests
3. **Short-circuiting**: Stop at first positive detection

**Configuration (via .env):**
- `VF_CHECK_ENABLED=true` (default: true)
- `VF_RECHECK_WINDOW_HOURS=48` (default: 48)
- Timeout: 10 seconds per HTTP request

### 3. Discord Notifications (`notifier.py`)
- Updated query to fetch `hasVF` and `vfUrl` columns
- Modified embed description to append VF link when available:
  ```
  **Verified Fan**: https://signup.ticketmaster.com/artistname
  ```
- VF info is displayed inline (no separate alert message)

### 4. Periodic Recheck (`main.py`)
- Added `recheck_vf_signups()` task loop (runs every 10 minutes)
- Imports `recheck_recent_events()` from `vf_checker`
- Rechecks events from last 48 hours where:
  - `hasVF = 0` or not yet checked
  - `ticketOnsaleStart` is in the future
  - Last check was >6 hours ago (or never checked)
- Prevents missing VF signups added after event creation

## How It Works

### New Event Flow
1. Ticketmaster API returns new event → `store_event()` inserts into DB
2. `schedule_vf_check_for_new_event()` queues async VF detection task
3. VF checker scrapes event page and/or tries slug guessing
4. Database updated with `hasVF` flag and `vfUrl` (if found)
5. When Discord notification is sent, VF link is included in embed

### Periodic Recheck Flow
1. Every 10 minutes, `recheck_vf_signups()` runs
2. Queries recent events (last 48h) with no VF or stale checks
3. Re-runs VF detection on up to 50 events per batch
4. Updates database with new findings
5. Next Discord notification will show newly discovered VF links

## Testing Recommendations

### Manual Testing
1. **Database migration**: Restart the bot and check `logs/db_log.log` for successful column additions
2. **VF detection**: Monitor `logs/api_log.log` for VF detection attempts and results
3. **Discord display**: Wait for a new event with VF to be posted; verify the VF link appears in the embed

### Test Cases
- Event with VF link directly on event page (e.g., major artist)
- Event requiring slug guessing (e.g., "Cardi B" → "cardib")
- Event with no VF (verify `hasVF=0` is set correctly)
- Late-added VF (create event without VF, add VF later, verify recheck finds it)

## Environment Variables (Optional)

Add to `.env` if you want to customize:
```env
VF_CHECK_ENABLED=true
VF_RECHECK_WINDOW_HOURS=48
```

## Notes

- **Low resource usage**: Detection is async and non-blocking; won't slow down event ingestion
- **Graceful degradation**: If VF detection fails, events are still processed normally
- **No manual maintenance**: All VF URLs are discovered automatically
- **Time-sensitive**: Recheck mechanism catches VF signups added after initial event creation
- **Modular**: All VF logic isolated in `vf_checker.py` for easy maintenance

## Potential Enhancements (Future)

- Add manual VF URL override table for artists with non-standard slugs
- Expose VF stats via Discord command (e.g., `!vfstats`)
- Send special alert to a dedicated channel when VF is newly detected
- Track VF signup open/close times

