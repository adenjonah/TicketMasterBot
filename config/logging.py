import logging
from config.config import DEBUG_LOGS  # Import DEBUG from config.py

# Set logging level based on DEBUG flag
logging_level = logging.DEBUG if DEBUG_LOGS == '1' else logging.INFO

# Configure logging
logging.basicConfig(level=logging_level, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ticketmaster_bot")