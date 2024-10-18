import io
import time
import uuid
from logging import getLogger

from PIL import Image
from sqlalchemy.orm import Session

from app.config.base_settings import settings
from app.config.db_settings import sessionmanager
from app.config.minio_settings import get_minio_session
from app.config.minio_settings import minio_client
from app.models import ImageStatistics
from app.models import ImageTask
from app.schemas import TransformationEnum

logger = getLogger(__name__)


def process_image(
    image_data: bytes,
    image_name: str,
    transformation: TransformationEnum,
    task_id: uuid.UUID,
    user_id: str,
) -> None:
    """Обрабатывает изображение, применяя указанные преобразования.

    Args:
        image_data (bytes): Данные изображения в байтах.
        image_name (str): Название изображения.
        transformation (TransformationEnum): преобразование,
            которое необходимо применить к изображению.
        task_id (uuid.UUID): uuid celery таски.
        user_id (str): Идентификатор пользователя,
            который загрузил изображение.

    Returns:
        ImageStatistics: Возвращает экземпляр ImageStatistics.
    """
    image = Image.open(io.BytesIO(image_data))

    start_time = time.time()

    original_img_data = io.BytesIO(image_data)
    original_file_name = f"{image_name}_original.{image.format.lower()}"
    minio_client.put_object(
        settings.bucket_name,
        original_file_name,
        original_img_data,
        len(original_img_data.getvalue()),
        content_type="image/jpeg",
    )

    db: Session = sessionmanager._sync_sessionmaker()

    image_task = ImageTask.sync_create(
        db=db,
        task_id=task_id,
        img_link=f"{original_file_name}",
        user_id=user_id,
    )

    suffix = (
        transformation if transformation in list(TransformationEnum) else None
    )
    if not suffix:
        logger.error(f"Incorrect transformation name: {transformation}")
        return

    transformation_to_func = {
        TransformationEnum.rotated.value: rotate_image,
        TransformationEnum.gray.value: convert_to_gray,
        TransformationEnum.scaled.value: resize_image,
    }

    transformation_func = transformation_to_func.get(suffix)
    if not transformation_func:
        logger.error(f"No function found for transformation: {suffix}")
        return

    _image_data = transformation_func(image)

    if suffix and _image_data:
        file_name = f"{image_name}_{suffix.value}.{image.format.lower()}"
        minio_client.put_object(
            bucket_name=settings.bucket_name,
            object_name=file_name,
            data=_image_data,
            length=len(_image_data.getvalue()),
            content_type="image/jpeg",
        )

        ImageTask.sync_create(
            db=db,
            task_id=task_id,
            img_link=f"{file_name}",
            user_id=user_id,
        )

    processing_time = time.time() - start_time

    ImageStatistics.sync_create(
        db=db,
        image_task_id=image_task.id,
        width=image.width,
        height=image.height,
        size_bytes=len(image_data),
        processing_time=processing_time,
    )


def rotate_image(image: Image) -> io.BytesIO:
    """Поворачивает изображение на 90 градусов.

    Args:
        image (Image): Оригинальное изображение.

    Returns:
        io.BytesIO: Данные изображения после поворота.
    """
    rotated_image = image.rotate(90, expand=True)
    rotated_image_data = io.BytesIO()
    rotated_image.save(rotated_image_data, format=image.format)
    rotated_image_data.seek(0)
    return rotated_image_data


def convert_to_gray(image: Image) -> io.BytesIO:
    """Конвертирует изображение в градации серого.

    Args:
        image (Image): Оригинальное изображение.

    Returns:
        io.BytesIO: Данные изображения после преобразования в градации серого.
    """
    gray_image = image.convert("L")
    gray_image_data = io.BytesIO()
    gray_image.save(gray_image_data, format=image.format)
    gray_image_data.seek(0)
    return gray_image_data


def resize_image(image: Image) -> io.BytesIO:
    """Изменяет размер изображения, увеличивая его в 2 раза.

    Args:
        image (Image): Оригинальное изображение.

    Returns:
        io.BytesIO: Данные изображения после изменения размера.
    """
    width, height = image.size
    resized_image = image.resize((width * 2, height * 2))
    resized_image_data = io.BytesIO()
    resized_image.save(resized_image_data, format=image.format)
    resized_image_data.seek(0)
    return resized_image_data


async def download_image(img_link: str) -> bytes:
    """Скачивает изображение по указанной ссылке.

    Args:
        img_link (str): Ссылка на изображение.

    Returns:
        bytes: Данные изображения в байтах.

    Raises:
        Exception: Если загрузка изображения не удалась.
    """
    minio_session = await get_minio_session()

    try:
        async with minio_session as minio_client:
            response = await minio_client.get_object(
                Bucket=settings.bucket_name, Key=img_link
            )

            image_data = bytearray()
            async for chunk in response["Body"].iter_chunks():
                image_data.extend(chunk)

        return image_data
    except Exception as e:
        logger.error(
            f"Во время получения изображения произошла ошибка: {str(e)}"
        )
        raise
