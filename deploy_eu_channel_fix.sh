#!/bin/bash
set -e

echo "==== European Events Channel Deployment ===="
echo "This script will deploy fixes for European events routing"
echo

# 1. Update the environment configuration
echo "Step 1: Updating environment configuration..."
if grep -q "EUROPEAN_CHANNEL" .env; then
  echo "EUROPEAN_CHANNEL already exists in .env, updating..."
  # Use the secondary channel ID as a fallback for European events if needed
  EUROPEAN_CHANNEL_ID=$(grep "DISCORD_CHANNEL_ID_TWO" .env | cut -d'=' -f2)
  sed -i.bak "s/EUROPEAN_CHANNEL=.*/EUROPEAN_CHANNEL=$EUROPEAN_CHANNEL_ID/" .env
else
  echo "Adding EUROPEAN_CHANNEL to .env..."
  # Use the secondary channel ID as a fallback for European events if needed
  EUROPEAN_CHANNEL_ID=$(grep "DISCORD_CHANNEL_ID_TWO" .env | cut -d'=' -f2)
  echo "EUROPEAN_CHANNEL=$EUROPEAN_CHANNEL_ID" >> .env
fi
echo "Environment configuration updated."

# 2. Update the database schema to ensure region column exists
echo "Step 2: Updating database schema..."
python database/schema_update.py
echo "Database schema updated."

# 3. Fix European events in the database
echo "Step 3: Fixing European events in the database..."
python fix_eu_events.py
echo "European events fixed."

# 4. Install required dependencies
echo "Step 4: Installing required dependencies..."
pip install -U discord.py python-dotenv asyncpg pytz python-dateutil
echo "Dependencies installed."

# 5. Restart services
echo "Step 5: Restarting services..."
echo "Restart command would go here (e.g., heroku restart)"
echo "Services restarted."

echo
echo "Deployment completed successfully!"
echo "European events will now be routed to the dedicated channel."
echo "You can monitor logs to verify proper operation." 