import uuid
import zipfile

from celery.result import AsyncResult
from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi import status as status_code
from fastapi.responses import FileResponse
from httpx import HTTPStatusError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.celery_settings import celery_app
from app.config.db_settings import get_async_db
from app.models import ImageTask
from app.models import User
from app.schemas import ImageTaskSchema
from app.schemas import ImageTaskStatusResponseSchema
from app.schemas import TaskStatusEnum
from app.schemas import TransformationEnum
from app.schemas import UploadResponseSchema
from app.schemas import UserHistoryImageTaskResponseSchema
from app.services.auth import get_current_user
from app.services.image import download_image
from app.tasks import process_image_task

router = APIRouter(prefix="/image", tags=["image"])

ALLOWED_EXTENSIONS = ("jpg", "jpeg", "png", "JPG", "JPEG", "PNG")


current_user_dependency: User = Depends(get_current_user)
db_dependency: AsyncSession = Depends(get_async_db)


def validate_file_extension(file: UploadFile) -> bool:
    """
    Проверяет, имеет ли файл допустимое расширение.

    Args:
        file (UploadFile): Загружаемый файл.

    Returns:
        bool: True, если файл имеет допустимое расширение, иначе False.
    """

    file_extension = file.filename.split(".")[-1].lower()
    return file_extension in ALLOWED_EXTENSIONS


@router.post(
    "/upload",
    response_model=UploadResponseSchema,
)
async def upload(
    files: list[UploadFile] = File(...),  # noqa
    transformation: TransformationEnum = Form(...),  # noqa
    current_user: User = current_user_dependency,
) -> UploadResponseSchema:
    """Обрабатывает загрузку изображений и инициирует их обработку.

    Args:
        files (list[UploadFile]): Список загружаемых файлов изображений.
        transformation (TransformationEnum): Список преобразований,
            которые необходимо применить к каждому изображению.
        current_user (User): Аутентифицированный пользователь,
            загружающий изображения.

    Returns:
        UploadResponseSchema: успешно загруженные и
            неуспешно загруженные изображения.
    """
    successfully_uploaded = []
    unsupported_files = []
    successfully_uploaded_to_task_id = {}

    for file in files:
        if not validate_file_extension(file):
            unsupported_files.append(file.filename)
            continue

        content = await file.read()
        task = process_image_task.delay(
            content,
            file.filename,
            transformation,
            str(current_user.id),
        )
        successfully_uploaded.append(file.filename)
        successfully_uploaded_to_task_id[file.filename] = task.id

    message = (
        "All files processed successfully."
        if not unsupported_files
        else "Some files were not processed due to unsupported formats."
    )
    result = UploadResponseSchema(
        success_files=successfully_uploaded,
        failed_files=unsupported_files,
        successfully_uploaded_to_task_id=successfully_uploaded_to_task_id,
        message=message,
    )

    return result


@router.get(
    "/status/{task_id}",
    response_model=ImageTaskStatusResponseSchema,
)
async def get_task_status(
    task_id: uuid.UUID,
    current_user: User = current_user_dependency,
    db: AsyncSession = db_dependency,
) -> ImageTaskStatusResponseSchema:
    """Получение статуса задачи по её идентификатору.

    Args:
        task_id (uuid.UUID): Идентификатор задачи.
        current_user (User): Аутентифицированный пользователь.
        db (AsyncSession): Сессия базы данных.

    Returns:
        ImageTaskStatusResponseSchema: Статус задачи и,
            если доступно, её результат.
    """
    task_result = AsyncResult(str(task_id), app=celery_app)
    if not task_result or task_result.state == TaskStatusEnum.PENDING:
        raise HTTPException(
            status_code=status_code.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    img_links = []
    if task_result.state == TaskStatusEnum.SUCCESS:
        image_tasks = await ImageTask.get_all_by_task_id(db, task_id)

        for image_task in image_tasks:
            img_links.append(image_task.img_link)

    return ImageTaskStatusResponseSchema(
        task_id=task_id,
        status=task_result.state,
        image_links=img_links,
    )


@router.get(
    "/history/{user_id}",
    response_model=UserHistoryImageTaskResponseSchema,
)
async def get_user_history(
    user_id: uuid.UUID,
    current_user: User = current_user_dependency,
    db: AsyncSession = db_dependency,
) -> UserHistoryImageTaskResponseSchema:
    """Получение истории изображений пользователя по его идентификатору.

    Args:
        user_id (uuid.UUID): переданный id пользователя.
        current_user (User): Аутентифицированный пользователь.
        db (AsyncSession): Асинхронная сессия
            для взаимодействия с базой данных.

    Returns:
        UserHistoryImageTaskResponseSchema: Список задач обработки
            изображений пользователя.
    """
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status_code.HTTP_403_FORBIDDEN,
            detail="You do not have access to it.",
        )

    try:
        image_tasks = await ImageTask.get_all_by_user_id(db, user_id)

        if not image_tasks:
            raise HTTPException(
                status_code=status_code.HTTP_404_NOT_FOUND,
                detail="No tasks found for this user",
            )

        tasks_list = [
            ImageTaskSchema(
                id=image_task.id,
                task_id=image_task.task_id,
                img_link=image_task.img_link,
                created_at=image_task.created_at,
                user_id=image_task.user_id,
            )
            for image_task in image_tasks
        ]

        return UserHistoryImageTaskResponseSchema(
            user_id=user_id,
            image_tasks=tasks_list,
        )
    finally:
        await db.close()


@router.get("/task/{task_id}")
async def download_images(
    task_id: uuid.UUID,
    current_user: User = current_user_dependency,
    db: AsyncSession = db_dependency,
) -> FileResponse:
    """
    Скачивание изображений по заданной задаче в виде zip-архива.

    Args:
        task_id (uuid.UUID): Идентификатор задачи.
        current_user (User): Аутентифицированный пользователь.
        db (AsyncSession): Сессия базы данных.

    Returns:
        FileResponse: Ответ с zip-архивом, содержащим изображения.
    """
    image_tasks = await ImageTask.get_all_by_task_id(db, task_id)
    if not image_tasks:
        raise HTTPException(status_code=404, detail="ImageTask not found.")

    if image_tasks[0].user_id != current_user.id:
        raise HTTPException(
            status_code=status_code.HTTP_403_FORBIDDEN,
            detail="You do not have access to it.",
        )

    zip_filename = f"{task_id}.zip"
    with zipfile.ZipFile(zip_filename, "w") as zip_file:
        for image_task in image_tasks:
            image_filename = image_task.img_link.split("/")[-1]
            try:
                image_data = await download_image(image_task.img_link)
                zip_file.writestr(image_filename, image_data)
            except HTTPStatusError:
                continue

    return FileResponse(
        zip_filename, media_type="application/zip", filename=zip_filename
    )
