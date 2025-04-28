import logging
import os
from config.config import DEBUG_LOGS  # Import DEBUG from config.py

# Set logging level based on DEBUG flag
logging_level = logging.DEBUG if DEBUG_LOGS == '1' else logging.INFO

# Configure root logging with minimal output in production
logging.basicConfig(
    level=logging_level, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    # In production mode, only show WARNING and above for most loggers
    # to reduce noise from third-party libraries
    handlers=[
        logging.StreamHandler()
    ]
)

# Set up our specific logger with appropriate levels
logger = logging.getLogger("ticketmaster_bot")
logger.setLevel(logging_level)

# Only log errors from discord.py and other libraries in production
if DEBUG_LOGS != '1':
    # Set higher logging threshold for noisy libraries
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    
    # Disable propagation of our logger to reduce duplicate logs
    logger.propagate = False