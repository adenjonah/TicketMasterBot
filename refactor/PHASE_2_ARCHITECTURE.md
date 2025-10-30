# Phase 2: Architecture Refactoring

## 🎯 Overview

**Duration**: 2 weeks (10-12 days)  
**Priority**: High  
**Risk Level**: Medium  
**Team Size**: 2-3 developers

Phase 2 implements clean architecture patterns: Repository pattern for data access, Service layer for business logic, and Dependency Injection for loose coupling. This phase transforms the monolithic functions into a properly layered architecture.

## 🏗️ Architecture Goals

### Current Problems
- **Scattered SQL queries** throughout the codebase
- **Business logic mixed** with infrastructure concerns
- **Tight coupling** between Discord bot and data layer
- **No abstraction** for external API calls
- **Global state** in alternating classifications

### Target Architecture
```
┌─────────────────────────────────────────┐
│           Presentation Layer            │
│  ┌─────────────────┐ ┌─────────────────┐│
│  │ Discord Bot     │ │ API Crawler     ││
│  │ (Commands/UI)   │ │ (Data Ingestion)││
│  └─────────────────┘ └─────────────────┘│
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│             Service Layer               │
│  ┌─────────────────┐ ┌─────────────────┐│
│  │ Notification    │ │ Event Processing││
│  │ Service         │ │ Service         ││
│  └─────────────────┘ └─────────────────┘│
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│           Repository Layer              │
│  ┌─────────────────┐ ┌─────────────────┐│
│  │ Event           │ │ Artist          ││
│  │ Repository      │ │ Repository      ││
│  └─────────────────┘ └─────────────────┘│
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│         Infrastructure Layer            │
│  ┌─────────────────┐ ┌─────────────────┐│
│  │ PostgreSQL      │ │ External APIs   ││
│  │ Database        │ │ (TM, Discord)   ││
│  └─────────────────┘ └─────────────────┘│
└─────────────────────────────────────────┘
```

## 📅 Week-by-Week Breakdown

### Week 3: Repository Pattern & Data Access

#### Days 1-3: Repository Pattern Implementation
**Goal**: Abstract all database operations behind repository interfaces

**Current Problem**:
```python
# Scattered throughout codebase
async with db_pool.acquire() as conn:
    events = await conn.fetch('''
        SELECT Events.eventID, Events.name, ... 
        FROM Events
        LEFT JOIN Artists ON Events.artistID = Artists.artistID
        WHERE Events.sentToDiscord = FALSE
    ''')
```

**Target Solution**:
```python
# repositories/interfaces.py
from abc import ABC, abstractmethod
from typing import List, Optional
from domain.models import Event, Artist, Venue

class EventRepository(ABC):
    """Abstract interface for event data access."""
    
    @abstractmethod
    async def save(self, event: Event) -> bool:
        """Save an event to storage."""
        pass
    
    @abstractmethod
    async def find_by_id(self, event_id: str) -> Optional[Event]:
        """Find event by ID."""
        pass
    
    @abstractmethod
    async def find_unsent_events(
        self, 
        region: Optional[str] = None, 
        notable_only: bool = False,
        limit: Optional[int] = None
    ) -> List[Event]:
        """Find events that haven't been sent to Discord."""
        pass
    
    @abstractmethod
    async def mark_as_sent(self, event_id: str) -> bool:
        """Mark event as sent to Discord."""
        pass

class ArtistRepository(ABC):
    """Abstract interface for artist data access."""
    
    @abstractmethod
    async def save(self, artist: Artist) -> bool:
        pass
    
    @abstractmethod
    async def find_by_id(self, artist_id: str) -> Optional[Artist]:
        pass
    
    @abstractmethod
    async def mark_as_notable(self, artist_id: str) -> bool:
        pass
```

**Implementation Steps**:
1. **Day 1**: Create repository interfaces and PostgreSQL implementations
2. **Day 2**: Implement event repository with all current query patterns
3. **Day 3**: Implement artist and venue repositories

**Deliverables**:
- [ ] `repositories/interfaces.py` - Abstract repository interfaces
- [ ] `repositories/postgresql/` - PostgreSQL implementations
- [ ] `repositories/exceptions.py` - Repository-specific exceptions
- [ ] Migration of existing database queries

#### Days 4-5: Service Layer Creation
**Goal**: Extract business logic into dedicated service classes

**Current Problem**:
```python
# Business logic mixed with infrastructure in tasks/notify_events.py
async def notify_events(bot, channel_id, notable_only=False, region=None):
    # 300+ lines mixing:
    # - Database queries
    # - Business logic
    # - Discord API calls
    # - Error handling
    # - URL processing
```

**Target Solution**:
```python
# services/notification_service.py
class NotificationService:
    """Handles event notification business logic."""
    
    def __init__(
        self, 
        event_repo: EventRepository,
        artist_repo: ArtistRepository,
        discord_client: DiscordClient
    ):
        self.event_repo = event_repo
        self.artist_repo = artist_repo
        self.discord_client = discord_client
    
    async def notify_events(
        self, 
        channel_id: str, 
        region: Optional[str] = None,
        notable_only: bool = False
    ) -> NotificationResult:
        """Send notifications for events matching criteria."""
        # Clean business logic separated from infrastructure
        pass
    
    async def process_new_event(self, event_data: dict) -> Event:
        """Process a newly discovered event."""
        pass
```

**Implementation Steps**:
1. **Day 4**: Create notification service with core business logic
2. **Day 5**: Create event processing service for crawler logic

**Deliverables**:
- [ ] `services/notification_service.py` - Event notification logic
- [ ] `services/event_processing_service.py` - Event processing logic
- [ ] `services/artist_service.py` - Artist management logic
- [ ] `services/exceptions.py` - Service-specific exceptions

#### Days 6-7: Dependency Injection Setup
**Goal**: Implement dependency injection container for loose coupling

**Current Problem**:
```python
# Hard-coded dependencies and runtime imports
from config.db_pool import db_pool  # Runtime import
from tasks.notify_events import notify_events  # Circular import risk
```

**Target Solution**:
```python
# di/container.py
class DIContainer:
    """Dependency injection container for managing object lifecycles."""
    
    def __init__(self):
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
    
    def register_singleton(self, interface: Type[T], implementation: T):
        """Register a singleton instance."""
        self._singletons[interface] = implementation
    
    def register_factory(self, interface: Type[T], factory: Callable[[], T]):
        """Register a factory function."""
        self._factories[interface] = factory
    
    def get(self, service_type: Type[T]) -> T:
        """Resolve a service instance."""
        pass

# di/setup.py
async def setup_container() -> DIContainer:
    """Configure the dependency injection container."""
    container = DIContainer()
    
    # Infrastructure
    db_pool = await create_db_pool()
    container.register_singleton(DatabasePool, db_pool)
    
    # Repositories
    event_repo = PostgreSQLEventRepository(db_pool)
    container.register_singleton(EventRepository, event_repo)
    
    # Services
    notification_service = NotificationService(event_repo, discord_client)
    container.register_singleton(NotificationService, notification_service)
    
    return container
```

**Implementation Steps**:
1. **Day 6**: Create DI container and setup infrastructure
2. **Day 7**: Wire up all services and repositories through DI

**Deliverables**:
- [ ] `di/container.py` - Dependency injection container
- [ ] `di/setup.py` - Container configuration
- [ ] `di/interfaces.py` - Service interfaces
- [ ] Migration of all dependency management

### Week 4: Business Logic Extraction & Integration

#### Days 8-10: Business Logic Extraction
**Goal**: Move all business logic from presentation layer to service layer

**Current Problems**:
- **Notification logic** in `tasks/notify_events.py` (400+ lines)
- **Event processing logic** in `tasks/fetch_and_process.py` (150+ lines)
- **Artist management logic** in command handlers
- **Region classification logic** in `api/alternating_events.py`

**Target Solutions**:

```python
# services/notification_service.py
class NotificationService:
    """Pure business logic for event notifications."""
    
    async def get_events_to_notify(
        self, 
        criteria: NotificationCriteria
    ) -> List[Event]:
        """Get events matching notification criteria."""
        return await self.event_repo.find_unsent_events(
            region=criteria.region,
            notable_only=criteria.notable_only,
            max_attempts=criteria.max_retry_attempts
        )
    
    async def prepare_notification(self, event: Event) -> NotificationMessage:
        """Prepare notification message for an event."""
        return NotificationMessage.from_event(event)
    
    async def send_notification(
        self, 
        message: NotificationMessage, 
        channel: str
    ) -> NotificationResult:
        """Send notification and handle response."""
        # Business logic only - no infrastructure concerns
        pass

# services/event_processing_service.py
class EventProcessingService:
    """Business logic for processing events from external APIs."""
    
    async def process_api_response(
        self, 
        api_data: dict, 
        region: str
    ) -> List[Event]:
        """Convert API response to domain events."""
        pass
    
    async def determine_event_significance(self, event: Event) -> EventSignificance:
        """Determine if event should be treated as notable."""
        pass
    
    async def classify_event_region(self, event: Event) -> str:
        """Determine appropriate region classification for event."""
        pass

# services/region_strategy_service.py
class RegionStrategyService:
    """Manages region-specific API strategies."""
    
    def get_strategy(self, region: str) -> RegionStrategy:
        """Get appropriate strategy for region."""
        if region in ['comedy', 'theater', 'film']:
            return AlternatingClassificationStrategy(region)
        else:
            return StandardRegionStrategy(region)
```

**Implementation Steps**:
1. **Day 8**: Extract notification business logic
2. **Day 9**: Extract event processing business logic  
3. **Day 10**: Extract region strategy and artist management logic

**Deliverables**:
- [ ] Complete business logic extraction from all presentation layer files
- [ ] Clean separation between business rules and infrastructure
- [ ] Comprehensive service layer tests
- [ ] Performance benchmarking to ensure no regression

#### Days 11-12: Integration & Testing
**Goal**: Integrate all layers and ensure system works end-to-end

**Integration Tasks**:
1. **Wire up new architecture** in main entry points (`newbot.py`, `crawler.py`)
2. **Update command handlers** to use service layer
3. **Configure dependency injection** in application startup
4. **Migrate notification tasks** to use new services
5. **Test end-to-end functionality**

**Implementation Steps**:
1. **Day 11**: Integration and wiring of all components
2. **Day 12**: Comprehensive testing and bug fixes

**Deliverables**:
- [ ] Fully integrated system using new architecture
- [ ] All existing functionality preserved
- [ ] Integration tests passing
- [ ] Performance metrics within acceptable range

## 🔧 Detailed Implementation

### Repository Implementation Example

```python
# repositories/postgresql/event_repository.py
from typing import List, Optional
from repositories.interfaces import EventRepository
from domain.models import Event
from database.connection import DatabasePool

class PostgreSQLEventRepository(EventRepository):
    """PostgreSQL implementation of event repository."""
    
    def __init__(self, db_pool: DatabasePool):
        self.db_pool = db_pool
    
    async def save(self, event: Event) -> bool:
        """Save an event to PostgreSQL database."""
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO Events (
                        eventID, name, artistID, venueID, eventDate, 
                        ticketOnsaleStart, url, image_url, region
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (eventID) DO NOTHING
                """, 
                    event.id, event.name, 
                    event.artist.id if event.artist else None,
                    event.venue.id, event.event_date, event.sale_date,
                    event.url, event.image_url, event.region
                )
                return True
            except Exception as e:
                # Log error and re-raise as repository exception
                raise RepositoryError(f"Failed to save event {event.id}") from e
    
    async def find_unsent_events(
        self, 
        region: Optional[str] = None,
        notable_only: bool = False,
        limit: Optional[int] = None
    ) -> List[Event]:
        """Find events that haven't been sent to Discord."""
        query_parts = ["""
            SELECT 
                e.eventID, e.name, e.eventDate, e.ticketOnsaleStart,
                e.url, e.image_url, e.region,
                a.artistID, a.name as artist_name, a.notable,
                v.venueID, v.name as venue_name, v.city, v.state
            FROM Events e
            LEFT JOIN Artists a ON e.artistID = a.artistID  
            LEFT JOIN Venues v ON e.venueID = v.venueID
            WHERE e.sentToDiscord = FALSE
            AND (e.notification_attempts IS NULL OR e.notification_attempts < 3)
        """]
        
        params = []
        param_count = 0
        
        if notable_only:
            query_parts.append("AND a.notable = TRUE")
        else:
            query_parts.append("AND (a.notable = FALSE OR a.notable IS NULL)")
        
        if region:
            param_count += 1
            if region == 'eu':
                query_parts.append(f"AND LOWER(e.region) = ${param_count}")
                params.append('eu')
            elif region == 'non-eu':
                query_parts.append(f"AND (LOWER(e.region) != ${param_count} OR e.region IS NULL)")
                params.append('eu')
        
        if limit:
            param_count += 1
            query_parts.append(f"LIMIT ${param_count}")
            params.append(limit)
        
        query = " ".join(query_parts)
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_event(row) for row in rows]
    
    def _row_to_event(self, row) -> Event:
        """Convert database row to Event domain object."""
        artist = None
        if row['artistid']:
            artist = Artist(
                id=row['artistid'],
                name=row['artist_name'],
                is_notable=row['notable'] or False
            )
        
        venue = Venue(
            id=row['venueid'],
            name=row['venue_name'],
            city=row['city'],
            state=row['state']
        )
        
        return Event(
            id=row['eventid'],
            name=row['name'],
            artist=artist,
            venue=venue,
            event_date=row['eventdate'],
            sale_date=row['ticketonsalestart'],
            url=row['url'],
            image_url=row['image_url'],
            region=row['region']
        )
```

### Service Implementation Example

```python
# services/notification_service.py
from typing import List, Optional
from dataclasses import dataclass
from repositories.interfaces import EventRepository
from domain.models import Event
from .exceptions import NotificationError

@dataclass
class NotificationCriteria:
    """Criteria for selecting events to notify."""
    region: Optional[str] = None
    notable_only: bool = False
    max_retry_attempts: int = 3
    limit: Optional[int] = None

@dataclass
class NotificationResult:
    """Result of notification operation."""
    event_id: str
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None

@dataclass
class NotificationSummary:
    """Summary of batch notification operation."""
    total_attempted: int
    successful: int
    failed: int
    results: List[NotificationResult]

class NotificationService:
    """Service for handling event notifications."""
    
    def __init__(
        self, 
        event_repo: EventRepository,
        discord_client,  # Will be properly typed in later phase
        url_processor
    ):
        self.event_repo = event_repo
        self.discord_client = discord_client
        self.url_processor = url_processor
    
    async def notify_events(
        self, 
        channel_id: str,
        criteria: NotificationCriteria
    ) -> NotificationSummary:
        """Send notifications for events matching criteria."""
        events = await self.event_repo.find_unsent_events(
            region=criteria.region,
            notable_only=criteria.notable_only,
            limit=criteria.limit
        )
        
        results = []
        for event in events:
            try:
                result = await self._notify_single_event(event, channel_id)
                results.append(result)
                
                if result.success:
                    await self.event_repo.mark_as_sent(event.id)
                    
            except Exception as e:
                results.append(NotificationResult(
                    event_id=event.id,
                    success=False,
                    error=str(e)
                ))
        
        return NotificationSummary(
            total_attempted=len(events),
            successful=sum(1 for r in results if r.success),
            failed=sum(1 for r in results if not r.success),
            results=results
        )
    
    async def _notify_single_event(
        self, 
        event: Event, 
        channel_id: str
    ) -> NotificationResult:
        """Send notification for a single event."""
        try:
            # Prepare notification message
            embed = self._create_event_embed(event)
            
            # Send to Discord
            message = await self.discord_client.send_embed(channel_id, embed)
            
            if message and message.id:
                return NotificationResult(
                    event_id=event.id,
                    success=True,
                    message_id=str(message.id)
                )
            else:
                return NotificationResult(
                    event_id=event.id,
                    success=False,
                    error="No message object returned from Discord"
                )
                
        except Exception as e:
            return NotificationResult(
                event_id=event.id,
                success=False,
                error=str(e)
            )
    
    def _create_event_embed(self, event: Event):
        """Create Discord embed for event notification."""
        # Business logic for creating notification message
        pass
```

### Dependency Injection Setup

```python
# di/setup.py
from typing import Dict, Any
from .container import DIContainer
from repositories.interfaces import EventRepository, ArtistRepository
from repositories.postgresql.event_repository import PostgreSQLEventRepository
from repositories.postgresql.artist_repository import PostgreSQLArtistRepository
from services.notification_service import NotificationService
from services.event_processing_service import EventProcessingService

async def create_application_container(config) -> DIContainer:
    """Create and configure the main application container."""
    container = DIContainer()
    
    # Infrastructure layer
    db_pool = await create_database_pool(config.database_url)
    container.register_singleton(DatabasePool, db_pool)
    
    discord_client = await create_discord_client(config.discord_token)
    container.register_singleton(DiscordClient, discord_client)
    
    # Repository layer
    event_repo = PostgreSQLEventRepository(db_pool)
    container.register_singleton(EventRepository, event_repo)
    
    artist_repo = PostgreSQLArtistRepository(db_pool)
    container.register_singleton(ArtistRepository, artist_repo)
    
    # Service layer
    notification_service = NotificationService(
        event_repo=event_repo,
        discord_client=discord_client,
        url_processor=URLProcessor()
    )
    container.register_singleton(NotificationService, notification_service)
    
    event_processing_service = EventProcessingService(
        event_repo=event_repo,
        artist_repo=artist_repo
    )
    container.register_singleton(EventProcessingService, event_processing_service)
    
    return container

# Integration in main application
async def main():
    """Main application entry point."""
    config = ConfigurationManager.load_from_environment()
    container = await create_application_container(config)
    
    # Start application with injected dependencies
    notification_service = container.get(NotificationService)
    # ... rest of application logic
```

## 🧪 Testing Strategy

### Repository Testing
```python
# tests/integration/test_repositories.py
import pytest
from repositories.postgresql.event_repository import PostgreSQLEventRepository
from domain.models import Event, Artist, Venue

@pytest.mark.asyncio
class TestEventRepository:
    """Integration tests for event repository."""
    
    async def test_save_and_retrieve_event(self, db_pool, sample_event):
        """Test saving and retrieving an event."""
        repo = PostgreSQLEventRepository(db_pool)
        
        # Save event
        success = await repo.save(sample_event)
        assert success
        
        # Retrieve event
        retrieved = await repo.find_by_id(sample_event.id)
        assert retrieved is not None
        assert retrieved.id == sample_event.id
        assert retrieved.name == sample_event.name
    
    async def test_find_unsent_events_filters(self, db_pool, sample_events):
        """Test filtering of unsent events."""
        repo = PostgreSQLEventRepository(db_pool)
        
        # Save test events
        for event in sample_events:
            await repo.save(event)
        
        # Test notable only filter
        notable_events = await repo.find_unsent_events(notable_only=True)
        assert all(event.is_notable() for event in notable_events)
        
        # Test region filter
        eu_events = await repo.find_unsent_events(region='eu')
        assert all(event.region == 'eu' for event in eu_events)
```

### Service Testing
```python
# tests/unit/test_notification_service.py
import pytest
from unittest.mock import AsyncMock, Mock
from services.notification_service import NotificationService, NotificationCriteria

@pytest.mark.asyncio
class TestNotificationService:
    """Unit tests for notification service."""
    
    async def test_notify_events_success(self):
        """Test successful event notification."""
        # Arrange
        mock_event_repo = AsyncMock()
        mock_discord_client = AsyncMock()
        mock_url_processor = Mock()
        
        sample_events = [create_sample_event()]
        mock_event_repo.find_unsent_events.return_value = sample_events
        mock_discord_client.send_embed.return_value = Mock(id="12345")
        
        service = NotificationService(
            event_repo=mock_event_repo,
            discord_client=mock_discord_client,
            url_processor=mock_url_processor
        )
        
        # Act
        criteria = NotificationCriteria(region='us', notable_only=True)
        result = await service.notify_events("channel123", criteria)
        
        # Assert
        assert result.successful == 1
        assert result.failed == 0
        mock_event_repo.mark_as_sent.assert_called_once_with(sample_events[0].id)
```

## 📋 Deliverables Checklist

### Repository Layer
- [ ] `repositories/interfaces.py` - Abstract repository interfaces
- [ ] `repositories/postgresql/event_repository.py` - Event data access
- [ ] `repositories/postgresql/artist_repository.py` - Artist data access
- [ ] `repositories/postgresql/venue_repository.py` - Venue data access
- [ ] `repositories/exceptions.py` - Repository-specific exceptions
- [ ] Migration of all existing database queries
- [ ] Comprehensive repository tests

### Service Layer
- [ ] `services/notification_service.py` - Event notification logic
- [ ] `services/event_processing_service.py` - Event processing logic
- [ ] `services/artist_service.py` - Artist management logic
- [ ] `services/region_strategy_service.py` - Region classification logic
- [ ] `services/exceptions.py` - Service-specific exceptions
- [ ] Business logic extraction complete
- [ ] Comprehensive service tests

### Dependency Injection
- [ ] `di/container.py` - DI container implementation
- [ ] `di/setup.py` - Container configuration
- [ ] `di/interfaces.py` - Service interfaces
- [ ] Integration in main entry points
- [ ] All dependencies properly managed

### Integration
- [ ] Updated `newbot.py` to use new architecture
- [ ] Updated `crawler.py` to use new architecture
- [ ] All command handlers using service layer
- [ ] Performance benchmarks within acceptable range
- [ ] End-to-end integration tests passing

## 🎯 Phase 2 Completion Criteria

### Technical Criteria
- [ ] Repository pattern implemented for all data access
- [ ] Service layer handles all business logic
- [ ] Dependency injection operational across application
- [ ] Clean separation of concerns achieved
- [ ] All existing functionality preserved
- [ ] Code complexity reduced by 30%

### Business Criteria
- [ ] All bot commands work unchanged
- [ ] All crawler functionality preserved
- [ ] Discord notifications work exactly as before
- [ ] Performance within 10% of baseline
- [ ] No new bugs introduced

### Quality Criteria
- [ ] 60%+ test coverage achieved
- [ ] All critical business logic tested
- [ ] Integration tests validate end-to-end flows
- [ ] Code follows SOLID principles
- [ ] Documentation updated for new architecture

**Next Phase**: [Phase 3: Testing & Quality](PHASE_3_TESTING.md) - Comprehensive test coverage and quality gates
