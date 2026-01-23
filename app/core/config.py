from typing import Optional
from decimal import Decimal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False
    SYNC_DATABASE_URL: str = "sqlite:///./test.db"
    ASYNC_DATABASE_URL: str = "sqlite+aiosqlite:///./test.db"
    DATABASE_URL: str = "sqlite:///./test.db"
    JWT_SECRET_KEY: str = "test_jwt_secret_key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CLOUDINARY_CLOUD_NAME: str = "test_cloudinary_cloud_name"
    CLOUDINARY_API_KEY: str = "test_cloudinary_api_key"
    CLOUDINARY_API_SECRET: Optional[str] = None
    APPLICATION_FOLDER: str = "flowcart_app"

    TAX_RATE: Decimal = Decimal("0.1")

    STRIPE_API_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    PAYMENT_PROVIDER: str = "stripe"
    STORAGE_PROVIDER: str = "cloudinary"
    
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "console"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


config = Config()
