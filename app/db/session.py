from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from .base import engine

# Factory for async sessions
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


# Dependency to get DB session
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
