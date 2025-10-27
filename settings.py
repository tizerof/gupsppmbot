import os
from typing import List

from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "gupsppmbot"
    DB_USER: str = "user"
    DB_PASSWORD: str = "password"

    TELEGRAM_BOT_TOKEN: str = ""
    
    ADMIN_IDS: List[int] = []
    
    WEBHOOK_HOST: str = ""
    WEB_SERVER_HOST: str = "0.0.0.0"
    WEB_SERVER_PORT: int = 8000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        # Используем DATABASE_URL из переменной окружения, если доступна (например, от Render)
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            return database_url
        
        # В противном случае строим URL из отдельных компонентов
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

settings = Settings()