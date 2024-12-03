import logging
import os
from datetime import datetime, timezone

# Load DEBUG flag from the environment
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Set logging level based on DEBUG flag
logging_level = logging.DEBUG if DEBUG else logging.INFO

# Configure logging
logging.basicConfig(level=logging_level, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ticketmaster_bot")  # Use a global logger name