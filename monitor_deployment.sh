#!/bin/bash

# Deployment Monitoring Script
# Usage: ./monitor_deployment.sh <app-name> [duration-in-seconds]

APP_NAME=$1
DURATION=${2:-300}  # Default 5 minutes

if [ -z "$APP_NAME" ]; then
    echo "Usage: $0 <heroku-app-name> [duration-in-seconds]"
    exit 1
fi

echo "📊 Monitoring $APP_NAME for $DURATION seconds..."
echo "Press Ctrl+C to stop monitoring"

# Function to check app health
check_health() {
    echo "=== Health Check at $(date) ==="
    
    # Check dyno status
    echo "🔍 Dyno Status:"
    heroku ps -a $APP_NAME
    
    # Check recent logs for errors
    echo ""
    echo "📝 Recent Logs (last 20 lines):"
    heroku logs -a $APP_NAME -n 20 | grep -E "(ERROR|WARN|FATAL|Exception|failed)" || echo "No recent errors found"
    
    # Check if bot/crawler processes are responding
    echo ""
    echo "🏃 Process Activity:"
    heroku logs -a $APP_NAME -n 50 | grep -E "(Bot ready|Crawler initialized|Event notification|event fetch)" | tail -5 || echo "No recent process activity"
    
    echo ""
    echo "----------------------------------------"
}

# Initial health check
check_health

# Monitor for specified duration
END_TIME=$(($(date +%s) + $DURATION))

while [ $(date +%s) -lt $END_TIME ]; do
    sleep 30
    check_health
done

echo ""
echo "✅ Monitoring complete!"
echo "🔄 If issues detected, run: ./rollback.sh $APP_NAME"
