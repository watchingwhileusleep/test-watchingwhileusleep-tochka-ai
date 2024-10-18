from celery import Celery

from app.config.base_settings import settings
from app.config.db_settings import sessionmanager


if sessionmanager._async_sessionmaker is None:
    sessionmanager.init(
        settings.async_database_url, settings.sync_database_url
    )


celery_app = Celery(
    "tasks",
    broker=settings.celery_broker_url,
)
"""Объект Celery."""


celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    worker_send_task_events=True,
    task_always_eager=False,
    # Настройка asyncio backend
    worker_concurrency=1,
    task_ignore_result=False,
    result_backend=settings.celery_result_backend,
)


celery_app.autodiscover_tasks(["app"])
