import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Discord Configuration
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID', 0))  # Main notable events channel
DISCORD_CHANNEL_ID_TWO = int(os.getenv('DISCORD_CHANNEL_ID_TWO', 0))  # Secondary channel for all unsent events

# Ticketmaster API Key
TICKETMASTER_API_KEY = os.getenv('TICKETMASTER_API_KEY')

# Redirect URI for OAuth or Webhooks
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost')  # Default to localhost if not set

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL')

# Testing
DEBUG = os.getenv("DEBUG", "false").lower()

# Validation to ensure critical environment variables are set
if not DISCORD_BOT_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN is not set in the environment variables.")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the environment variables.")

if not TICKETMASTER_API_KEY:
    raise ValueError("TICKETMASTER_API_KEY is not set in the environment variables.")