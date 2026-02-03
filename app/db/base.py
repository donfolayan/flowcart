from app.core.config import config
from sqlalchemy.ext.asyncio import create_async_engine, AsyncAttrs
from sqlalchemy.orm import declarative_base

DATABASE_URL = config.DATABASE_URL

# Create async SQLAlchemy engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
)

Base = declarative_base(cls=AsyncAttrs)
