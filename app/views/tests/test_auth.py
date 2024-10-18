import pytest
from faker import Faker
from httpx import AsyncClient

from app.config.db_settings import sessionmanager

fake = Faker()


class TestRegistration:
    @pytest.mark.asyncio
    async def test_should_registered(self, httpx_client: AsyncClient) -> None:
        """Проверяет, что пользователь успешно зарегистрировался"""
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = fake.email()
        password = fake.password()

        async with sessionmanager.async_connect():
            response = await httpx_client.post(
                "/auth/registration",
                json={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "password": password,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == first_name
        assert data["last_name"] == last_name
        assert data["email"] == email

    @pytest.mark.asyncio
    async def test_should_raise_when_username_already_registered(
        self, httpx_client: AsyncClient
    ) -> None:
        """
        Проверяет, что должна упасть ошибка,
            если при регистрации указан занятый username.
        """
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = fake.email()
        password = fake.password()

        async with sessionmanager.async_connect():
            response = await httpx_client.post(
                "/auth/registration",
                json={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "password": password,
                },
            )

        assert response.status_code == 200

        password = fake.password()

        response = await httpx_client.post(
            "/auth/registration",
            json={
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": password,
            },
        )

        assert response.status_code == 400


class TestLogin:
    @pytest.mark.asyncio
    async def test_should_logged(self, httpx_client: AsyncClient) -> None:
        """Проверяет, что пользователь аутентифицировался."""
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = fake.email()
        password = fake.password()

        async with sessionmanager.async_connect():
            await httpx_client.post(
                "/auth/registration",
                json={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "password": password,
                },
            )

        response = await httpx_client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_incorrect_login(self, httpx_client: AsyncClient) -> None:
        """
        Проверяет, что пользователь не прошел
            аутентификацию введя некорректные данные.
        """
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = fake.email()
        password = fake.password()

        async with sessionmanager.async_connect():
            await httpx_client.post(
                "/auth/registration",
                json={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "password": password,
                },
            )

            password = fake.password()

        response = await httpx_client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Incorrect email or password"
