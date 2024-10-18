import uuid

import pytest
from faker import Faker
from httpx import AsyncClient
from redis import Redis

from app.config.db_settings import sessionmanager
from app.schemas import TaskStatusEnum
from app.schemas import TransformationEnum

fake = Faker()


class TestImageUpload:
    @pytest.mark.asyncio
    async def test_upload_images_success(
        self, httpx_client: AsyncClient
    ) -> None:
        """Проверяет успешную загрузку изображений."""
        email = fake.email()
        password = fake.password()

        user_data = {
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": email,
            "password": password,
        }
        async with sessionmanager.async_connect():
            await httpx_client.post("/auth/registration", json=user_data)

        response_data = (
            await httpx_client.post(
                "/auth/login", json={"email": email, "password": password}
            )
        ).json()

        file_name_1 = fake.file_name()
        file_name_2 = fake.file_name()
        files = [
            (
                "files",
                (
                    f"{file_name_1}.jpg",
                    fake.image(size=(640, 480), image_format="jpeg"),
                    "image/jpeg",
                ),
            ),
            (
                "files",
                (
                    f"{file_name_2}.png",
                    fake.image(size=(640, 480), image_format="png"),
                    "image/jpeg",
                ),
            ),
        ]

        response = await httpx_client.post(
            "/image/upload",
            data={
                "transformation": TransformationEnum.rotated.value,
            },
            files=files,
            headers={
                "Authorization": f"Bearer {response_data.get("access_token")}"
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert (f"{file_name_1}.jpg", f"{file_name_2}.png") == tuple(
            data.get("success_files")
        )

    @pytest.mark.asyncio
    async def test_upload_images_invalid_extension(
        self, httpx_client: AsyncClient
    ) -> None:
        """Проверяет загрузку изображения с недопустимым расширением."""
        email = fake.email()
        password = fake.password()

        user_data = {
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": email,
            "password": password,
        }

        async with sessionmanager.async_connect():
            await httpx_client.post("/auth/registration", json=user_data)

        response_data = (
            await httpx_client.post(
                "/auth/login", json={"email": email, "password": password}
            )
        ).json()

        file_name = fake.file_name()
        files = [("files", (f"{file_name}.txt", "Some content", "text/plain"))]
        response = await httpx_client.post(
            "/image/upload",
            data={
                "transformation": TransformationEnum.scaled.value,
            },
            files=files,
            headers={
                "Authorization": f"Bearer {response_data.get("access_token")}"
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "failed_files" in data
        assert [f"{file_name}.txt"] == data["failed_files"]


class TestTaskStatus:
    @pytest.mark.skip(
        "fixme: не находит задачу через AsyncResult, вечный pending"
    )
    @pytest.mark.asyncio
    async def test_get_task_status_success(
        self,
        httpx_client: AsyncClient,
        redis_client: Redis,
    ) -> None:
        """Проверяет успешное получение статуса задачи."""
        email = fake.email()
        password = fake.password()

        user_data = {
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": email,
            "password": password,
        }

        async with sessionmanager.async_connect():
            await httpx_client.post("/auth/registration", json=user_data)

        response_data = (
            await httpx_client.post(
                "/auth/login", json={"email": email, "password": password}
            )
        ).json()

        file_name = fake.file_name()
        files = [
            (
                "files",
                (
                    f"{file_name}.jpg",
                    fake.image(size=(640, 480), image_format="jpeg"),
                    "image/jpeg",
                ),
            ),
        ]

        response = await httpx_client.post(
            "/image/upload",
            data={
                "transformation": TransformationEnum.scaled.value,
            },
            files=files,
            headers={
                "Authorization": f"Bearer {response_data.get("access_token")}"
            },
        )

        data = response.json()
        task_id = data.get("successfully_uploaded_to_task_id").get(
            f"{file_name}.jpg"
        )
        assert task_id is not None

        response = await httpx_client.get(
            f"/image/status/{task_id}",
            headers={
                "Authorization": f"Bearer {response_data.get("access_token")}"
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert task_id == data.get("task_id")
        assert data.get("status") == TaskStatusEnum.SUCCESS
        assert len(data.get("image_links")) == 1

    @pytest.mark.asyncio
    async def test_get_task_status_not_found(
        self, httpx_client: AsyncClient
    ) -> None:
        """Проверяет, что возвращается ошибка, если задача не найдена."""
        email = fake.email()
        password = fake.password()

        user_data = {
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": email,
            "password": password,
        }

        async with sessionmanager.async_connect():
            await httpx_client.post("/auth/registration", json=user_data)

        response_data = (
            await httpx_client.post(
                "/auth/login", json={"email": email, "password": password}
            )
        ).json()

        response = await httpx_client.get(
            f"/image/status/{uuid.uuid4().hex}",
            headers={
                "Authorization": f"Bearer {response_data.get("access_token")}"
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"


class TestUserHistory:
    @pytest.mark.asyncio
    async def test_get_user_history_success(
        self, httpx_client: AsyncClient
    ) -> None:
        """Проверяет успешное получение истории изображений пользователя."""
        email = fake.email()
        password = fake.password()

        user_data = {
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": email,
            "password": password,
        }

        async with sessionmanager.async_connect():
            registration_response = (
                await httpx_client.post("/auth/registration", json=user_data)
            ).json()

        login_response = (
            await httpx_client.post(
                "/auth/login", json={"email": email, "password": password}
            )
        ).json()

        file_name = fake.file_name()
        files = [
            (
                "files",
                (
                    f"{file_name}.jpg",
                    fake.image(size=(640, 480), image_format="jpeg"),
                    "image/jpeg",
                ),
            ),
        ]

        await httpx_client.post(
            "/image/upload",
            data={
                "transformation": TransformationEnum.rotated.value,
            },
            files=files,
            headers={
                "Authorization": f"Bearer {login_response.get('access_token')}"
            },
        )

        response = await httpx_client.get(
            f"/image/history/{registration_response.get('id')}",
            headers={
                "Authorization": f"Bearer {login_response.get('access_token')}"
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == registration_response.get("id")
        assert len(data["image_tasks"]) > 0

    @pytest.mark.asyncio
    async def test_get_user_history_forbidden(
        self, httpx_client: AsyncClient
    ) -> None:
        """Проверяет запрет доступа к истории другого пользователя."""
        email1 = fake.email()
        password1 = fake.password()

        user_data_1 = {
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": email1,
            "password": password1,
        }

        async with sessionmanager.async_connect():
            registration_response_1 = (
                await httpx_client.post("/auth/registration", json=user_data_1)
            ).json()

        (
            await httpx_client.post(
                "/auth/login", json={"email": email1, "password": password1}
            )
        ).json()

        email2 = fake.email()
        password2 = fake.password()

        user_data_2 = {
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": email2,
            "password": password2,
        }
        await httpx_client.post("/auth/registration", json=user_data_2)

        response_login_2 = (
            await httpx_client.post(
                "/auth/login", json={"email": email2, "password": password2}
            )
        ).json()

        response = await httpx_client.get(
            f"/image/history/{registration_response_1.get('id')}",
            headers={
                "Authorization": f"Bearer {response_login_2.get('access_token')}"
            },
        )

        assert response.status_code == 403
        assert response.json().get("detail") == "You do not have access to it."


class TestTaskDownload:
    @pytest.mark.asyncio
    async def test_download_images_success(
        self, httpx_client: AsyncClient
    ) -> None:
        """Проверяет успешное скачивание изображений по заданной задаче."""
        email = fake.email()
        password = fake.password()

        user_data = {
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": email,
            "password": password,
        }

        async with sessionmanager.async_connect():
            await httpx_client.post("/auth/registration", json=user_data)

        response_data = (
            await httpx_client.post(
                "/auth/login", json={"email": email, "password": password}
            )
        ).json()

        file_name = fake.file_name()
        files = [
            (
                "files",
                (
                    f"{file_name}.jpg",
                    fake.image(size=(640, 480), image_format="jpeg"),
                    "image/jpeg",
                ),
            ),
        ]

        response = await httpx_client.post(
            "/image/upload",
            data={
                "transformation": TransformationEnum.rotated.value,
            },
            files=files,
            headers={
                "Authorization": f"Bearer {response_data.get('access_token')}"
            },
        )

        data = response.json()
        task_id = data.get("successfully_uploaded_to_task_id").get(
            f"{file_name}.jpg"
        )
        assert task_id is not None

        response = await httpx_client.get(
            f"/image/task/{task_id}",
            headers={
                "Authorization": f"Bearer {response_data.get('access_token')}"
            },
        )

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/zip"
        assert (
            response.headers["Content-Disposition"]
            == f'attachment; filename="{task_id}.zip"'
        )

    @pytest.mark.asyncio
    async def test_download_images_forbidden(
        self, httpx_client: AsyncClient
    ) -> None:
        """Проверяет запрет доступа к скачиванию изображений другого пользователя."""
        email1 = fake.email()
        password1 = fake.password()

        user_data1 = {
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": email1,
            "password": password1,
        }

        async with sessionmanager.async_connect():
            await httpx_client.post("/auth/registration", json=user_data1)

        response_data1 = (
            await httpx_client.post(
                "/auth/login", json={"email": email1, "password": password1}
            )
        ).json()

        email2 = fake.email()
        password2 = fake.password()

        user_data2 = {
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": email2,
            "password": password2,
        }
        await httpx_client.post("/auth/registration", json=user_data2)

        response_data2 = (
            await httpx_client.post(
                "/auth/login", json={"email": email2, "password": password2}
            )
        ).json()

        file_name = fake.file_name()
        files = [
            (
                "files",
                (
                    f"{file_name}.jpg",
                    fake.image(size=(640, 480), image_format="jpeg"),
                    "image/jpeg",
                ),
            ),
        ]

        response = await httpx_client.post(
            "/image/upload",
            data={
                "transformation": TransformationEnum.rotated.value,
            },
            files=files,
            headers={
                "Authorization": f"Bearer {response_data1.get('access_token')}"
            },
        )

        data = response.json()
        task_id = data.get("successfully_uploaded_to_task_id").get(
            f"{file_name}.jpg"
        )
        assert task_id is not None

        response = await httpx_client.get(
            f"/image/task/{task_id}",
            headers={
                "Authorization": f"Bearer {response_data2.get('access_token')}"
            },
        )

        assert response.status_code == 403
        assert response.json().get("detail") == "You do not have access to it."
