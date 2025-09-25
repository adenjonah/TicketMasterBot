"""
Legacy configuration support during migration period.
This module provides backward compatibility while code is being updated.
"""

import warnings
import os
from .manager import ConfigurationManager


def get_legacy_config():
    """
    Provide legacy configuration format for existing code.
    
    This function maintains backward compatibility during the migration period.
    It will be removed after all code is updated to use the new configuration system.
    """
    warnings.warn(
        "Legacy configuration access is deprecated. Use ConfigurationManager instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    region = os.getenv('REGION', 'east')
    region_config = ConfigurationManager.get_region_config(region)
    
    # Return old format for backward compatibility
    return {
        'CENTER_POINT': region_config.center_point_str,
        'RADIUS': str(region_config.radius),
        'CLASSIFICATION_ID': region_config.classification_id,
        'GENRE_ID': region_config.genre_id,
        'REGION': region_config.name
    }


def get_legacy_discord_config():
    """
    Provide legacy Discord configuration format.
    
    Returns individual configuration values as they were accessed before.
    """
    warnings.warn(
        "Legacy Discord configuration access is deprecated. Use ConfigurationManager.get_discord_config() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    discord_config = ConfigurationManager.get_discord_config()
    
    return {
        'DISCORD_BOT_TOKEN': discord_config.bot_token,
        'DISCORD_CHANNEL_ID': discord_config.main_channel_id,
        'DISCORD_CHANNEL_ID_TWO': discord_config.secondary_channel_id,
        'EUROPEAN_CHANNEL': discord_config.european_channel_id,
        'EUROPEAN_CHANNEL_TWO': discord_config.european_secondary_channel_id
    }
