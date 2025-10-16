from sqlalchemy.ext.asyncio import create_async_engine, AsyncAttrs
from sqlalchemy.orm import declarative_base
from decouple import config
from typing import cast

DATABASE_URL = cast(str, config("DATABASE_URL", cast=str))

# Create async SQLAlchemy engine
engine = create_async_engine(DATABASE_URL, echo=True)

Base = declarative_base(cls=AsyncAttrs)
