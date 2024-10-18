import asyncio
import io
import os
from contextlib import ExitStack
from pathlib import Path

import pytest
import redis
from dotenv import load_dotenv
from fastapi import FastAPI
from httpx import AsyncClient
from PIL import Image
from PIL.ImageFile import ImageFile
from pytest_postgresql import factories
from pytest_postgresql.janitor import DatabaseJanitor
from redis import Redis

from app.config.celery_settings import celery_app
from app.config.db_settings import get_async_db
from app.config.db_settings import sessionmanager
from app.main import init_app

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

if os.environ.get("TESTING") == "True":
    celery_app.conf.update(task_always_eager=True)


@pytest.fixture(scope="module")
def redis_client() -> Redis:
    client = redis.StrictRedis(host="localhost", port=6379, db=0)
    yield client
    client.close()


@pytest.fixture(autouse=True)
async def app() -> FastAPI:
    with ExitStack():
        yield init_app(init_db=False)


@pytest.fixture
async def httpx_client(app) -> AsyncClient:
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


test_db = factories.postgresql_proc(port=None, dbname="test_db")


@pytest.fixture(scope="session")
def event_loop(request) -> asyncio.AbstractEventLoop:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def connection_test(test_db, event_loop):
    pg_host = test_db.host
    pg_port = test_db.port
    pg_user = test_db.user
    pg_db = test_db.dbname
    pg_password = test_db.password

    with DatabaseJanitor(
        user=pg_user,
        host=pg_host,
        port=pg_port,
        dbname=pg_db,
        version=test_db.version,
        password=pg_password,
    ):
        async_connection_str = (
            f"postgresql+psycopg://{pg_user}:@{pg_host}:{pg_port}/{pg_db}"
        )
        sync_connection_str = (
            f"postgresql://{pg_user}:@{pg_host}:{pg_port}/{pg_db}"
        )
        sessionmanager.init(async_connection_str, sync_connection_str)
        yield
        await sessionmanager.close()


@pytest.fixture(scope="function", autouse=True)
async def create_tables(connection_test) -> None:
    async with sessionmanager.async_connect() as connection:
        await sessionmanager.drop_all_async(connection)
        await sessionmanager.create_all_async(connection)


@pytest.fixture(scope="function", autouse=True)
async def session_override(app, connection_test):
    async def get_db_override():
        async with sessionmanager.async_session() as session:
            yield session

    app.dependency_overrides[get_async_db] = get_db_override


@pytest.fixture(scope="function")
async def image_and_image_data() -> tuple[ImageFile, bytes]:
    """Создает тестовое изображение и возвращает его."""
    img = Image.new("RGB", (100, 100), color="red")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    img_byte_arr.seek(0)
    return Image.open(
        io.BytesIO(img_byte_arr.getvalue())
    ), img_byte_arr.getvalue()
