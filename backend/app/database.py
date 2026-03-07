from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Create engine only if DATABASE_URL is configured
_db_url = settings.DATABASE_URL
if _db_url:
    engine = create_async_engine(_db_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
else:
    engine = None
    async_session = None


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session
