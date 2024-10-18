import uuid
from collections.abc import Sequence
from datetime import datetime
from logging import getLogger

from pydantic import EmailStr
from sqlalchemy import UUID
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.orm import relationship

from app.config.db_settings import Base

logger = getLogger(__name__)


class User(Base):
    """Модель пользователя"""

    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String)
    created_at = Column(DateTime, default=datetime.now)

    tasks = relationship("ImageTask", back_populates="user")

    @classmethod
    async def create(cls, db: AsyncSession, id=None, **kwargs) -> "User":
        """Создает экземпляр модели User."""
        if not id:
            id = uuid.uuid4()

        user = cls(id=id, **kwargs)
        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"Создан новый пользователь, id: {user.id}")

        return user

    @classmethod
    async def get_by_id(cls, db: AsyncSession, id: uuid.UUID) -> "User | None":
        """Возвращает экземпляр модели User по id."""
        try:
            user = await db.get(cls, id)
        except NoResultFound:
            return None
        return user

    @classmethod
    async def get_by_email(
        cls, db: AsyncSession, email: EmailStr
    ) -> "User | None":
        """Возвращает экземпляр модели User по email."""
        user = (
            (await db.execute(select(cls).where(cls.email == email)))
            .scalars()
            .first()
        )
        return user

    @classmethod
    async def get_all(cls, db: AsyncSession) -> Sequence["User"]:
        """Возвращает все экземпляры User."""
        return (await db.execute(select(cls))).scalars().all()


class ImageTask(Base):
    """Модель задачи обработки изображения"""

    __tablename__ = "image_tasks"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    task_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        default=uuid.uuid4,
    )
    img_link = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    user = relationship("User", back_populates="tasks")
    statistics = relationship(
        "ImageStatistics",
        back_populates="image_task",
        cascade="all, delete-orphan",
        uselist=False,
    )

    @classmethod
    async def create(cls, db: AsyncSession, id=None, **kwargs) -> "ImageTask":
        """Создает экземпляр модели ImageTask."""
        if not id:
            id = uuid.uuid4()

        image_task = cls(id=id, **kwargs)
        db.add(image_task)
        await db.commit()
        await db.refresh(image_task)

        return image_task

    @classmethod
    def sync_create(cls, db: Session, id=None, **kwargs) -> "ImageTask":
        """Синхронно создает экземпляр модели ImageTask."""
        if not id:
            id = uuid.uuid4()

        image_task = cls(id=id, **kwargs)
        db.add(image_task)
        db.commit()
        db.refresh(image_task)

        return image_task

    @classmethod
    async def get_by_id(
        cls, db: AsyncSession, id: uuid.UUID
    ) -> "ImageTask | None":
        """Возвращает экземпляр модели ImageTask по id."""
        try:
            image_task = await db.get(cls, id)
        except NoResultFound:
            return None
        return image_task

    @classmethod
    async def get_by_user_id(
        cls, db: AsyncSession, user_id: uuid.UUID
    ) -> "ImageTask | None":
        """Возвращает экземпляр ImageTask по user_id."""
        image_tasks = (
            (await db.execute(select(cls).where(cls.user_id == user_id)))
            .scalars()
            .first()
        )
        return image_tasks

    @classmethod
    async def get_all_by_user_id(
        cls, db: AsyncSession, user_id: uuid.UUID
    ) -> Sequence["ImageTask"]:
        """Возвращает экземпляры ImageTask по user_id."""
        image_tasks = (
            (await db.execute(select(cls).where(cls.user_id == user_id)))
            .scalars()
            .all()
        )
        return image_tasks

    @classmethod
    async def get_all_by_task_id(
        cls, db: AsyncSession, task_id: uuid.UUID
    ) -> Sequence["ImageTask"]:
        """Возвращает экземпляры ImageTask по task_id."""
        image_tasks = (
            (await db.execute(select(cls).where(cls.task_id == task_id)))
            .scalars()
            .all()
        )
        return image_tasks

    @classmethod
    async def get_all(cls, db: AsyncSession) -> Sequence["ImageTask"]:
        """Возвращает все экземпляры ImageTask."""
        return (await db.execute(select(cls))).scalars().all()


class ImageStatistics(Base):
    """Модель для хранения статистики обработанных изображений."""

    __tablename__ = "image_statistics"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    image_task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("image_tasks.id"),
        nullable=False,
    )
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    processing_time = Column(Float, nullable=False)

    image_task = relationship(
        "ImageTask",
        back_populates="statistics",
    )

    @classmethod
    async def create(
        cls, db: AsyncSession, id=None, **kwargs
    ) -> "ImageStatistics":
        """Создает экземпляр модели ImageStatistics."""
        if not id:
            id = uuid.uuid4()

        image_statistics = cls(id=id, **kwargs)
        db.add(image_statistics)
        await db.commit()
        await db.refresh(image_statistics)

        return image_statistics

    @classmethod
    def sync_create(cls, db: Session, id=None, **kwargs) -> "ImageStatistics":
        """Синхронно создает экземпляр модели ImageStatistics."""
        if not id:
            id = uuid.uuid4()

        image_statistics = cls(id=id, **kwargs)
        db.add(image_statistics)
        db.commit()
        db.refresh(image_statistics)

        return image_statistics

    @classmethod
    async def get_by_id(
        cls, db: AsyncSession, id: uuid.UUID
    ) -> "ImageStatistics | None":
        """Возвращает экземпляр модели ImageStatistics по id."""
        try:
            image_statistics = await db.get(cls, id)
        except NoResultFound:
            return None
        return image_statistics

    @classmethod
    async def get_by_image_task_id(
        cls, db: AsyncSession, image_task_id: uuid.UUID
    ) -> "ImageStatistics":
        """Возвращает экземпляр модели по image_task_id."""
        image_statistics = (
            (
                await db.execute(
                    select(cls).where(cls.image_task_id == image_task_id)
                )
            )
            .scalars()
            .first()
        )
        return image_statistics

    @classmethod
    async def get_all_by_image_task_id(
        cls, db: AsyncSession, image_task_id: uuid.UUID
    ) -> Sequence["ImageStatistics"]:
        """Возвращает экземпляры модели по image_task_id."""
        image_statistics = (
            (
                await db.execute(
                    select(cls).where(cls.image_task_id == image_task_id)
                )
            )
            .scalars()
            .all()
        )
        return image_statistics

    @classmethod
    async def get_all(cls, db: AsyncSession) -> Sequence["ImageStatistics"]:
        """Возвращает все экземпляры ImageStatistics."""
        return (await db.execute(select(cls))).scalars().all()


all_models = tuple(subclass for subclass in Base.__subclasses__())
"""Кортеж содержащий все зарегистрированные модели."""
