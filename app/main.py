from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.base_settings import settings
from app.config.db_settings import sessionmanager


def init_app(init_db=True) -> FastAPI:
    """Инициализирует FastAPI сервер."""
    lifespan = None

    if init_db:
        sessionmanager.init(
            settings.async_database_url, settings.sync_database_url
        )

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            yield
            if sessionmanager._async_engine is not None:
                await sessionmanager.close()

    server = FastAPI(title="FastAPI server", lifespan=lifespan)
    """Объект сервера."""

    from app.views.auth import router as auth_router
    from app.views.image import router as image_router

    server.include_router(auth_router)
    server.include_router(image_router)

    return server


app = init_app()
