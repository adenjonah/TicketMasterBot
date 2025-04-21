#!/bin/bash
set -e

echo "=== European Events Channel Fix Deployment ==="
echo "This script will deploy the fix to make European events go to their own channel."

# Make sure we have the Heroku CLI and are logged in
if ! command -v heroku &> /dev/null; then
    echo "Error: Heroku CLI is not installed. Please install it first."
    exit 1
fi

# Get app name
read -p "Enter your Heroku app name: " APP_NAME
echo "Using app: $APP_NAME"

# 1. Set the EUROPEAN_CHANNEL config var
echo -e "\n1. Setting EUROPEAN_CHANNEL environment variable..."
read -p "Enter the Discord channel ID for European events: " EUROPEAN_CHANNEL

if [ -z "$EUROPEAN_CHANNEL" ]; then
    # Get the secondary channel ID as fallback
    SECONDARY_CHANNEL=$(heroku config:get DISCORD_CHANNEL_ID_TWO -a $APP_NAME)
    EUROPEAN_CHANNEL=$SECONDARY_CHANNEL
    echo "Using secondary channel ID as fallback: $EUROPEAN_CHANNEL"
fi

heroku config:set EUROPEAN_CHANNEL=$EUROPEAN_CHANNEL -a $APP_NAME
echo "EUROPEAN_CHANNEL environment variable set."

# 2. Deploy the code changes
echo -e "\n2. Deploying code changes..."
git add .
git commit -m "Fix European events channel routing"
git push heroku main
echo "Code deployed to Heroku."

# 3. Run SQL script to fix database
echo -e "\n3. Running SQL script to fix European events..."
heroku pg:psql -a $APP_NAME < fix_eu_events.sql
echo "Database updated."

# 4. Restart the app
echo -e "\n4. Restarting the app..."
heroku restart -a $APP_NAME
echo "App restarted."

echo -e "\nDeployment completed!"
echo "European events should now be routed to channel ID: $EUROPEAN_CHANNEL"
echo "You can verify by checking the logs: heroku logs -a $APP_NAME --tail" 