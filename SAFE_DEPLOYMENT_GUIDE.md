# Safe Deployment Guide with Instant Rollback

This guide provides a safe way to deploy your cleaned-up TicketMasterBot to Heroku with instant rollback capabilities.

## 🚀 Quick Start

1. **Deploy with safety checks:**
   ```bash
   ./safe_deploy.sh <your-app-name>
   ```

2. **Monitor the deployment:**
   ```bash
   ./monitor_deployment.sh <your-app-name>
   ```

3. **Rollback if needed:**
   ```bash
   ./rollback.sh <your-app-name>
   ```

## 📋 Available Heroku Apps

Based on your Heroku account, you have these TicketMaster-related apps:
- `tm-bot-and-crawler-east`
- `tm-crawler-canada` 
- `tm-crawler-comedy`
- `tm-crawler-south-and-mexico`
- `tm-crawler-west`
- `tm-scraper-europe`

## 🛡️ Safety Features

### Safe Deployment (`safe_deploy.sh`)
- ✅ Saves current release version for rollback
- ✅ Enables maintenance mode during deployment
- ✅ Automatic health checks after deployment
- ✅ Auto-rollback if processes fail to start
- ✅ Zero-downtime deployment process

### Instant Rollback (`rollback.sh`)
- ⚡ Instant rollback to previous working release
- 📝 Remembers last known good release
- 🔧 Handles maintenance mode automatically
- ✅ Confirms rollback before executing

### Deployment Monitoring (`monitor_deployment.sh`)
- 📊 Real-time health monitoring
- 🔍 Error detection in logs
- 🏃 Process activity verification
- ⏰ Configurable monitoring duration

## 🎯 Step-by-Step Deployment

### 1. Choose Your Target App
First, decide which app to deploy to. For a bot + crawler setup, `tm-bot-and-crawler-east` seems appropriate.

### 2. Deploy Safely
```bash
./safe_deploy.sh tm-bot-and-crawler-east
```

This will:
- Save your current release for rollback
- Enable maintenance mode
- Deploy your cleaned code
- Check if processes start correctly
- Disable maintenance mode
- Show you monitoring commands

### 3. Monitor the Deployment
```bash
./monitor_deployment.sh tm-bot-and-crawler-east 300
```

This monitors for 5 minutes (300 seconds) and shows:
- Dyno status
- Recent errors
- Process activity

### 4. Rollback if Needed
If anything goes wrong:
```bash
./rollback.sh tm-bot-and-crawler-east
```

## 🔍 What to Watch For

### ✅ Good Signs
- Both `bot` and `crawler` processes show "up"
- Logs show "Bot ready" and "Crawler initialized"
- No error messages in recent logs
- Event notifications continue working

### ❌ Warning Signs
- Processes stuck in "starting" state
- Error messages about missing modules
- Database connection errors
- No activity from bot or crawler

## 🆘 Emergency Procedures

### Instant Rollback
```bash
./rollback.sh <app-name>
```

### Check Current Status
```bash
heroku ps -a <app-name>
heroku logs -a <app-name> --tail
```

### Manual Maintenance Mode
```bash
heroku maintenance:on -a <app-name>   # Enable
heroku maintenance:off -a <app-name>  # Disable
```

## 🎛️ Environment Variables

Make sure these are set in your Heroku app:
```bash
heroku config -a <app-name>
```

Required variables:
- `DATABASE_URL` (should be auto-set)
- `DISCORD_BOT_TOKEN`
- `TICKETMASTER_API_KEY`
- `DISCORD_CHANNEL_ID`
- `DISCORD_CHANNEL_ID_TWO`
- Region-specific variables based on your app

## 📝 Post-Deployment Checklist

After successful deployment:
- [ ] Both bot and crawler processes are running
- [ ] Bot responds to Discord commands
- [ ] Crawler is fetching events
- [ ] Database connections working
- [ ] No errors in logs for 10+ minutes
- [ ] Event notifications still working

## 🔧 Troubleshooting

### If deployment fails:
1. Check the error message in terminal
2. The script will auto-rollback failed deployments
3. Check `heroku logs -a <app-name>` for details

### If app becomes unresponsive:
1. Run `./rollback.sh <app-name>` immediately
2. Check logs to identify the issue
3. Fix the issue locally before redeploying

### If rollback fails:
1. Check Heroku dashboard for release history
2. Use: `heroku rollback v<number> -a <app-name>`
3. Contact Heroku support if needed

Remember: **Better safe than sorry!** Use the monitoring script and don't hesitate to rollback if anything seems off.
