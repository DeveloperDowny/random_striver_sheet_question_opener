from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables."""

    telegram_bot_token: str = Field(..., description="Telegram Bot API token")
    server_base_url: str = Field(..., description="Base URL for API server")

    model_config = ConfigDict(case_sensitive=False)
