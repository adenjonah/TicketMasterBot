#!/bin/bash

# Safe Heroku Deployment Script with Instant Rollback
# Usage: ./safe_deploy.sh <app-name>

set -e  # Exit on any error

APP_NAME=$1
if [ -z "$APP_NAME" ]; then
    echo "Usage: $0 <heroku-app-name>"
    echo "Available apps:"
    heroku apps | grep -E "tm-|discord"
    exit 1
fi

echo "🚀 Starting safe deployment to $APP_NAME..."

# Check if app exists
if ! heroku apps:info -a $APP_NAME >/dev/null 2>&1; then
    echo "❌ App $APP_NAME not found!"
    exit 1
fi

# Add heroku remote if not exists
if ! git remote get-url heroku >/dev/null 2>&1; then
    echo "📡 Adding Heroku remote..."
    heroku git:remote -a $APP_NAME
fi

# Get current release info for rollback
echo "💾 Getting current release info for potential rollback..."
CURRENT_RELEASE=$(heroku releases -a $APP_NAME --json | jq -r '.[0].version')
echo "Current release: v$CURRENT_RELEASE"

# Create a pre-deployment backup/snapshot
echo "📸 Creating pre-deployment snapshot..."
echo "Release v$CURRENT_RELEASE" > .last_known_good_release

# Check current app health
echo "🔍 Checking current app health..."
heroku ps -a $APP_NAME

# Stage all changes
echo "📦 Staging changes..."
git add .

# Check if there are any changes to commit
if git diff --staged --quiet; then
    echo "⚠️  No changes to deploy!"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
else
    # Commit changes
    echo "📝 Committing changes..."
    git commit -m "Deploy: $(date '+%Y-%m-%d %H:%M:%S') - Safe deployment with rollback capability"
fi

# Deploy with maintenance mode for zero-downtime
echo "🔧 Enabling maintenance mode for safe deployment..."
heroku maintenance:on -a $APP_NAME

# Deploy
echo "🚀 Deploying to Heroku..."
if git push heroku main; then
    echo "✅ Code deployment successful!"
    
    # Wait for release to complete
    echo "⏳ Waiting for release to complete..."
    sleep 10
    
    # Check if processes are running
    echo "🔍 Checking process status..."
    if heroku ps -a $APP_NAME | grep -q "up"; then
        echo "✅ Processes are running!"
        
        # Disable maintenance mode
        echo "🟢 Disabling maintenance mode..."
        heroku maintenance:off -a $APP_NAME
        
        # Get new release version
        NEW_RELEASE=$(heroku releases -a $APP_NAME --json | jq -r '.[0].version')
        echo "🎉 Deployment successful! New release: v$NEW_RELEASE"
        
        # Save successful deployment info
        echo "Release v$NEW_RELEASE deployed at $(date)" > .last_successful_deploy
        
        echo ""
        echo "🔍 Quick health check - checking logs for any immediate errors..."
        timeout 30s heroku logs -a $APP_NAME --tail | head -20 || true
        
        echo ""
        echo "✅ Deployment complete!"
        echo "📊 Monitor logs: heroku logs -a $APP_NAME --tail"
        echo "🔄 Rollback command: ./rollback.sh $APP_NAME"
        
    else
        echo "❌ Processes failed to start properly!"
        echo "🔄 Initiating automatic rollback..."
        heroku rollback v$CURRENT_RELEASE -a $APP_NAME
        heroku maintenance:off -a $APP_NAME
        exit 1
    fi
else
    echo "❌ Deployment failed!"
    echo "🔄 Disabling maintenance mode..."
    heroku maintenance:off -a $APP_NAME
    exit 1
fi
