from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import config

# Create async SQLAlchemy engine
engine = create_async_engine(
    config.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
)

# Factory for async sessions
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


# Dependency to get DB session
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
