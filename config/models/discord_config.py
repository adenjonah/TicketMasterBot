"""Discord configuration model."""

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
        
        # Validate main channels
        for channel_name, channel_id in [
            ("main_channel_id", self.main_channel_id),
            ("secondary_channel_id", self.secondary_channel_id)
        ]:
            if channel_id <= 0:
                raise ValueError(f"Invalid {channel_name}: {channel_id}")
        
        # European channels can be 0 (disabled) but if set, must be positive
        for channel_name, channel_id in [
            ("european_channel_id", self.european_channel_id),
            ("european_secondary_channel_id", self.european_secondary_channel_id)
        ]:
            if channel_id < 0:
                raise ValueError(f"Invalid {channel_name}: {channel_id} (can be 0 for disabled)")
    
    def has_european_channels(self) -> bool:
        """Check if European channels are configured."""
        return self.european_channel_id > 0 and self.european_secondary_channel_id > 0
