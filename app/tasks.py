from app.config.celery_settings import celery_app
from app.schemas import TransformationEnum
from app.services.image import process_image


@celery_app.task(bind=True)
def process_image_task(
    self,
    image_data: bytes,
    image_name: str,
    transformation: TransformationEnum,
    user_id: str,
) -> None:
    """Вызывает сервис обработки изображения."""
    task_id = self.request.id
    process_image(
        image_data=image_data,
        image_name=image_name,
        transformation=transformation,
        task_id=task_id,
        user_id=user_id,
    )
    return task_id
