# Configuration Specification
**Version:** 1.0.0  
**Status:** Approved  
**Prepared By:** Rachana Gandla  

This document describes the environment variables, configuration parameters, and the Pydantic Settings model used to configure the DevTrack backend.

---

## 1. Setting Management with Pydantic
DevTrack manages configuration settings in a single class `Settings` defined in `app/core/config.py` using `pydantic-settings`.
*   **Key Advantage:** It validates environment variable types at startup, preventing the server from booting if crucial credentials are malformed or missing.

---

## 2. Environment Variables Reference

We maintain a local `.env` file in the project root. Below are the supported configuration parameters:

### 2.1 Core Server Settings
| Variable Name | Data Type | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | String | `development` | Defines app behavior. Options: `development`, `staging`, `production`. |
| `PORT` | Integer | `8000` | Port Uvicorn binds to during local execution. |
| `CORS_ORIGINS` | String | `["http://localhost:3000"]` | JSON array of allowed origins for cross-origin browser requests. |
| `LOG_LEVEL` | String | `INFO` | Standard logger threshold. Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |

### 2.2 Database Settings
| Variable Name | Data Type | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | String | *Required* | Asynchronous SQLAlchemy connection string (e.g. `postgresql+asyncpg://user:pass@localhost:5432/devtrack`). |

### 2.3 JWT Security Settings
| Variable Name | Data Type | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `JWT_SECRET_KEY` | String | *Required* | Cryptographically strong secret key used for signing session tokens. |
| `JWT_ALGORITHM` | String | `HS256` | Cryptographic signature format. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Integer | `15` | Number of minutes an access token remains valid. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Integer | `7` | Duration before a refresh token expires. |

### 2.4 External Platform Integration Settings
| Variable Name | Data Type | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `GITHUB_API_TOKEN` | String | `None` | Optional personal access token (PAT) to increase GitHub API rate limits from 60 to 5000 requests per hour. |
| `SYNC_INTERVAL_HOURS` | Integer | `12` | Frequency of background synchronization runs. |

---

## 3. Configuration Loading Example

The application reads variables from the environment (or a local `.env` file) during bootstrap:

```python
# app/core/config.py
from typing import List
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    LOG_LEVEL: str = "INFO"
    
    DATABASE_URL: str
    
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    GITHUB_API_TOKEN: str | None = None
    SYNC_INTERVAL_HOURS: int = 12

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
```
