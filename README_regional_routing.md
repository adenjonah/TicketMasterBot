# European Events Channel Routing

This update adds support for routing European region events to a dedicated Discord channel, separate from the main notable and regular event channels.

## Changes Made

### 1. Environment Configuration
- Added `EUROPEAN_CHANNEL` environment variable to the `.env` file to store the Discord channel ID for European events
- Updated `config.py` to import the new environment variable

### 2. Bot Task Updates
- Modified `notify_events_task()` in `newbot.py` to route events based on region:
  - Notable artist events continue to go to the main channel
  - European region events now go to the European channel
  - All other non-notable events go to the secondary channel

### 3. Event Notification Logic
- Updated `notify_events()` in `tasks/notify_events.py` to accept a `region` parameter
- Added region-based filtering to the database query
- Added region information to event embeds (footer text)
- Set different embed colors based on region (purple for European events)

### 4. Reminder System
- Updated `check_reminders()` in `tasks/check_reminders.py` to handle the European channel
- Modified reminder routing to send European event reminders to the dedicated channel
- Added region information to reminder embeds
- Applied consistent color coding for reminders (matching the event notification colors)

## How It Works

When events are scraped from the Ticketmaster API, they are assigned a region based on the crawler configuration (e.g., 'eu' for Europe). The bot now uses this region information to:

1. Route European events (region = 'eu') to the dedicated European channel
2. Apply special formatting to European events (purple color scheme)
3. Add region information to all event notifications
4. Send reminders to the appropriate channels based on region

## Configuration

To use this feature, make sure your `.env` file includes:

```
EUROPEAN_CHANNEL=your_channel_id
```

Where `your_channel_id` is the Discord channel ID where you want European events to be sent.

## Testing

To test this functionality:
1. Make sure your bot has access to the European channel
2. Set the `region` field to 'eu' for some events in your database
3. Run the bot and verify events are routed correctly

You can manually test this by running the `reset_european_events_direct.py` script which marks all European events as unsent, allowing them to be sent to the European channel on the next notification cycle. 