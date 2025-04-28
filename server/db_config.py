# -*- coding: utf-8 -*-
"""
Database configuration for the SheetHandler API.
Uses Pydantic for settings management and validation.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from pydantic_settings import BaseSettings


class DBConfig(BaseSettings):
    """Database configuration using Pydantic settings."""
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # MongoDB connection settings
    MONGODB_URI: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URI"
    )
    DATABASE_NAME: str = Field(
        default="sheet_roulette",
        description="Name of the MongoDB database"
    )
    
    # Optional connection pool settings
    MAX_POOL_SIZE: Optional[int] = Field(
        default=100,
        description="Maximum number of connections in the pool"
    )
    MIN_POOL_SIZE: Optional[int] = Field(
        default=10,
        description="Minimum number of connections in the pool"
    )
    
    # Optional timeout settings
    CONNECTION_TIMEOUT_MS: Optional[int] = Field(
        default=5000,
        description="Connection timeout in milliseconds"
    )
    SERVER_SELECTION_TIMEOUT_MS: Optional[int] = Field(
        default=30000,
        description="Server selection timeout in milliseconds"
    )