from datetime import timedelta

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.db_settings import get_async_db
from app.models import User
from app.schemas import UserCreateSchema
from app.schemas import UserLoginSchema
from app.schemas import UserResponseSchema
from app.services.auth import ACCESS_TOKEN_EXPIRE_MINUTES
from app.services.auth import authenticate_user
from app.services.auth import create_access_token
from app.services.auth import pwd_context

router = APIRouter(prefix="/auth", tags=["auth"])


db_dependency: AsyncSession = Depends(get_async_db)


@router.post("/registration", response_model=UserResponseSchema)
async def registration(
    user: UserCreateSchema, db: AsyncSession = db_dependency
) -> UserResponseSchema:
    """Регистрирует нового пользователя.

    Args:
        user (UserCreateSchema): Объект, содержащий данные для
            создания нового пользователя.
        db (AsyncSession): Асинхронная сессия для
            взаимодействия с базой данных.

    Returns:
        UserResponseSchema: Объект, содержащий данные
            о зарегистрированном пользователе.

    Raises:
        HTTPException: Возникает, если пользователь
            с таким email уже существует.
    """
    existing_user = await User.get_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_password = pwd_context.hash(user.password)

    new_user = await User.create(
        db,
        password=hashed_password,
        **user.model_dump(exclude={"password"}),
    )

    return UserResponseSchema.model_validate(new_user)


@router.post("/login")
async def login(
    user: UserLoginSchema, db: AsyncSession = db_dependency
) -> dict:
    """Аутентификация пользователя.

    Args:
        user (UserLoginSchema): Форма аутентификации.
        db (AsyncSession): Асинхронная сессия для
            взаимодействия с базой данных.

    Returns:
        dict: Словарь с полями `access_token` и `token_type`.

    Raises:
        HTTPException: Возникает, если email пользователя
            или пароль неверны.
    """
    auth_user = await authenticate_user(db, user.email, user.password)
    if not auth_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}
