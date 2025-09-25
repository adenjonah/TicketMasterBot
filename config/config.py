import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# =============================================================================
# NEW CONFIGURATION SYSTEM INTEGRATION
# =============================================================================
try:
    from .manager import ConfigurationManager
    
    # Check if we should use the new configuration system
    USE_NEW_CONFIG = os.getenv('USE_NEW_CONFIG', '0') == '1'
    
    if USE_NEW_CONFIG:
        print("📁 Using new configuration system")
        
        # Get region configuration
        region = os.getenv('REGION', 'east')
        region_config = ConfigurationManager.get_region_config(region)
        discord_config = ConfigurationManager.get_discord_config()
        api_config = ConfigurationManager.get_api_config()
        
        # Export for existing code compatibility
        CENTER_POINT = region_config.center_point_str
        RADIUS = str(region_config.radius)
        CLASSIFICATION_ID = region_config.classification_id
        GENRE_ID = region_config.genre_id
        
        DISCORD_BOT_TOKEN = discord_config.bot_token
        DISCORD_CHANNEL_ID = discord_config.main_channel_id
        DISCORD_CHANNEL_ID_TWO = discord_config.secondary_channel_id
        EUROPEAN_CHANNEL = discord_config.european_channel_id
        EUROPEAN_CHANNEL_TWO = discord_config.european_secondary_channel_id
        
        TICKETMASTER_API_KEY = api_config.ticketmaster_api_key
        DATABASE_URL = api_config.database_url
        DEBUG_LOGS = '1' if api_config.debug_logs else '0'
        
    else:
        print("🔧 Using legacy configuration system")
        # Fall back to legacy configuration
        from .legacy import get_legacy_config, get_legacy_discord_config
        
        legacy_config = get_legacy_config()
        legacy_discord = get_legacy_discord_config()
        
        CENTER_POINT = legacy_config['CENTER_POINT']
        RADIUS = legacy_config['RADIUS']
        CLASSIFICATION_ID = legacy_config['CLASSIFICATION_ID']
        GENRE_ID = legacy_config['GENRE_ID']
        
        DISCORD_BOT_TOKEN = legacy_discord['DISCORD_BOT_TOKEN']
        DISCORD_CHANNEL_ID = legacy_discord['DISCORD_CHANNEL_ID']
        DISCORD_CHANNEL_ID_TWO = legacy_discord['DISCORD_CHANNEL_ID_TWO']
        EUROPEAN_CHANNEL = legacy_discord['EUROPEAN_CHANNEL']
        EUROPEAN_CHANNEL_TWO = legacy_discord['EUROPEAN_CHANNEL_TWO']
        
        TICKETMASTER_API_KEY = os.getenv('TICKETMASTER_API_KEY')
        DATABASE_URL = os.getenv('DATABASE_URL')
        DEBUG_LOGS = os.getenv('DEBUG_LOGS')

except ImportError as e:
    print(f"⚠️  New configuration system not available ({e}), using legacy")
    # Original legacy configuration as fallback
    DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID', 0))
    DISCORD_CHANNEL_ID_TWO = int(os.getenv('DISCORD_CHANNEL_ID_TWO', 0))
    EUROPEAN_CHANNEL = int(os.getenv('EUROPEAN_CHANNEL', 0))
    EUROPEAN_CHANNEL_TWO = int(os.getenv('EUROPEAN_CHANNEL_TWO', 0))
    
    DEBUG_LOGS = os.getenv('DEBUG_LOGS')
    TICKETMASTER_API_KEY = os.getenv('TICKETMASTER_API_KEY')
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    CENTER_POINT = os.getenv('CENTER_POINT')
    RADIUS = os.getenv('RADIUS')
    
    # Add missing variables that were in original config
    REGION = os.getenv('REGION', 'east')
    if REGION == 'east':
        CENTER_POINT = CENTER_POINT or '43.58785,-64.72599'
        RADIUS = RADIUS or '950'
    # ... other regions would be handled similarly

# =============================================================================
# LEGACY COMPATIBILITY (maintained for backward compatibility)
# =============================================================================

# Redirect URI for OAuth or Webhooks
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost')
UNIT = os.getenv('UNIT', 'miles')

# Ensure these variables exist for legacy code
if 'CLASSIFICATION_ID' not in locals():
    CLASSIFICATION_ID = 'KZFzniwnSyZfZ7v7nJ'
if 'GENRE_ID' not in locals():
    GENRE_ID = ''

# Validation to ensure critical environment variables are set
if not DISCORD_BOT_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN is not set in the environment variables.")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the environment variables.")

if not TICKETMASTER_API_KEY:
    raise ValueError("TICKETMASTER_API_KEY is not set in the environment variables.")