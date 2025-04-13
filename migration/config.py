from pydantic_settings import BaseSettings

class Config(BaseSettings):
    MONGODB_URI: str
    DATABASE_NAME: str
    BASE_DIRECTORY: str