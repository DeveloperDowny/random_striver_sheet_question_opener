from pydantic_settings import BaseSettings

class DBConfig(BaseSettings):
    MONGODB_URI: str
    DATABASE_NAME: str