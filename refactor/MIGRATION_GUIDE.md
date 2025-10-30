# Migration Guide: Step-by-Step Refactoring Implementation

## 🎯 Overview

This guide provides detailed, step-by-step instructions for implementing the TicketMasterBot refactoring plan. It includes practical commands, code examples, and checkpoint procedures to ensure safe migration.

## 🚦 Pre-Migration Checklist

### Prerequisites
- [ ] Python 3.9+ installed
- [ ] PostgreSQL access (local or cloud)
- [ ] Discord bot token and channel access
- [ ] Ticketmaster API key
- [ ] Git repository with write access
- [ ] Heroku CLI (if using Heroku deployment)

### Backup Procedures
```bash
# 1. Create backup branch
git checkout -b backup/pre-refactoring-$(date +%Y%m%d)
git push origin backup/pre-refactoring-$(date +%Y%m%d)

# 2. Export current database schema
pg_dump $DATABASE_URL --schema-only > backup/schema_$(date +%Y%m%d).sql

# 3. Export environment configuration
env | grep -E "(DISCORD|TICKETMASTER|DATABASE)" > backup/env_$(date +%Y%m%d).txt

# 4. Test current deployment
python -m pytest tests/ || echo "No existing tests found"
```

### Environment Setup
```bash
# 1. Create development branch
git checkout -b refactor/phase-1-foundation

# 2. Install additional development dependencies
pip install pytest pytest-asyncio pytest-cov mypy black flake8 bandit

# 3. Create development requirements file
cat >> requirements-dev.txt << EOF
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
pytest-benchmark>=4.0.0
mypy>=1.0.0
black>=22.0.0
flake8>=5.0.0
bandit>=1.7.0
testcontainers>=3.7.0
pydantic>=1.10.0
prometheus-client>=0.15.0
EOF

pip install -r requirements-dev.txt
```

## 📋 Phase 1: Foundation Implementation

### Week 1, Days 1-3: Configuration System Refactoring

#### Day 1: Create Configuration Models

**Step 1: Create new configuration structure**
```bash
mkdir -p config/models
touch config/models/__init__.py
```

**Step 2: Implement configuration models**
```python
# config/models/region_config.py
from dataclasses import dataclass
from typing import Tuple

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

# config/models/discord_config.py
from dataclasses import dataclass

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

# config/models/__init__.py
from .region_config import RegionConfig
from .discord_config import DiscordConfig

__all__ = ['RegionConfig', 'DiscordConfig']
```

**Step 3: Test configuration models**
```bash
# Create basic test structure
mkdir -p tests/unit/config
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/unit/config/__init__.py

# Run tests
python -m pytest tests/unit/config/ -v
```

**Checkpoint 1**: Configuration models created and tested
```bash
git add config/models/ tests/unit/config/
git commit -m "Phase 1.1: Add configuration models with validation"
```

#### Day 2: Create Configuration Manager

**Step 1: Implement configuration manager**
```python
# config/manager.py
from typing import Dict, Optional, List
import os
from .models import RegionConfig, DiscordConfig

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
    def list_available_regions(cls) -> List[str]:
        """Get list of all available region names."""
        return list(cls._regions.keys())
```

**Step 2: Create backward compatibility bridge**
```python
# config/legacy.py
"""
Legacy configuration support during migration period.
This module provides backward compatibility while code is being updated.
"""
import warnings
import os
from .manager import ConfigurationManager

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

**Checkpoint 2**: Configuration manager implemented
```bash
git add config/manager.py config/legacy.py
git commit -m "Phase 1.2: Add configuration manager with legacy support"
```

#### Day 3: Update Existing Code

**Step 1: Gradually migrate existing configuration usage**
```python
# config/config.py - Update existing file to use new system
import os
from dotenv import load_dotenv
from .manager import ConfigurationManager
from .legacy import get_legacy_config

# Load environment variables from the .env file
load_dotenv()

# New configuration system
try:
    config_manager = ConfigurationManager()
    
    # For gradual migration, check if using new system
    USE_NEW_CONFIG = os.getenv('USE_NEW_CONFIG', '0') == '1'
    
    if USE_NEW_CONFIG:
        # Use new configuration system
        region = os.getenv('REGION', 'east')
        region_config = config_manager.get_region_config(region)
        discord_config = config_manager.get_discord_config()
        
        # Export for existing code
        CENTER_POINT = region_config.center_point_str
        RADIUS = str(region_config.radius)
        CLASSIFICATION_ID = region_config.classification_id
        GENRE_ID = region_config.genre_id
        
        DISCORD_BOT_TOKEN = discord_config.bot_token
        DISCORD_CHANNEL_ID = discord_config.main_channel_id
        # ... other Discord config
    else:
        # Use legacy configuration (existing code)
        legacy_config = get_legacy_config()
        CENTER_POINT = legacy_config['CENTER_POINT']
        RADIUS = legacy_config['RADIUS']
        CLASSIFICATION_ID = legacy_config['CLASSIFICATION_ID']
        GENRE_ID = legacy_config['GENRE_ID']
        
        # Keep existing Discord config
        DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
        DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID', 0))
        # ... rest of existing config

except Exception as e:
    # Fallback to original configuration if new system fails
    print(f"Warning: New configuration system failed ({e}), using legacy")
    # ... original configuration code ...
```

**Step 2: Test migration**
```bash
# Test with new config system
export USE_NEW_CONFIG=1
python -c "from config.config import CENTER_POINT, RADIUS; print(f'Center: {CENTER_POINT}, Radius: {RADIUS}')"

# Test with legacy system
export USE_NEW_CONFIG=0
python -c "from config.config import CENTER_POINT, RADIUS; print(f'Center: {CENTER_POINT}, Radius: {RADIUS}')"
```

**Checkpoint 3**: Configuration migration complete
```bash
git add config/config.py
git commit -m "Phase 1.3: Migrate existing configuration with backward compatibility"
```

### Week 1, Days 4-5: Domain Model Creation

#### Day 4: Create Domain Models

**Step 1: Create domain structure**
```bash
mkdir -p domain
touch domain/__init__.py
```

**Step 2: Implement core domain models**
```python
# domain/models.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Artist:
    """Artist domain model."""
    id: str
    name: str
    is_notable: bool = False
    
    def __post_init__(self):
        if not self.id or not self.name:
            raise ValueError("Artist must have ID and name")

@dataclass
class Venue:
    """Venue domain model."""
    id: str
    name: str
    city: str
    state: str
    
    def __post_init__(self):
        if not all([self.id, self.name, self.city, self.state]):
            raise ValueError("Venue must have all required fields")

@dataclass  
class Event:
    """Event domain model."""
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
    
    def __post_init__(self):
        if not all([self.id, self.name, self.venue, self.event_date, self.sale_date, self.url]):
            raise ValueError("Event must have all required fields")
        
        if self.event_date <= datetime.now():
            raise ValueError("Event date must be in the future")
        
        if self.sale_date <= datetime.now():
            raise ValueError("Sale date must be in the future")
    
    def is_notable(self) -> bool:
        """Check if this event features a notable artist."""
        return self.artist is not None and self.artist.is_notable
    
    def should_notify_now(self) -> bool:
        """Check if this event should be notified to Discord."""
        return not self.sent_to_discord and self.sale_date > datetime.now()
    
    def get_region_classification(self) -> str:
        """Get region classification for routing."""
        if self.region and self.region.lower() == 'eu':
            return 'eu'
        return 'non-eu'
```

**Step 3: Create conversion utilities**
```python
# domain/factories.py
from typing import Dict, Any, Optional
from datetime import datetime
from .models import Event, Artist, Venue

class EventFactory:
    """Factory for creating Event domain objects from various sources."""
    
    @staticmethod
    def from_database_row(row: Dict[str, Any]) -> Event:
        """Create Event from database row."""
        artist = None
        if row.get('artistid'):
            artist = Artist(
                id=row['artistid'],
                name=row.get('artist_name', 'Unknown Artist'),
                is_notable=row.get('notable', False)
            )
        
        venue = Venue(
            id=row['venueid'],
            name=row.get('venue_name', 'Unknown Venue'),
            city=row.get('city', 'Unknown City'),
            state=row.get('state', 'Unknown State')
        )
        
        return Event(
            id=row['eventid'],
            name=row['name'],
            artist=artist,
            venue=venue,
            event_date=row['eventdate'],
            sale_date=row['ticketonsalestart'],
            url=row['url'],
            image_url=row.get('image_url'),
            sent_to_discord=row.get('senttodiscord', False),
            region=row.get('region')
        )
    
    @staticmethod
    def from_api_response(api_data: Dict[str, Any], region: str) -> Event:
        """Create Event from Ticketmaster API response."""
        # Extract venue information
        venue_data = api_data.get('_embedded', {}).get('venues', [{}])[0]
        venue = Venue(
            id=venue_data.get('id', 'unknown'),
            name=venue_data.get('name', 'Unknown Venue'),
            city=venue_data.get('city', {}).get('name', 'Unknown City'),
            state=venue_data.get('state', {}).get('stateCode', 'Unknown State')
        )
        
        # Extract artist information (if available)
        artist = None
        attractions = api_data.get('_embedded', {}).get('attractions', [])
        if attractions:
            artist_data = attractions[0]
            artist = Artist(
                id=artist_data.get('id', 'unknown'),
                name=artist_data.get('name', 'Unknown Artist'),
                is_notable=False  # Will be determined later by artist service
            )
        
        # Extract dates
        sales = api_data.get('sales', {}).get('public', {})
        sale_date = datetime.fromisoformat(sales.get('startDateTime', datetime.now().isoformat()))
        event_date = datetime.fromisoformat(api_data.get('dates', {}).get('start', {}).get('dateTime', datetime.now().isoformat()))
        
        return Event(
            id=api_data['id'],
            name=api_data.get('name', 'Unknown Event'),
            artist=artist,
            venue=venue,
            event_date=event_date,
            sale_date=sale_date,
            url=api_data.get('url', ''),
            image_url=api_data.get('images', [{}])[0].get('url'),
            region=region
        )
```

**Checkpoint 4**: Domain models created
```bash
git add domain/
git commit -m "Phase 1.4: Add domain models with validation and factories"
```

#### Day 5: Create Basic Testing Infrastructure

**Step 1: Set up pytest configuration**
```python
# tests/conftest.py
import pytest
import asyncio
from unittest.mock import Mock
from datetime import datetime, timedelta

from domain.models import Event, Artist, Venue

# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def sample_artist():
    """Create a sample artist for testing."""
    return Artist(
        id="artist123",
        name="Test Artist", 
        is_notable=True
    )

@pytest.fixture
def sample_venue():
    """Create a sample venue for testing."""
    return Venue(
        id="venue123",
        name="Test Venue",
        city="Test City",
        state="TS"
    )

@pytest.fixture
def sample_event(sample_artist, sample_venue):
    """Create a sample event for testing."""
    return Event(
        id="event123",
        name="Test Event",
        artist=sample_artist,
        venue=sample_venue,
        event_date=datetime.now() + timedelta(days=30),
        sale_date=datetime.now() + timedelta(days=1),
        url="https://example.com/event"
    )
```

**Step 2: Create basic tests**
```python
# tests/unit/test_domain.py
import pytest
from datetime import datetime, timedelta
from domain.models import Event, Artist, Venue

class TestArtist:
    """Test Artist domain model."""
    
    def test_artist_creation_valid(self):
        """Test creating artist with valid data."""
        artist = Artist(id="test123", name="Test Artist", is_notable=True)
        assert artist.id == "test123"
        assert artist.name == "Test Artist"
        assert artist.is_notable == True
    
    def test_artist_creation_invalid_empty_id(self):
        """Test creating artist with empty ID raises error."""
        with pytest.raises(ValueError, match="Artist must have ID and name"):
            Artist(id="", name="Test Artist")
    
    def test_artist_creation_invalid_empty_name(self):
        """Test creating artist with empty name raises error."""
        with pytest.raises(ValueError, match="Artist must have ID and name"):
            Artist(id="test123", name="")

class TestEvent:
    """Test Event domain model."""
    
    def test_event_is_notable_with_notable_artist(self, sample_event):
        """Test event notability with notable artist."""
        sample_event.artist.is_notable = True
        assert sample_event.is_notable() == True
    
    def test_event_is_notable_with_non_notable_artist(self, sample_event):
        """Test event notability with non-notable artist."""
        sample_event.artist.is_notable = False
        assert sample_event.is_notable() == False
    
    def test_event_is_notable_with_no_artist(self, sample_venue):
        """Test event notability with no artist."""
        event = Event(
            id="event123",
            name="Test Event",
            artist=None,
            venue=sample_venue,
            event_date=datetime.now() + timedelta(days=30),
            sale_date=datetime.now() + timedelta(days=1),
            url="https://example.com/event"
        )
        assert event.is_notable() == False
    
    def test_should_notify_now_unsent_future_sale(self, sample_event):
        """Test notification logic for unsent event with future sale date."""
        sample_event.sent_to_discord = False
        sample_event.sale_date = datetime.now() + timedelta(hours=1)
        assert sample_event.should_notify_now() == True
    
    def test_should_notify_now_already_sent(self, sample_event):
        """Test notification logic for already sent event."""
        sample_event.sent_to_discord = True
        assert sample_event.should_notify_now() == False
```

**Step 3: Run tests**
```bash
# Install pytest if not already installed
pip install pytest pytest-asyncio

# Run tests
python -m pytest tests/ -v

# Run with coverage
pip install pytest-cov
python -m pytest tests/ --cov=domain --cov-report=html
```

**Checkpoint 5**: Basic testing infrastructure established
```bash
git add tests/
git commit -m "Phase 1.5: Add basic testing infrastructure with domain model tests"
```

### Week 2, Days 8-10: Error Handling & Database Management

#### Day 8: Standardize Error Handling

**Step 1: Create custom exception hierarchy**
```python
# errors/exceptions.py
"""Custom exception hierarchy for TicketMasterBot."""

class TicketMasterBotException(Exception):
    """Base exception for all bot-related errors."""
    pass

class ConfigurationError(TicketMasterBotException):
    """Configuration-related errors."""
    pass

class DomainValidationError(TicketMasterBotException):
    """Domain model validation errors."""
    pass

class RepositoryError(TicketMasterBotException):
    """Repository/data access errors."""
    pass

class ServiceError(TicketMasterBotException):
    """Service layer errors."""
    pass

class ExternalAPIError(TicketMasterBotException):
    """External API communication errors."""
    pass

class DiscordAPIError(ExternalAPIError):
    """Discord API specific errors."""
    
    def __init__(self, message: str, status_code: int = None, retry_after: int = None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after

class TicketmasterAPIError(ExternalAPIError):
    """Ticketmaster API specific errors."""
    
    def __init__(self, message: str, status_code: int = None, rate_limit_exceeded: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.rate_limit_exceeded = rate_limit_exceeded
```

**Step 2: Create centralized error handlers**
```python
# errors/handlers.py
import logging
from typing import Optional, Dict, Any
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorResult:
    """Result of error handling operation."""
    
    def __init__(self, should_retry: bool = False, delay_seconds: int = 0, 
                 escalate: bool = False, message: str = ""):
        self.should_retry = should_retry
        self.delay_seconds = delay_seconds
        self.escalate = escalate
        self.message = message

class ErrorHandler:
    """Centralized error handling with consistent patterns."""
    
    @staticmethod
    async def handle_discord_error(error: Exception, context: str) -> ErrorResult:
        """Handle Discord API errors with appropriate retry logic."""
        import discord
        
        if isinstance(error, discord.errors.RateLimited):
            logger.warning(f"Discord rate limited in {context}, retrying after {error.retry_after}s")
            return ErrorResult(should_retry=True, delay_seconds=int(error.retry_after))
        
        elif isinstance(error, discord.errors.Forbidden):
            logger.error(f"Discord permission denied in {context}: {error}")
            return ErrorResult(should_retry=False, escalate=True, 
                             message="Permission denied - check bot permissions")
        
        elif isinstance(error, discord.errors.HTTPException):
            if error.status == 429:  # Rate limited
                retry_after = getattr(error, 'retry_after', 60)
                return ErrorResult(should_retry=True, delay_seconds=retry_after)
            elif 500 <= error.status < 600:  # Server errors
                return ErrorResult(should_retry=True, delay_seconds=30)
            else:  # Client errors
                logger.error(f"Discord client error in {context}: {error}")
                return ErrorResult(should_retry=False, escalate=True)
        
        else:
            logger.error(f"Unexpected Discord error in {context}: {error}")
            return ErrorResult(should_retry=False, escalate=True)
    
    @staticmethod 
    async def handle_database_error(error: Exception, operation: str) -> ErrorResult:
        """Handle database errors with connection recovery."""
        import asyncpg
        
        if isinstance(error, asyncpg.exceptions.ConnectionDoesNotExistError):
            logger.warning(f"Database connection lost during {operation}, will retry")
            return ErrorResult(should_retry=True, delay_seconds=5)
        
        elif isinstance(error, asyncpg.exceptions.TooManyConnectionsError):
            logger.warning(f"Database connection pool exhausted during {operation}")
            return ErrorResult(should_retry=True, delay_seconds=10)
        
        elif isinstance(error, asyncpg.exceptions.InterfaceError):
            logger.error(f"Database interface error during {operation}: {error}")
            return ErrorResult(should_retry=True, delay_seconds=15)
        
        elif isinstance(error, asyncpg.exceptions.PostgresError):
            # Check if it's a transient error
            if error.sqlstate in ['08000', '08003', '08006']:  # Connection errors
                return ErrorResult(should_retry=True, delay_seconds=10)
            else:
                logger.error(f"Database error during {operation}: {error}")
                return ErrorResult(should_retry=False, escalate=True)
        
        else:
            logger.error(f"Unexpected database error during {operation}: {error}")
            return ErrorResult(should_retry=False, escalate=True)
    
    @staticmethod
    async def handle_api_error(error: Exception, api_name: str, context: str) -> ErrorResult:
        """Handle external API errors."""
        import aiohttp
        
        if isinstance(error, aiohttp.ClientTimeout):
            logger.warning(f"{api_name} API timeout in {context}")
            return ErrorResult(should_retry=True, delay_seconds=30)
        
        elif isinstance(error, aiohttp.ClientResponseError):
            if error.status == 429:  # Rate limited
                return ErrorResult(should_retry=True, delay_seconds=60)
            elif 500 <= error.status < 600:  # Server errors
                return ErrorResult(should_retry=True, delay_seconds=30)
            elif error.status == 401:  # Unauthorized
                logger.error(f"{api_name} API authentication failed: {error}")
                return ErrorResult(should_retry=False, escalate=True, 
                                 message="API authentication failed")
            else:
                logger.error(f"{api_name} API client error: {error}")
                return ErrorResult(should_retry=False, escalate=True)
        
        else:
            logger.error(f"Unexpected {api_name} API error in {context}: {error}")
            return ErrorResult(should_retry=False, escalate=True)
```

**Checkpoint 6**: Error handling system implemented
```bash
git add errors/
git commit -m "Phase 1.6: Add standardized error handling system"
```

#### Day 9-10: Database Schema Management

**Step 1: Extract schema definitions**
```bash
mkdir -p database/schema database/migrations
```

**Step 2: Create SQL schema files**
```sql
-- database/schema/001_initial_tables.sql
-- Initial table definitions
CREATE TABLE IF NOT EXISTS Events (
    eventID TEXT PRIMARY KEY,
    name TEXT,
    artistID TEXT,
    venueID TEXT,
    eventDate TIMESTAMPTZ,
    ticketOnsaleStart TIMESTAMPTZ,
    url TEXT,
    image_url TEXT,
    sentToDiscord BOOLEAN DEFAULT FALSE,
    lastUpdated TIMESTAMPTZ,
    reminder TIMESTAMPTZ DEFAULT NULL,
    presaleData JSONB DEFAULT NULL,
    region TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS Venues (
    venueID TEXT PRIMARY KEY,
    name TEXT,
    city TEXT,
    state TEXT
);

CREATE TABLE IF NOT EXISTS Artists (
    artistID TEXT PRIMARY KEY,
    name TEXT,
    notable BOOLEAN DEFAULT FALSE
);

-- database/schema/002_notification_tracking.sql
-- Add notification tracking columns
ALTER TABLE Events 
ADD COLUMN IF NOT EXISTS notification_attempts INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_notification_attempt TIMESTAMPTZ DEFAULT NULL,
ADD COLUMN IF NOT EXISTS notification_error TEXT DEFAULT NULL;

-- database/schema/003_indexes.sql
-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_events_sent_to_discord 
ON Events (sentToDiscord) WHERE sentToDiscord = FALSE;

CREATE INDEX IF NOT EXISTS idx_events_region 
ON Events (region);

CREATE INDEX IF NOT EXISTS idx_events_notification_attempts 
ON Events (notification_attempts) WHERE notification_attempts IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_artists_notable 
ON Artists (notable) WHERE notable = TRUE;
```

**Step 3: Create schema manager**
```python
# database/schema_manager.py
import logging
from typing import List, Dict, Any
import asyncpg
from pathlib import Path

logger = logging.getLogger(__name__)

class Migration:
    """Represents a database migration."""
    
    def __init__(self, version: str, description: str, sql_file: str):
        self.version = version
        self.description = description
        self.sql_file = sql_file
    
    async def apply(self, conn: asyncpg.Connection) -> bool:
        """Apply this migration to the database."""
        try:
            sql_path = Path(__file__).parent / "schema" / self.sql_file
            with open(sql_path, 'r') as f:
                sql_content = f.read()
            
            await conn.execute(sql_content)
            logger.info(f"Applied migration {self.version}: {self.description}")
            return True
        except Exception as e:
            logger.error(f"Failed to apply migration {self.version}: {e}")
            return False

class SchemaManager:
    """Manages database schema with proper migrations."""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.migrations = [
            Migration("001", "Initial tables", "001_initial_tables.sql"),
            Migration("002", "Notification tracking", "002_notification_tracking.sql"),
            Migration("003", "Performance indexes", "003_indexes.sql"),
        ]
    
    async def ensure_schema_current(self) -> bool:
        """Ensure database schema is at current version."""
        async with self.db_pool.acquire() as conn:
            # Create migrations table if it doesn't exist
            await self._create_migrations_table(conn)
            
            # Get current schema version
            current_version = await self._get_current_version(conn)
            
            # Apply pending migrations
            for migration in self.migrations:
                if migration.version > current_version:
                    success = await self._apply_migration(conn, migration)
                    if not success:
                        return False
            
            return True
    
    async def _create_migrations_table(self, conn: asyncpg.Connection):
        """Create migrations tracking table."""
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                description TEXT,
                applied_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
    
    async def _get_current_version(self, conn: asyncpg.Connection) -> str:
        """Get the current schema version."""
        result = await conn.fetchval('''
            SELECT version FROM schema_migrations 
            ORDER BY version DESC LIMIT 1
        ''')
        return result or "000"
    
    async def _apply_migration(self, conn: asyncpg.Connection, migration: Migration) -> bool:
        """Apply a specific migration and record it."""
        async with conn.transaction():
            success = await migration.apply(conn)
            if success:
                await conn.execute('''
                    INSERT INTO schema_migrations (version, description) 
                    VALUES ($1, $2)
                ''', migration.version, migration.description)
            return success
    
    async def get_migration_status(self) -> List[Dict[str, Any]]:
        """Get status of all migrations."""
        async with self.db_pool.acquire() as conn:
            applied_migrations = await conn.fetch('''
                SELECT version, description, applied_at 
                FROM schema_migrations 
                ORDER BY version
            ''')
            
            applied_versions = {row['version'] for row in applied_migrations}
            
            status = []
            for migration in self.migrations:
                status.append({
                    'version': migration.version,
                    'description': migration.description,
                    'applied': migration.version in applied_versions,
                    'sql_file': migration.sql_file
                })
            
            return status
```

**Step 4: Update database initialization**
```python
# database/init.py (updated)
import logging
from config.db_pool import db_pool
from .schema_manager import SchemaManager

logger = logging.getLogger(__name__)

async def initialize_db():
    """Create tables if they do not exist and ensure schema compatibility."""
    logger.info("Initializing the database...")
    
    # Use new schema manager
    schema_manager = SchemaManager(db_pool)
    success = await schema_manager.ensure_schema_current()
    
    if success:
        logger.info("Database schema updated successfully.")
    else:
        logger.error("Failed to update database schema")
        raise Exception("Database schema update failed")
    
    # Log migration status
    status = await schema_manager.get_migration_status()
    for migration in status:
        status_text = "APPLIED" if migration['applied'] else "PENDING"
        logger.info(f"Migration {migration['version']}: {migration['description']} - {status_text}")
```

**Checkpoint 7**: Schema management system complete
```bash
git add database/schema/ database/migrations/ database/schema_manager.py
git commit -m "Phase 1.7: Add database schema management with migrations"
```

## 🧪 Testing Phase 1 Implementation

### Comprehensive Testing
```bash
# Run all tests
python -m pytest tests/ -v --cov=. --cov-report=html

# Test configuration system
python -c "
from config.manager import ConfigurationManager
config = ConfigurationManager.get_region_config('east')
print(f'✓ Configuration: {config.name} - {config.center_point_str}')
"

# Test domain models
python -c "
from domain.models import Event, Artist, Venue
from datetime import datetime, timedelta
artist = Artist('test', 'Test Artist', True)
venue = Venue('test', 'Test Venue', 'Test City', 'TS')
event = Event('test', 'Test Event', artist, venue, 
              datetime.now() + timedelta(days=30),
              datetime.now() + timedelta(days=1),
              'https://example.com')
print(f'✓ Domain Models: Event {event.name} is notable: {event.is_notable()}')
"

# Test error handling
python -c "
from errors.handlers import ErrorHandler
import asyncio
async def test():
    result = await ErrorHandler.handle_database_error(Exception('test'), 'test_op')
    print(f'✓ Error Handling: Should retry: {result.should_retry}')
asyncio.run(test())
"
```

### Phase 1 Completion Checklist
- [ ] Configuration system supports all current regions + easy extension
- [ ] Domain models replace raw dictionary usage in core functions
- [ ] Test runner operational with fixtures for all major components
- [ ] Error handling follows consistent patterns
- [ ] All existing functionality works without changes
- [ ] Database schema management operational
- [ ] Code complexity reduced by 20%

## 🔄 Migration Rollback Procedures

### Emergency Rollback
```bash
# If something goes wrong, quick rollback
git checkout main
git branch -D refactor/phase-1-foundation

# Restore from backup
git checkout backup/pre-refactoring-$(date +%Y%m%d)

# Deploy previous version
heroku releases:rollback --app your-app-name
```

### Selective Rollback
```bash
# Rollback specific components
git revert <commit-hash>  # Revert specific commit

# Disable new configuration system
export USE_NEW_CONFIG=0

# Use legacy configuration
python -c "from config.legacy import get_legacy_config; print(get_legacy_config())"
```

## ⏭️ Next Steps

After completing Phase 1, proceed to [Phase 2: Architecture](PHASE_2_ARCHITECTURE.md) implementation following the same detailed step-by-step approach.

### Phase 2 Preview
- Repository pattern implementation
- Service layer creation  
- Dependency injection setup
- Business logic extraction

The migration guide will continue with detailed Phase 2, 3, and 4 implementations in subsequent documents.
