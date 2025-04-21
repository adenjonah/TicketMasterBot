# European Events Channel Fix - Deployment Guide

This guide explains how to deploy the fix for routing European events to a dedicated Discord channel.

## The Issue

The bot is currently not sending European events (region='eu') to their dedicated channel because:

1. The EUROPEAN_CHANNEL environment variable is not set in Heroku
2. If no European channel is configured, events with region='eu' are skipped entirely

## Deployment Options

### Option 1: Automated Deployment Script

Use the provided deployment script to automatically apply all fixes:

```bash
./deploy_eu_fix.sh
```

This script will:
1. Set the EUROPEAN_CHANNEL environment variable in Heroku
2. Deploy your code changes to Heroku
3. Run SQL scripts to fix European events in the database
4. Restart the app

### Option 2: Manual Deployment

If the automated script doesn't work, follow these steps manually:

1. **Set the environment variable:**
   ```bash
   heroku config:set EUROPEAN_CHANNEL=YOUR_CHANNEL_ID -a YOUR_APP_NAME
   ```
   
   If you don't have a dedicated European channel, use your secondary channel instead:
   ```bash
   heroku config:set EUROPEAN_CHANNEL=$(heroku config:get DISCORD_CHANNEL_ID_TWO -a YOUR_APP_NAME) -a YOUR_APP_NAME
   ```

2. **Fix the database:**
   ```bash
   heroku pg:psql -a YOUR_APP_NAME < fix_eu_events.sql
   ```

3. **Push code changes:**
   ```bash
   git add .
   git commit -m "Fix European events channel routing"
   git push heroku main
   ```

4. **Restart the app:**
   ```bash
   heroku restart -a YOUR_APP_NAME
   ```

## Verifying the Fix

After deployment, check the logs to verify the fix is working:

```bash
heroku logs -a YOUR_APP_NAME --tail
```

Look for these indicators of success:
1. `Checking for European events to send to channel ID: [YOUR_CHANNEL_ID]` - Shows that European events are now being checked
2. `Found X unsent European events with exact match 'eu'` - Shows that EU events are being found
3. `Fetched X unsent events to notify for region=eu` - Shows that EU events are being sent

## What Changed?

1. **Fallback Channel Logic:** The bot now uses the secondary channel as a fallback if no European channel is configured, ensuring European events are never skipped.

2. **SQL Query Fixes:** Fixed SQL errors in the count query and improved region filtering.

3. **Database Fixes:** Ensured consistent lowercase 'eu' for all European events.

4. **Better Logging:** Added diagnostic queries to help identify region capitalization issues.

## Troubleshooting

If events still aren't showing up:

1. Check that there are unsent European events in the database:
   ```bash
   heroku pg:psql -a YOUR_APP_NAME -c "SELECT COUNT(*) FROM Events WHERE sentToDiscord = FALSE AND LOWER(region) = 'eu';"
   ```

2. Make sure the SQL region check is working by checking capitalization:
   ```bash
   heroku pg:psql -a YOUR_APP_NAME -c "SELECT region, COUNT(*) FROM Events GROUP BY region;"
   ```

3. Ensure the bot has permission to send messages to the European channel 