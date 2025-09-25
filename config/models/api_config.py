"""API configuration model."""

from dataclasses import dataclass


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
        
        # Basic validation of database URL format
        if not (self.database_url.startswith('postgresql://') or 
                self.database_url.startswith('postgres://')):
            raise ValueError("Database URL must be a valid PostgreSQL connection string")
