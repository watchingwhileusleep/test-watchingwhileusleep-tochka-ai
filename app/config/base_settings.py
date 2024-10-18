from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Базовые настройки приложения."""

    async_database_url: str
    sync_database_url: str
    secret_key: str
    celery_broker_url: str
    celery_result_backend: str
    minio_url: str
    minio_access_key: str
    minio_secret_key: str
    minio_download_url: str
    bucket_name: str
    testing: bool

    class Config:
        env_file = ".env"


settings = Settings()
"""Базовые настройки приложения."""
