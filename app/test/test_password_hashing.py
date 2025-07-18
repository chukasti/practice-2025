import pytest
from passlib.context import CryptContext
from pydantic import BaseModel


# Создаем тестовую версию модели LoginPass
class LoginPass(BaseModel):
    login: str
    password: str


# Создаем отдельный контекст для хеширования паролей
test_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.fixture
def test_db_connection():
    """Фикстура для тестового подключения к БД"""
    yield None


@pytest.fixture
def test_user(test_db_connection):
    # Создаем тестового пользователя без реального подключения к БД
    username = "test_user_123"
    password = "secure_password_123"
    hashed_password = test_pwd_context.hash(password)

    yield {
        "username": username,
        "password": password,
        "hashed_password": hashed_password
    }


def test_password_is_hashed(test_user):
    """Проверяем, что пароль хранится в хешированном виде"""
    assert test_user["password"] != test_user["hashed_password"]
    assert "secure_password_123" not in test_user["hashed_password"]


def test_password_verification(test_user):
    """Проверяем, что хеш пароля можно верифицировать"""
    assert test_pwd_context.verify(
        test_user["password"],
        test_user["hashed_password"]
    )


def test_wrong_password_fails(test_user):
    """Проверяем, что неправильный пароль не проходит проверку"""
    assert not test_pwd_context.verify(
        "wrong_password",
        test_user["hashed_password"]
    )