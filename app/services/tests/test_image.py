import asyncio
import uuid

import pytest
from faker import Faker
from httpx import AsyncClient
from PIL import Image
from PIL.ImageFile import ImageFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.db_settings import sessionmanager
from app.models import ImageStatistics
from app.models import ImageTask
from app.models import User
from app.schemas import TransformationEnum
from app.services.image import convert_to_gray
from app.services.image import process_image
from app.services.image import resize_image
from app.services.image import rotate_image

fake = Faker()


class TestProcessImage:
    @pytest.mark.asyncio
    async def test_process_image(
        self,
        httpx_client: AsyncClient,
        image_and_image_data: tuple[ImageFile, bytes],
    ) -> None:
        """Проверяет, что изображение успешно обрабатывается с поворотом."""
        task_id = uuid.uuid4()

        db: AsyncSession = sessionmanager._async_sessionmaker()

        test_user = await User.create(
            db,
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            password=fake.password(),
        )

        process_image(
            image_data=image_and_image_data[1],
            image_name="test_image",
            transformation=TransformationEnum.rotated,
            task_id=task_id,
            user_id=test_user.id,
        )

        image_task = await ImageTask.get_all_by_user_id(db, test_user.id)
        assert image_task is not None

        original_img_link = image_task[0].img_link
        rotated_img_link = image_task[1].img_link
        assert original_img_link == "test_image_original.jpeg"
        assert rotated_img_link == "test_image_rotated.jpeg"

        image_statistics = await ImageStatistics.get_by_image_task_id(
            db, image_task[0].id
        )
        assert image_statistics is not None
        assert image_statistics.width > 0
        assert image_statistics.height > 0

    @pytest.mark.skip(
        "fixme: при запуске по отдельности - все ок, в общем пуле всё блокируется."
    )
    @pytest.mark.asyncio
    async def test_rotate_image(
        self, image_and_image_data: tuple[ImageFile, bytes]
    ) -> None:
        """Проверяет поворот изображения на 90 градусов."""
        rotated_image_data = await asyncio.to_thread(
            rotate_image, image_and_image_data[0]
        )
        rotated_image = Image.open(rotated_image_data)

        assert rotated_image.size == (
            100,
            100,
        ), "Размер изображения должен остаться таким же"

    @pytest.mark.skip(
        "fixme: при запуске по отдельности - все ок, в общем пуле всё блокируется."
    )
    @pytest.mark.asyncio
    async def test_convert_to_gray(
        self, image_and_image_data: tuple[ImageFile, bytes]
    ) -> None:
        """Проверяет преобразование изображения в градации серого."""
        gray_image_data = await asyncio.to_thread(
            convert_to_gray, image_and_image_data[0]
        )
        gray_image = Image.open(gray_image_data)

        assert (
            gray_image.mode == "L"
        ), "Изображение должно быть в градациях серого"

    @pytest.mark.skip(
        "fixme: при запуске по отдельности - все ок, в общем пуле всё блокируется."
    )
    @pytest.mark.asyncio
    async def test_resize_image(
        self, image_and_image_data: tuple[ImageFile, bytes]
    ) -> None:
        """Проверяет изменение размера изображения (увеличение в 2 раза)."""
        resized_image_data = await asyncio.to_thread(
            resize_image, image_and_image_data[0]
        )
        resized_image = Image.open(resized_image_data)

        assert resized_image.size == (
            200,
            200,
        ), "Размер изображения должен быть увеличен в 2 раза"
