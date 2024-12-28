# Ticketmaster Bot

Ticketmaster Bot is a Discord bot designed to alert users every time a new event becomes available on Ticketmaster. Built for a ticket resale company based in NYC, it ensures users receive timely updates about upcoming events and provides powerful tools for managing event notifications.

## Features
- **Event Alerts**: Automatically notifies a Discord server when new events are added to Ticketmaster.
  <img width="400" alt="alert example" src="https://github.com/user-attachments/assets/4e758a2f-7784-466c-bc24-0f7549195267" />
- **User Commands**:
  - `!next`: Displays events with tickets going on sale next.\
    <img width="400" alt="!next example" src="https://github.com/user-attachments/assets/96ae5c98-b7ab-4bd3-928f-1d47077d17f4" />
  - `!addartist <artistID>`: Marks an artist as notable, sending their events to a dedicated high-profile channel.\
    <img width="400" alt="!addartist example" src="https://github.com/user-attachments/assets/6858b56d-3e46-43ec-8a13-bea9f698b6f4" />

- **API Crawlers**: Continuously fetch new events from Ticketmaster’s API for four regions in North America.

## Tech Stack
- **Programming Language**: Python
- **Database**: PostgreSQL
- **Hosting**: [Heroku](https://www.heroku.com/)
- **APIs**:
  - [Ticketmaster Discovery API](https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/)
  - [Discord API](https://discord.com/developers/docs/reference)
- **Deployment**: CI/CD pipeline auto-deploys updates to Heroku from GitHub.

## Architecture

The project is composed of two key components:
1. **API Crawlers**: Four Python scripts, each assigned to a specific North American region, poll the Ticketmaster API every minute and store new events in a PostgreSQL database.
2. **Bot Script**: The Discord bot retrieves unsent events from the database, posts them in designated channels, and handles user commands.\
   Example request:\
   `https://app.ticketmaster.com/discovery/v2/events?apikey=YOUR_API_KEY&source=ticketmaster&locale=*&size=199&page=1&onsaleStartDateTime=2024-12-27T00:00:00Z&classificationId=CONCERTS&onsaleOnAfterStartDate=DATE&sort=onSaleStartDate,asc&latlong=CENTER&radius=DIST&unit=miles`

## Challenges & Solutions
- **Rate Limits**: The Ticketmaster API enforces a rate limit of 1000 events returned per query.\
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/ea1f8666-d388-46b4-a3a7-28d3948d0604" />

  - **Solution**: Run five separate Heroku servers (four crawlers and one bot) to distribute requests and avoid exceeding rate limits.\
     <img width="400" alt="North American Regions" src="https://github.com/user-attachments/assets/4c276389-ebde-4274-9292-27aa9c9228e9" />
- **Storage Efficiency**: Optimized database structure to handle high-frequency updates and large datasets effectively.\
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/cca06550-89bf-46c9-8ed6-492b7699ff54" />


## Future Development
- Expand coverage to include events from other continents.
- Optimize database queries for better performance.
- Add new Discord commands and enhance logging mechanisms.
- Improve bot scalability and error handling.

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/adenjonah/TicketMasterBot.git
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your environment variables:
   - [TICKETMASTER_API_KEY](https://developer.ticketmaster.com/products-and-docs/tutorials/events-search/search_events_with_discovery_api.html)
   - [DISCORD_CHANNEL_ID](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID)
   - [DISCORD_CHANNEL_ID_TWO](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID)
   - [DISCORD_BOT_TOKEN](https://discordpy.readthedocs.io/en/stable/discord.html)
   - [DATABASE_URL](https://www.prisma.io/dataguide/postgresql/setting-up-a-local-postgresql-database)
   - DEBUG_LOGS (1 if on, 0 if off)
   - CENTER_POINT (long, lat of the zone you want to crawl)
   - RADIUS (in miles)
   - UNIT=miles
   - REDIRECT_URI=http://localhost \
    Example `.env`
     ```
      TICKETMASTER_API_KEY='P7v8iurhq2a9r84o84irqo2uhq'
      DISCORD_BOT_TOKEN='MKSEalfnj87yBbE8.GHQ_Cx.KHGbkFHBFYUBFI-ri_XY'
      DISCORD_CHANNEL_ID='3795263749501923847509'
      DISCORD_CHANNEL_ID_TWO='73425974283745975392785'
      REDIRECT_URI='http://localhost'
      DATABASE_URL='postgres://7stfuastdg88:utaf8sfiasgig9asiygfouasgf0.cluster-s78syag9.us-east-2.rds.amazonaws.com:26739/aiysgfyasg98f'
      DEBUG_LOGS='1'
      CENTER_POINT=43.89789,-72.84782
      RADIUS=685
      UNIT=miles
     ```
4. Deploy to Heroku or run locally using the provided scripts (run newbot.py and crawler.py at the same time).
## Usage
- Add the bot to your [Discord server](https://discordjs.guide/preparations/adding-your-bot-to-servers.html#bot-invite-links).
- Configure the database with your Ticketmaster API regions and preferences via environment variables.
- Start receiving real-time alerts and use commands like `!next` and `!addartist` to interact with the bot.
## Repository
Find the source code and deployment instructions [here](https://github.com/adenjonah/TicketMasterBot).
## About the Developer
This project was developed by **adenjonah** as a solo initiative, requiring approximately 30 hours of work, including iterations. For inquiries or collaboration, feel free to reach out via GitHub or the contacts in my profile.
