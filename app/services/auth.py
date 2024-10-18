from datetime import datetime
from datetime import timedelta

import jwt
from fastapi import Header
from fastapi import HTTPException
from fastapi import status
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.base_settings import settings
from app.models import User
from app.views.auth import db_dependency

SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_access_token(
    data: dict, expires_delta: timedelta | None = None
):
    """Создает JWT токен с заданными данными и временем истечения.

    Args:
        data (dict): Данные, которые необходимо закодировать в токен.
        expires_delta (Optional[timedelta]): Опциональная дельта
            времени для установки времени истечения.

    Returns:
        str: Закодированный JWT токен.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> User:
    """Аутентифицирует пользователя по его email и паролю.

    Args:
        db (AsyncSession): Асинхронная сессия базы данных.
        email (str): Email пользователя.
        password (str): Пароль пользователя.

    Returns:
        User: Объект пользователя, если аутентификация успешна.

    Raises:
        HTTPException: Если email или пароль неверны.
    """
    user = await User.get_by_email(db, email)
    if not user or not pwd_context.verify(password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    return user


def verify_token(token: str) -> str:
    """Проверяет JWT токен и извлекает email из его полезной нагрузки.

    Args:
        token (str): JWT токен.

    Returns:
        str: Email пользователя, если токен действителен.

    Raises:
        HTTPException: Если токен истек или недействителен.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        return email
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc


async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = db_dependency,
) -> User:
    """Возвращает текущего пользователя по JWT токену.

    Args:
        authorization (str): JWT токен, передаваемый в заголовке Authorization.
        db (AsyncSession): Асинхронная сессия базы данных.

    Returns:
        User: Объект текущего пользователя.

    Raises:
        HTTPException: Если токен недействителен или пользователь не найден.
    """
    token = authorization.split(" ")[1]
    email = verify_token(token)
    user = await User.get_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user
