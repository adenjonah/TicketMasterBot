"""Region configuration model."""

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
        if not self.name:
            raise ValueError("Region name cannot be empty")
        if not self.classification_id:
            raise ValueError("Classification ID cannot be empty")
