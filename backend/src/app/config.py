from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    amadeus_client_id: Optional[str] = None
    amadeus_client_secret: Optional[str] = None
    amadeus_hostname: str = "test"
    cors_origins: str = "http://localhost:5173"
    database_url: str = "sqlite:///./flight_tracker.db"
    scheduler_interval_minutes: int = 60
    smtp_host: str = "localhost"
    smtp_port: int = 25
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_address: str = "alerts@flighttracker.local"
    smtp_use_tls: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
