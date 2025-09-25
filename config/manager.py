"""Configuration management for TicketMasterBot."""

from typing import Dict, List
import os
from .models import RegionConfig, DiscordConfig, APIConfig


class ConfigurationManager:
    """Centralized configuration management with validation and extension support."""
    
    # Pre-defined region configurations
    _regions: Dict[str, RegionConfig] = {
        "east": RegionConfig(
            name="east",
            center_point=(43.58785, -64.72599),
            radius=950
        ),
        "north": RegionConfig(
            name="north", 
            center_point=(62.41709, -108.42529),
            radius=1717
        ),
        "south": RegionConfig(
            name="south",
            center_point=(29.74590, -92.86707),
            radius=1094
        ),
        "west": RegionConfig(
            name="west",
            center_point=(15.42661, -133.61964),
            radius=2171
        ),
        "europe": RegionConfig(
            name="europe",
            center_point=(47.37116, 8.50755),
            radius=1200
        ),
        "comedy": RegionConfig(
            name="comedy",
            center_point=(44.69209, -99.95477),
            radius=3016,
            classification_id="KZFzniwnSyZfZ7v7na",
            genre_id="KnvZfZ7vAe1"
        ),
        "theater": RegionConfig(
            name="theater",
            center_point=(44.69209, -99.95477),
            radius=3016,
            classification_id="KZFzniwnSyZfZ7v7na", 
            genre_id="KnvZfZ7v7l1"
        ),
        "film": RegionConfig(
            name="film",
            center_point=(44.69209, -99.95477),
            radius=3016,
            classification_id="KZFzniwnSyZfZ7v7nn",
            genre_id="KnvZfZ7vAka"
        )
    }
    
    @classmethod
    def get_region_config(cls, region_name: str) -> RegionConfig:
        """Get configuration for a specific region with validation."""
        if region_name not in cls._regions:
            available_regions = ", ".join(cls._regions.keys())
            raise ValueError(f"Unknown region: {region_name}. Available regions: {available_regions}")
        
        config = cls._regions[region_name]
        config.validate()
        return config
    
    @classmethod
    def get_discord_config(cls) -> DiscordConfig:
        """Get Discord configuration from environment with validation."""
        config = DiscordConfig(
            bot_token=os.getenv('DISCORD_BOT_TOKEN', ''),
            main_channel_id=int(os.getenv('DISCORD_CHANNEL_ID', 0)),
            secondary_channel_id=int(os.getenv('DISCORD_CHANNEL_ID_TWO', 0)),
            european_channel_id=int(os.getenv('EUROPEAN_CHANNEL', 0)),
            european_secondary_channel_id=int(os.getenv('EUROPEAN_CHANNEL_TWO', 0))
        )
        config.validate()
        return config
    
    @classmethod
    def get_api_config(cls) -> APIConfig:
        """Get API configuration from environment with validation."""
        config = APIConfig(
            ticketmaster_api_key=os.getenv('TICKETMASTER_API_KEY', ''),
            database_url=os.getenv('DATABASE_URL', ''),
            debug_logs=os.getenv('DEBUG_LOGS', '0') == '1'
        )
        config.validate()
        return config
    
    @classmethod
    def list_available_regions(cls) -> List[str]:
        """Get list of all available region names."""
        return list(cls._regions.keys())
    
    @classmethod
    def add_region(cls, region_name: str, config: RegionConfig) -> None:
        """Add a new region configuration (for extensibility)."""
        config.validate()
        cls._regions[region_name] = config
    
    @classmethod
    def validate_all_configurations(cls) -> Dict[str, bool]:
        """Validate all region configurations and return status."""
        results = {}
        for region_name, config in cls._regions.items():
            try:
                config.validate()
                results[region_name] = True
            except ValueError:
                results[region_name] = False
        return results
