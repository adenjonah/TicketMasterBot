"""Pytest configuration and shared fixtures."""

import pytest
import os
import sys
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


@pytest.fixture(autouse=True)
def clean_environment():
    """Clean environment variables before each test to avoid interference."""
    # Store original environment
    original_env = dict(os.environ)
    
    # Clear configuration-related environment variables
    config_vars = [
        'DISCORD_BOT_TOKEN', 'DISCORD_CHANNEL_ID', 'DISCORD_CHANNEL_ID_TWO',
        'EUROPEAN_CHANNEL', 'EUROPEAN_CHANNEL_TWO', 'TICKETMASTER_API_KEY',
        'DATABASE_URL', 'DEBUG_LOGS', 'REGION'
    ]
    
    for var in config_vars:
        if var in os.environ:
            del os.environ[var]
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def sample_environment():
    """Provide a sample environment configuration for testing."""
    return {
        'DISCORD_BOT_TOKEN': 'test_bot_token_12345',
        'DISCORD_CHANNEL_ID': '123456789012345678',
        'DISCORD_CHANNEL_ID_TWO': '876543210987654321',
        'EUROPEAN_CHANNEL': '555666777888999000',
        'EUROPEAN_CHANNEL_TWO': '111222333444555666',
        'TICKETMASTER_API_KEY': 'test_tm_api_key_abcdef',
        'DATABASE_URL': 'postgresql://testuser:testpass@localhost:5432/testdb',
        'DEBUG_LOGS': '0',
        'REGION': 'east'
    }
