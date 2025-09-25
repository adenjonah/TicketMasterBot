"""Tests for RegionConfig model."""

import pytest
from config.models.region_config import RegionConfig


class TestRegionConfig:
    """Test RegionConfig functionality."""
    
    def test_region_config_creation_valid(self):
        """Test creating region config with valid data."""
        config = RegionConfig(
            name="test",
            center_point=(45.0, -90.0),
            radius=100
        )
        assert config.name == "test"
        assert config.center_point == (45.0, -90.0)
        assert config.radius == 100
        assert config.classification_id == "KZFzniwnSyZfZ7v7nJ"  # Default
        assert config.genre_id == ""  # Default
    
    def test_region_config_with_custom_classification(self):
        """Test creating region config with custom classification."""
        config = RegionConfig(
            name="comedy",
            center_point=(45.0, -90.0),
            radius=100,
            classification_id="KZFzniwnSyZfZ7v7na",
            genre_id="KnvZfZ7vAe1"
        )
        assert config.classification_id == "KZFzniwnSyZfZ7v7na"
        assert config.genre_id == "KnvZfZ7vAe1"
    
    def test_center_point_string_format(self):
        """Test center point string formatting."""
        config = RegionConfig("test", (45.123, -90.456), 100)
        assert config.center_point_str == "45.123,-90.456"
    
    def test_validation_valid_config(self):
        """Test validation with valid configuration."""
        config = RegionConfig("test", (45.0, -90.0), 100)
        config.validate()  # Should not raise
    
    def test_validation_invalid_radius(self):
        """Test validation with invalid radius."""
        config = RegionConfig("test", (45.0, -90.0), -100)
        with pytest.raises(ValueError, match="Radius must be positive"):
            config.validate()
    
    def test_validation_invalid_latitude_high(self):
        """Test validation with latitude too high."""
        config = RegionConfig("test", (95.0, -90.0), 100)
        with pytest.raises(ValueError, match="Invalid latitude"):
            config.validate()
    
    def test_validation_invalid_latitude_low(self):
        """Test validation with latitude too low."""
        config = RegionConfig("test", (-95.0, -90.0), 100)
        with pytest.raises(ValueError, match="Invalid latitude"):
            config.validate()
    
    def test_validation_invalid_longitude_high(self):
        """Test validation with longitude too high."""
        config = RegionConfig("test", (45.0, 190.0), 100)
        with pytest.raises(ValueError, match="Invalid longitude"):
            config.validate()
    
    def test_validation_invalid_longitude_low(self):
        """Test validation with longitude too low."""
        config = RegionConfig("test", (45.0, -190.0), 100)
        with pytest.raises(ValueError, match="Invalid longitude"):
            config.validate()
    
    def test_validation_empty_name(self):
        """Test validation with empty name."""
        config = RegionConfig("", (45.0, -90.0), 100)
        with pytest.raises(ValueError, match="Region name cannot be empty"):
            config.validate()
    
    def test_validation_empty_classification_id(self):
        """Test validation with empty classification ID."""
        config = RegionConfig("test", (45.0, -90.0), 100, classification_id="")
        with pytest.raises(ValueError, match="Classification ID cannot be empty"):
            config.validate()
