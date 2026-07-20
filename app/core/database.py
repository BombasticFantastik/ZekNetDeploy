from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

import asyncio
from alembic import command
from alembic.config import Config

from app.core.config import settings


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True, # Отображение запросов, потом поменять на фолс
    future=True
)


async_session_maker = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


def _run_alembic_upgrade():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

async def init_db() -> None:
    await asyncio.to_thread(_run_alembic_upgrade)