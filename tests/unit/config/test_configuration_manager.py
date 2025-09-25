"""Tests for ConfigurationManager."""

import pytest
import os
from unittest.mock import patch
from config.manager import ConfigurationManager
from config.models import RegionConfig


class TestConfigurationManager:
    """Test ConfigurationManager functionality."""
    
    def test_get_region_config_valid_regions(self):
        """Test getting configuration for all valid regions."""
        expected_regions = ["east", "north", "south", "west", "europe", "comedy", "theater", "film"]
        
        for region in expected_regions:
            config = ConfigurationManager.get_region_config(region)
            assert config.name == region
            assert isinstance(config.center_point, tuple)
            assert len(config.center_point) == 2
            assert config.radius > 0
            assert config.classification_id  # Should not be empty
    
    def test_get_region_config_invalid_region(self):
        """Test error handling for invalid region."""
        with pytest.raises(ValueError, match="Unknown region: invalid"):
            ConfigurationManager.get_region_config('invalid')
    
    def test_list_available_regions(self):
        """Test listing all available regions."""
        regions = ConfigurationManager.list_available_regions()
        expected_regions = ["east", "north", "south", "west", "europe", "comedy", "theater", "film"]
        
        assert len(regions) == len(expected_regions)
        for region in expected_regions:
            assert region in regions
    
    def test_add_region_custom(self):
        """Test adding a custom region."""
        custom_config = RegionConfig(
            name="custom",
            center_point=(40.0, -100.0),
            radius=500
        )
        
        ConfigurationManager.add_region("custom", custom_config)
        
        # Should be able to retrieve the custom region
        retrieved = ConfigurationManager.get_region_config("custom")
        assert retrieved.name == "custom"
        assert retrieved.center_point == (40.0, -100.0)
        assert retrieved.radius == 500
        
        # Clean up
        if "custom" in ConfigurationManager._regions:
            del ConfigurationManager._regions["custom"]
    
    def test_validate_all_configurations(self):
        """Test validation of all region configurations."""
        results = ConfigurationManager.validate_all_configurations()
        
        # All pre-defined regions should be valid
        for region_name, is_valid in results.items():
            assert is_valid, f"Region {region_name} should be valid"
    
    @patch.dict(os.environ, {
        'DISCORD_BOT_TOKEN': 'test_token',
        'DISCORD_CHANNEL_ID': '123456789',
        'DISCORD_CHANNEL_ID_TWO': '987654321',
        'EUROPEAN_CHANNEL': '555666777',
        'EUROPEAN_CHANNEL_TWO': '888999000'
    })
    def test_get_discord_config_valid(self):
        """Test getting Discord configuration with valid environment."""
        config = ConfigurationManager.get_discord_config()
        
        assert config.bot_token == 'test_token'
        assert config.main_channel_id == 123456789
        assert config.secondary_channel_id == 987654321
        assert config.european_channel_id == 555666777
        assert config.european_secondary_channel_id == 888999000
        assert config.has_european_channels() == True
    
    @patch.dict(os.environ, {
        'DISCORD_BOT_TOKEN': '',
        'DISCORD_CHANNEL_ID': '0',
        'DISCORD_CHANNEL_ID_TWO': '0'
    }, clear=True)
    def test_get_discord_config_invalid(self):
        """Test getting Discord configuration with invalid environment."""
        with pytest.raises(ValueError, match="Discord bot token is required"):
            ConfigurationManager.get_discord_config()
    
    @patch.dict(os.environ, {
        'TICKETMASTER_API_KEY': 'test_api_key',
        'DATABASE_URL': 'postgresql://user:pass@localhost:5432/test_db',
        'DEBUG_LOGS': '1'
    })
    def test_get_api_config_valid(self):
        """Test getting API configuration with valid environment."""
        config = ConfigurationManager.get_api_config()
        
        assert config.ticketmaster_api_key == 'test_api_key'
        assert config.database_url == 'postgresql://user:pass@localhost:5432/test_db'
        assert config.debug_logs == True
    
    @patch.dict(os.environ, {
        'TICKETMASTER_API_KEY': '',
        'DATABASE_URL': 'invalid_url'
    }, clear=True)
    def test_get_api_config_invalid(self):
        """Test getting API configuration with invalid environment."""
        with pytest.raises(ValueError, match="Ticketmaster API key is required"):
            ConfigurationManager.get_api_config()
    
    def test_specific_region_configurations(self):
        """Test specific configurations for known regions."""
        # Test east region
        east = ConfigurationManager.get_region_config('east')
        assert east.center_point == (43.58785, -64.72599)
        assert east.radius == 950
        assert east.classification_id == "KZFzniwnSyZfZ7v7nJ"
        
        # Test comedy region (should have different classification)
        comedy = ConfigurationManager.get_region_config('comedy')
        assert comedy.classification_id == "KZFzniwnSyZfZ7v7na"
        assert comedy.genre_id == "KnvZfZ7vAe1"
        
        # Test europe region
        europe = ConfigurationManager.get_region_config('europe')
        assert europe.center_point == (47.37116, 8.50755)
        assert europe.radius == 1200
