import contextlib
from collections.abc import AsyncIterator
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
"""Базовый класс модели базы данных."""


class DatabaseSessionManager:
    """
    Менеджер сессий для работы с синхронными и асинхронными базами данных.
    """

    def __init__(self) -> None:
        self._async_engine: AsyncEngine | None = None
        self._sync_engine = None
        self._async_sessionmaker: async_sessionmaker | None = None
        self._sync_sessionmaker = None

    def init(self, async_host: str, sync_host: str) -> None:
        """Инициализация асинхронного и синхронного движка."""
        self._async_engine = create_async_engine(async_host)
        self._async_sessionmaker = async_sessionmaker(
            bind=self._async_engine, autocommit=False
        )

        self._sync_engine = create_engine(sync_host)
        self._sync_sessionmaker = sessionmaker(
            bind=self._sync_engine, autocommit=False
        )

    async def close(self) -> None:
        """Закрывает оба движка при завершении работы."""
        if self._async_engine:
            await self._async_engine.dispose()
            self._async_engine = None
            self._async_sessionmaker = None

        if self._sync_engine:
            self._sync_engine.dispose()
            self._sync_engine = None
            self._sync_sessionmaker = None

    @contextlib.asynccontextmanager
    async def async_connect(self) -> AsyncIterator[AsyncConnection]:
        """Контекстный менеджер для асинхронного подключения."""
        if self._async_engine is None:
            raise Exception("Асинхронный движок не инициализирован.")
        async with self._async_engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @contextlib.asynccontextmanager
    async def async_session(self) -> AsyncIterator[AsyncSession]:
        """Контекстный менеджер для асинхронной сессии."""
        if self._async_sessionmaker is None:
            raise Exception(
                "Асинхронный сессионный фабрикатор не инициализирован."
            )
        session = self._async_sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @contextlib.contextmanager
    def sync_session(self) -> Iterator[Session]:
        """Контекстный менеджер для синхронной сессии."""
        if self._sync_sessionmaker is None:
            raise Exception(
                "Синхронный сессионный фабрикатор не инициализирован."
            )
        session = self._sync_sessionmaker()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    async def create_all_async(self, connection: AsyncConnection) -> None:
        """Создает таблицы для асинхронного движка."""
        await connection.run_sync(Base.metadata.create_all)

    def create_all_sync(self) -> None:
        """Создает таблицы для синхронного движка."""
        Base.metadata.create_all(self._sync_engine)

    async def drop_all_async(self, connection: AsyncConnection) -> None:
        """Удаляет таблицы для асинхронного движка."""
        await connection.run_sync(Base.metadata.drop_all)

    def drop_all_sync(self) -> None:
        """Удаляет таблицы для синхронного движка."""
        Base.metadata.drop_all(self._sync_engine)


sessionmanager = DatabaseSessionManager()


async def get_async_db():
    async with sessionmanager.async_session() as session:
        yield session


def get_sync_db():
    with sessionmanager.sync_session() as session:
        yield session
