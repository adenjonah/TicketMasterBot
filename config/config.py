import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Discord Configuration
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID', 0))  # Main notable events channel
DISCORD_CHANNEL_ID_TWO = int(os.getenv('DISCORD_CHANNEL_ID_TWO', 0))  # Secondary channel for all unsent events
EUROPEAN_CHANNEL = int(os.getenv('EUROPEAN_CHANNEL', 0))  # Channel for European events


DEBUG_LOGS = os.getenv('DEBUG_LOGS')
# Ticketmaster API Key
TICKETMASTER_API_KEY = os.getenv('TICKETMASTER_API_KEY')

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL')

CENTER_POINT = os.getenv('CENTER_POINT')
RADIUS = os.getenv('RADIUS')

#General
REDIRECT_URI='http://localhost'
UNIT='miles'

REGION=os.getenv('REGION')
# Default API parameters
CLASSIFICATION_ID='KZFzniwnSyZfZ7v7nJ'
GENRE_ID=''

if REGION == 'east':
    CENTER_POINT='43.58785,-64.72599'
    RADIUS='950'
elif REGION == 'north': 
    CENTER_POINT='62.41709,-108.42529'
    RADIUS='1717'
elif REGION == 'south':
    CENTER_POINT='29.74590,-92.86707'
    RADIUS='1094' 
elif REGION == 'west': 
    CENTER_POINT='15.42661,-133.61964'
    RADIUS='2171'
elif REGION == 'europe': 
    CENTER_POINT='47.37116,8.50755'
    RADIUS='1200'
elif REGION == 'comedy':
    CENTER_POINT='44.69209,-99.95477'
    RADIUS='3016'
    CLASSIFICATION_ID='KZFzniwnSyZfZ7v7na'
    GENRE_ID='KnvZfZ7vAe1'
elif REGION == 'theater':
    CENTER_POINT='44.69209,-99.95477'
    RADIUS='3016'
    CLASSIFICATION_ID='KZFzniwnSyZfZ7v7na'
    GENRE_ID='KnvZfZ7v7l1'
elif REGION == 'film':
    CENTER_POINT='44.69209,-99.95477'
    RADIUS='3016'
    CLASSIFICATION_ID='KZFzniwnSyZfZ7v7nn'  # Film
    GENRE_ID='KnvZfZ7vAka'  # Miscellaneous Film

# Validation to ensure critical environment variables are set
if not DISCORD_BOT_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN is not set in the environment variables.")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the environment variables.")

if not TICKETMASTER_API_KEY:
    raise ValueError("TICKETMASTER_API_KEY is not set in the environment variables.")