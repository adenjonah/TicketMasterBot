# Phase 1: Foundation Refactoring

## 🎯 Overview

**Duration**: 2 weeks (10-12 days)  
**Priority**: Critical  
**Risk Level**: Low  
**Team Size**: 1-2 developers

Phase 1 establishes the foundational elements needed for clean architecture: proper configuration management, domain models, basic testing infrastructure, and standardized error handling.

## 🎪 Goals & Success Criteria

### Primary Goals
1. **Replace procedural configuration** with extensible class-based system
2. **Create domain models** for core business entities
3. **Establish testing infrastructure** with basic test coverage
4. **Standardize error handling** patterns across the codebase
5. **Maintain 100% backward compatibility**

### Success Criteria
- [ ] Configuration system supports all current regions + easy extension
- [ ] Domain models replace raw dictionary usage in core functions
- [ ] Test runner operational with fixtures for all major components
- [ ] Error handling follows consistent patterns
- [ ] All existing functionality works without changes
- [ ] Code complexity reduced by 20%

## 📅 Week-by-Week Breakdown

### Week 1: Configuration & Models

#### Days 1-3: Configuration System Refactoring
**Goal**: Replace `config/config.py` with extensible class-based configuration

**Current Problem**:
```python
# config/config.py - 73 lines of procedural if/elif statements
if REGION == 'east':
    CENTER_POINT='43.58785,-64.72599'
    RADIUS='950'
elif REGION == 'north': 
    CENTER_POINT='62.41709,-108.42529'
    RADIUS='1717'
# ... repeated 8 times
```

**Target Solution**:
```python
# config/models.py
@dataclass
class RegionConfig:
    name: str
    center_point: Tuple[float, float]
    radius: int
    classification_id: str = "KZFzniwnSyZfZ7v7nJ"
    genre_id: str = ""

class ConfigurationManager:
    """Centralized configuration management with validation and extension support."""
    
    @classmethod
    def get_region_config(cls, region_name: str) -> RegionConfig:
        """Get configuration for a specific region with validation."""
        pass
    
    @classmethod
    def get_discord_config(cls) -> DiscordConfig:
        """Get Discord-related configuration with validation."""
        pass
```

**Implementation Steps**:
1. **Day 1**: Create `config/models.py` with data classes
2. **Day 2**: Create `ConfigurationManager` with factory methods
3. **Day 3**: Update existing code to use new configuration system

**Deliverables**:
- [ ] `config/models.py` - Configuration data classes
- [ ] `config/manager.py` - Configuration management logic
- [ ] `config/factory.py` - Configuration factory methods
- [ ] Migration of all existing config usage
- [ ] Validation for all environment variables

#### Days 4-5: Domain Model Creation
**Goal**: Create typed domain models for core business entities

**Current Problem**:
```python
# Raw dictionaries passed around
event = {"id": "123", "name": "Concert", "artistID": "456", ...}
artist = {"artistID": "456", "name": "Taylor Swift", "notable": True}
```

**Target Solution**:
```python
# domain/models.py
@dataclass
class Artist:
    id: str
    name: str
    is_notable: bool = False
    
    def __post_init__(self):
        if not self.id or not self.name:
            raise ValueError("Artist must have ID and name")

@dataclass
class Venue:
    id: str
    name: str
    city: str
    state: str

@dataclass  
class Event:
    id: str
    name: str
    artist: Optional[Artist]
    venue: Venue
    event_date: datetime
    sale_date: datetime
    url: str
    image_url: Optional[str] = None
    sent_to_discord: bool = False
    region: Optional[str] = None
    
    def is_notable(self) -> bool:
        """Check if this event features a notable artist."""
        return self.artist is not None and self.artist.is_notable
    
    def should_notify_now(self) -> bool:
        """Check if this event should be notified to Discord."""
        return not self.sent_to_discord and self.sale_date > datetime.now()
```

**Implementation Steps**:
1. **Day 4**: Create domain models with validation
2. **Day 5**: Create factory methods for converting from/to dictionaries

**Deliverables**:
- [ ] `domain/models.py` - Core domain entities
- [ ] `domain/factories.py` - Conversion utilities
- [ ] `domain/exceptions.py` - Domain-specific exceptions
- [ ] Type hints throughout existing codebase

#### Days 6-7: Basic Testing Infrastructure
**Goal**: Establish testing framework with fixtures and basic tests

**Implementation Steps**:
1. **Day 6**: Set up pytest, create test structure, basic fixtures
2. **Day 7**: Write tests for configuration and domain models

**Deliverables**:
- [ ] `tests/` directory structure
- [ ] `tests/conftest.py` - Pytest configuration and fixtures
- [ ] `tests/unit/test_config.py` - Configuration tests
- [ ] `tests/unit/test_domain.py` - Domain model tests
- [ ] `tests/fixtures/` - Test data fixtures
- [ ] CI integration (GitHub Actions or similar)

### Week 2: Error Handling & Database

#### Days 8-10: Error Handling Standardization
**Goal**: Implement consistent error handling patterns

**Current Problem**:
```python
# Inconsistent error handling throughout codebase
try:
    # Some operation
except Exception as e:
    logger.error(f"Error: {e}")  # Sometimes logs and continues
    # OR
    return False  # Sometimes returns failure
    # OR
    raise  # Sometimes re-raises
```

**Target Solution**:
```python
# errors/handlers.py
class ErrorHandler:
    """Centralized error handling with consistent patterns."""
    
    @staticmethod
    async def handle_discord_error(error: discord.DiscordException, context: str) -> ErrorResult:
        """Handle Discord API errors with appropriate retry logic."""
        pass
    
    @staticmethod 
    async def handle_database_error(error: Exception, operation: str) -> ErrorResult:
        """Handle database errors with connection recovery."""
        pass

# errors/exceptions.py  
class TicketMasterBotException(Exception):
    """Base exception for all bot-related errors."""
    pass

class ConfigurationError(TicketMasterBotException):
    """Configuration-related errors."""
    pass

class EventProcessingError(TicketMasterBotException):
    """Event processing errors."""
    pass
```

**Implementation Steps**:
1. **Day 8**: Create custom exception hierarchy
2. **Day 9**: Implement centralized error handlers  
3. **Day 10**: Update existing code to use standardized error handling

**Deliverables**:
- [ ] `errors/exceptions.py` - Custom exception hierarchy
- [ ] `errors/handlers.py` - Centralized error handling
- [ ] `errors/retry.py` - Retry logic utilities
- [ ] Updated error handling throughout codebase
- [ ] Error handling tests

#### Days 11-12: Database Schema Management
**Goal**: Proper database schema management and migrations

**Current Problem**:
```python
# database/init.py - 350+ lines of SQL DDL mixed with Python
await conn.execute('''
CREATE TABLE IF NOT EXISTS Events (
    eventID TEXT PRIMARY KEY,
    # ... 15 more columns
)''')
# Repeated for 6+ tables
```

**Target Solution**:
```python
# database/schema.py
class SchemaManager:
    """Manages database schema with proper migrations."""
    
    async def ensure_schema_current(self) -> None:
        """Ensure database schema is at current version."""
        pass
    
    async def apply_migration(self, migration: Migration) -> None:
        """Apply a specific schema migration.""" 
        pass

# database/migrations/
# 001_initial_schema.sql
# 002_add_notification_tracking.sql
# 003_add_region_support.sql
```

**Implementation Steps**:
1. **Day 11**: Extract schema definitions to SQL files
2. **Day 12**: Create migration system and schema manager

**Deliverables**:
- [ ] `database/schema/` - SQL schema definitions
- [ ] `database/migrations/` - Migration scripts
- [ ] `database/schema_manager.py` - Migration management
- [ ] `database/connection.py` - Improved connection handling
- [ ] Schema versioning system

## 🧪 Testing Strategy

### Test Categories
1. **Unit Tests**: Individual functions/classes (target: 80% coverage)
2. **Integration Tests**: Database and external API interactions
3. **Contract Tests**: Domain model validation
4. **Configuration Tests**: All environment variable combinations

### Test Structure
```
tests/
├── conftest.py              # Pytest configuration
├── fixtures/
│   ├── events.json          # Test event data
│   ├── artists.json         # Test artist data
│   └── config.yaml          # Test configuration
├── unit/
│   ├── test_config.py       # Configuration tests
│   ├── test_domain.py       # Domain model tests
│   └── test_errors.py       # Error handling tests
├── integration/
│   ├── test_database.py     # Database integration
│   └── test_api.py          # External API tests
└── helpers/
    ├── factories.py         # Test data factories
    └── assertions.py        # Custom assertions
```

### Key Test Scenarios
- [ ] All region configurations load correctly
- [ ] Domain models validate input data properly
- [ ] Error handlers respond appropriately to different error types
- [ ] Database schema migrations apply cleanly
- [ ] Configuration changes don't break existing functionality

## 🚀 Implementation Guide

### Day 1-3: Configuration Refactoring

#### Step 1: Create Configuration Models
```python
# config/models.py
from dataclasses import dataclass
from typing import Tuple, Dict, Optional

@dataclass
class RegionConfig:
    """Configuration for a specific geographical region."""
    name: str
    center_point: Tuple[float, float]
    radius: int
    classification_id: str = "KZFzniwnSyZfZ7v7nJ"
    genre_id: str = ""
    
    @property
    def center_point_str(self) -> str:
        """Return center point as comma-separated string for API."""
        return f"{self.center_point[0]},{self.center_point[1]}"
    
    def validate(self) -> None:
        """Validate configuration values."""
        if self.radius <= 0:
            raise ValueError(f"Radius must be positive: {self.radius}")
        if not (-90 <= self.center_point[0] <= 90):
            raise ValueError(f"Invalid latitude: {self.center_point[0]}")
        if not (-180 <= self.center_point[1] <= 180):
            raise ValueError(f"Invalid longitude: {self.center_point[1]}")

@dataclass
class DiscordConfig:
    """Discord-related configuration."""
    bot_token: str
    main_channel_id: int
    secondary_channel_id: int
    european_channel_id: int
    european_secondary_channel_id: int
    
    def validate(self) -> None:
        """Validate Discord configuration."""
        if not self.bot_token:
            raise ValueError("Discord bot token is required")
        for channel_id in [self.main_channel_id, self.secondary_channel_id]:
            if channel_id <= 0:
                raise ValueError(f"Invalid channel ID: {channel_id}")

@dataclass
class APIConfig:
    """External API configuration."""
    ticketmaster_api_key: str
    database_url: str
    debug_logs: bool = False
    
    def validate(self) -> None:
        """Validate API configuration."""
        if not self.ticketmaster_api_key:
            raise ValueError("Ticketmaster API key is required")
        if not self.database_url:
            raise ValueError("Database URL is required")
```

#### Step 2: Create Configuration Manager
```python
# config/manager.py
from typing import Dict, Optional
import os
from .models import RegionConfig, DiscordConfig, APIConfig

class ConfigurationManager:
    """Centralized configuration management."""
    
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
        """Get configuration for a specific region."""
        if region_name not in cls._regions:
            raise ValueError(f"Unknown region: {region_name}")
        
        config = cls._regions[region_name]
        config.validate()
        return config
    
    @classmethod
    def get_discord_config(cls) -> DiscordConfig:
        """Get Discord configuration from environment."""
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
        """Get API configuration from environment."""
        config = APIConfig(
            ticketmaster_api_key=os.getenv('TICKETMASTER_API_KEY', ''),
            database_url=os.getenv('DATABASE_URL', ''),
            debug_logs=os.getenv('DEBUG_LOGS') == '1'
        )
        config.validate()
        return config
    
    @classmethod
    def list_available_regions(cls) -> List[str]:
        """Get list of all available region names."""
        return list(cls._regions.keys())
```

#### Step 3: Migration Pattern
```python
# config/legacy.py - Temporary bridge during migration
"""
Legacy configuration support during migration period.
This module provides backward compatibility while code is being updated.
"""
import warnings
from .manager import ConfigurationManager

# Maintain backward compatibility
def get_legacy_config():
    """Provide legacy configuration format for existing code."""
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
        'GENRE_ID': region_config.genre_id
    }
```

### Testing Implementation

#### Configuration Tests
```python
# tests/unit/test_config.py
import pytest
from config.manager import ConfigurationManager
from config.models import RegionConfig

class TestConfigurationManager:
    """Test configuration management functionality."""
    
    def test_get_region_config_valid_region(self):
        """Test getting configuration for valid region."""
        config = ConfigurationManager.get_region_config('east')
        assert config.name == 'east'
        assert config.radius == 950
        assert config.center_point == (43.58785, -64.72599)
    
    def test_get_region_config_invalid_region(self):
        """Test error handling for invalid region."""
        with pytest.raises(ValueError, match="Unknown region"):
            ConfigurationManager.get_region_config('invalid')
    
    def test_region_config_validation(self):
        """Test region configuration validation."""
        # Valid config should pass
        config = RegionConfig("test", (45.0, -90.0), 100)
        config.validate()  # Should not raise
        
        # Invalid latitude should fail
        invalid_config = RegionConfig("test", (95.0, -90.0), 100)
        with pytest.raises(ValueError, match="Invalid latitude"):
            invalid_config.validate()
    
    def test_center_point_string_format(self):
        """Test center point string formatting."""
        config = RegionConfig("test", (45.123, -90.456), 100)
        assert config.center_point_str == "45.123,-90.456"
```

## 🔄 Migration & Rollback Strategy

### Migration Approach
1. **Parallel Implementation**: New config system alongside old
2. **Gradual Transition**: Update one module at a time
3. **Feature Flag**: Environment variable to toggle between systems
4. **Validation**: Ensure both systems return equivalent results

### Rollback Plan
1. **Environment Variable**: `USE_LEGACY_CONFIG=1` reverts to old system
2. **Git Branches**: Each day's work in separate branch for easy revert
3. **Testing**: Comprehensive tests ensure no functionality regression
4. **Monitoring**: Track any performance/behavior changes

### Backward Compatibility
- Old configuration access still works with deprecation warnings
- All existing functionality preserved
- No changes to external API or database schemas
- Environment variables remain the same

## 📋 Deliverables Checklist

### Configuration System
- [ ] `config/models.py` - Configuration data classes
- [ ] `config/manager.py` - Configuration management logic  
- [ ] `config/factory.py` - Configuration factory methods
- [ ] `config/legacy.py` - Backward compatibility bridge
- [ ] Migration of all existing config usage
- [ ] Comprehensive configuration tests

### Domain Models
- [ ] `domain/models.py` - Core domain entities (Event, Artist, Venue)
- [ ] `domain/factories.py` - Conversion utilities
- [ ] `domain/exceptions.py` - Domain-specific exceptions
- [ ] Type hints added throughout existing codebase
- [ ] Domain model tests with edge cases

### Testing Infrastructure
- [ ] `tests/` directory structure established
- [ ] `tests/conftest.py` - Pytest configuration and fixtures
- [ ] `tests/fixtures/` - Test data fixtures
- [ ] CI integration (GitHub Actions)
- [ ] Test coverage reporting
- [ ] 30%+ test coverage achieved

### Error Handling
- [ ] `errors/exceptions.py` - Custom exception hierarchy
- [ ] `errors/handlers.py` - Centralized error handling
- [ ] `errors/retry.py` - Retry logic utilities
- [ ] Updated error handling throughout codebase
- [ ] Error handling tests

### Database Management
- [ ] `database/schema/` - SQL schema definitions
- [ ] `database/migrations/` - Migration scripts
- [ ] `database/schema_manager.py` - Migration management
- [ ] `database/connection.py` - Improved connection handling
- [ ] Schema versioning system

## 🎯 Phase 1 Completion Criteria

### Technical Criteria
- [ ] All new configuration system tests pass
- [ ] Domain models handle all current data correctly
- [ ] Error handling is consistent across all modules
- [ ] Database schema management is operational
- [ ] Test coverage is ≥30%
- [ ] No performance regression in existing functionality

### Business Criteria  
- [ ] All existing bot commands work unchanged
- [ ] All existing crawler functionality preserved
- [ ] No disruption to Discord notifications
- [ ] Configuration changes require no environment variable updates
- [ ] Team can add new regions without code changes

### Quality Criteria
- [ ] Code complexity reduced by 20%
- [ ] All new code follows consistent patterns
- [ ] Documentation updated for new systems
- [ ] Deprecation warnings guide migration path
- [ ] Rollback procedures tested and documented

**Next Phase**: [Phase 2: Architecture](PHASE_2_ARCHITECTURE.md) - Service layer and repository implementation
