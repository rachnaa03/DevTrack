from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Core Server Settings
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    LOG_LEVEL: str = "INFO"
    
    # Database Settings
    DATABASE_URL: str
    
    # JWT Security Settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # External Platform Integration Settings
    GITHUB_API_TOKEN: str | None = None
    SYNC_INTERVAL_HOURS: int = 12

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
