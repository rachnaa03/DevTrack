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
    GITHUB_API_URL: str = "https://api.github.com"
    GITHUB_RATE_LIMIT_AUTH: int = 5000
    GITHUB_RATE_LIMIT_UNAUTH: int = 60
    GITHUB_RATE_LIMIT_OVERRIDE: int | None = None
    GITHUB_RATE_LIMIT_PERIOD: float = 3600.0
    
    LEETCODE_API_URL: str = "https://leetcode.com/graphql"
    LEETCODE_RATE_LIMIT_MAX: int = 60
    LEETCODE_RATE_LIMIT_OVERRIDE: int | None = None
    LEETCODE_RATE_LIMIT_PERIOD: float = 3600.0
    
    SYNC_INTERVAL_HOURS: int = 12

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
