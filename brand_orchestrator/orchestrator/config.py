"""Configuration management for the orchestrator."""

import os
from typing import Optional


class Config:
    """Configuration class for orchestrator settings."""

    def __init__(self):
        self.api_key = os.getenv("API_KEY", "")
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///data/orchestrator.db")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls()
