# config.py
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables."""

    telegram_bot_token: str = Field(..., description="Telegram Bot API token")
    server_base_url: str = Field(..., description="Base URL for the backend API server")
    # NEW: The public URL where Telegram will send updates
    webhook_url: str = Field(..., description="Public URL for the Telegram webhook")
    # Optional: A secret token to verify requests from Telegram
    webhook_secret_token: str | None = Field(None, description="Secret token for webhook verification")

    model_config = ConfigDict(
        case_sensitive=False,
        env_file='.env', # Load from .env file if present
        extra='ignore'
    )

# Load settings
bot_config = Settings()