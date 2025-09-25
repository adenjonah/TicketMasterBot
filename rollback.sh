#!/bin/bash

# Instant Rollback Script
# Usage: ./rollback.sh <app-name> [release-version]

set -e

APP_NAME=$1
RELEASE_VERSION=$2

if [ -z "$APP_NAME" ]; then
    echo "Usage: $0 <heroku-app-name> [release-version]"
    exit 1
fi

echo "🔄 Starting rollback for $APP_NAME..."

# If no release version specified, use the last known good release
if [ -z "$RELEASE_VERSION" ]; then
    if [ -f ".last_known_good_release" ]; then
        RELEASE_VERSION=$(cat .last_known_good_release | cut -d'v' -f2)
        echo "📖 Using last known good release: v$RELEASE_VERSION"
    else
        # Get previous release
        RELEASE_VERSION=$(heroku releases -a $APP_NAME --json | jq -r '.[1].version')
        echo "📖 Using previous release: v$RELEASE_VERSION"
    fi
fi

echo "⚠️  About to rollback $APP_NAME to release v$RELEASE_VERSION"
read -p "Are you sure? (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Rollback cancelled."
    exit 0
fi

# Enable maintenance mode
echo "🔧 Enabling maintenance mode..."
heroku maintenance:on -a $APP_NAME

# Perform rollback
echo "🔄 Rolling back to v$RELEASE_VERSION..."
if heroku rollback v$RELEASE_VERSION -a $APP_NAME; then
    echo "✅ Rollback successful!"
    
    # Wait a moment for the rollback to take effect
    sleep 5
    
    # Check processes
    echo "🔍 Checking process status..."
    heroku ps -a $APP_NAME
    
    # Disable maintenance mode
    echo "🟢 Disabling maintenance mode..."
    heroku maintenance:off -a $APP_NAME
    
    echo ""
    echo "✅ Rollback complete!"
    echo "📊 Monitor logs: heroku logs -a $APP_NAME --tail"
    
    # Update last known good release
    echo "Release v$RELEASE_VERSION" > .last_known_good_release
    
else
    echo "❌ Rollback failed!"
    heroku maintenance:off -a $APP_NAME
    exit 1
fi
