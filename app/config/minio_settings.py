import socket
from logging import getLogger
from unittest.mock import Mock

import aioboto3
from botocore.config import Config
from minio import Minio

from app.config.base_settings import settings

logger = getLogger(__name__)


def is_minio_available(minio_url: str) -> bool:
    """Проверяет, доступен ли Minio по переданному адресу."""
    try:
        host, port = minio_url.split(":")
        socket.create_connection((host, int(port)), timeout=5)
        return True
    except OSError:
        return False


async def get_minio_session():
    """Возвращает асинхронный клиент для работы с MinIO."""
    if is_minio_available(settings.minio_url):
        session = aioboto3.Session()
        client = session.client(
            "s3",
            endpoint_url=settings.minio_download_url,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            use_ssl=False,
            config=Config(
                connect_timeout=20,
                read_timeout=120,
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )
        return client
    else:
        logger.warning("\n\nMinIO не доступен. Продолжаем c Mock()\n\n")
        mock_client = Mock()
        mock_client.get_object = Mock(
            return_value={"Body": Mock(read=Mock(return_value=b"Mock data"))}
        )
        return mock_client


if is_minio_available(settings.minio_url):
    minio_client = Minio(
        settings.minio_url,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False,
    )
    """Клиент для работы с MinIO."""

    if not minio_client.bucket_exists(settings.bucket_name):
        minio_client.make_bucket(settings.bucket_name)
else:
    minio_client = Mock()
    logger.warning(
        "\n\nMinIO не доступен. Продолжаем с minio_client = Mock()\n\n"
    )
