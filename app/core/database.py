from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# 1. Asynchronous SQLAlchemy Engine using asyncpg
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.ENVIRONMENT == "development" and settings.LOG_LEVEL == "DEBUG"),
    future=True,
)

# 2. Asynchronous Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 3. Declarative Base for future SQLAlchemy ORM models
class Base(AsyncAttrs, DeclarativeBase):
    pass

# 4. Dependency for FastAPI route handlers and repositories
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an asynchronous database session context."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
