import uuid
from datetime import datetime
from enum import Enum

from pydantic import UUID4
from pydantic import BaseModel
from pydantic import EmailStr


class Token(BaseModel):
    """Модель для возврата jwt токена."""

    access_token: str
    token_type: str


class UserEmailSchema(BaseModel):
    """Схема для почты пользователя."""

    email: EmailStr


class UserPasswordSchema(BaseModel):
    """Схема для пароля пользователя."""

    password: str


class UserSchemaBase(UserEmailSchema):
    """Базовая схема для модели User."""

    first_name: str
    last_name: str


class UserCreateSchema(UserSchemaBase, UserPasswordSchema):
    """Схема для создания нового пользователя."""


class UserResponseSchema(UserSchemaBase):
    """Схема для представления данных пользователя."""

    id: uuid.UUID

    class Config:
        from_attributes = True


class UserLoginSchema(UserEmailSchema, UserPasswordSchema):
    """Схема для аутентификации пользователя."""


class TransformationEnum(str, Enum):
    """Enum возможных преобразований."""

    original = "original"
    rotated = "rotated"
    gray = "gray"
    scaled = "scaled"


class UploadResponseSchema(BaseModel):
    """Схема результатов загрузки изображений."""

    success_files: list[str]
    failed_files: list[str]
    successfully_uploaded_to_task_id: dict[str, str]
    message: str


class TaskStatusEnum(str, Enum):
    """Enum статусов celery задачи."""

    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class ImageTaskStatusResponseSchema(BaseModel):
    """Схема для проверки статуса ImageTask."""

    task_id: uuid.UUID
    status: TaskStatusEnum
    image_links: list[str] | None = None

    class Config:
        from_attributes = True


class ImageTaskSchema(BaseModel):
    """Схема для модели ImageTask."""

    id: uuid.UUID
    task_id: uuid.UUID
    img_link: str
    created_at: datetime
    user_id: uuid.UUID


class UserHistoryImageTaskResponseSchema(BaseModel):
    """Схема для возврата всех ImageTask пользователя."""

    user_id: UUID4
    image_tasks: list[ImageTaskSchema]

    class Config:
        from_attributes = True
