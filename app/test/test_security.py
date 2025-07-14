import pytest
from fastapi import HTTPException
from jose import jwt
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Конфигурация для тестов
SECRET_KEY = "_caE+)3J3^8Lb&u$xaPVemEJj8RpV3"
ALGORITHM = "HS256"


@pytest.fixture
def valid_token():
    test_data = {"userid": "test_user", "true_userid": "123"}
    return jwt.encode(
        {**test_data, "exp": datetime.utcnow() + timedelta(minutes=20)},
        SECRET_KEY,
        algorithm=ALGORITHM
    )


@pytest.fixture
def expired_token():
    # Фикстура для просроченного токена
    return jwt.encode(
        {"userid": "test_user", "exp": datetime.utcnow() - timedelta(minutes=1)},
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def test_token_creation_and_verification(valid_token):
    # Проверка декодирования
    decoded = jwt.decode(valid_token, SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["userid"] == "test_user"

    mock_verify = MagicMock(return_value=("test_user", "123"))
    mock_request = MagicMock(cookies={"session_id": valid_token})

    with patch.dict('sys.modules', {'app.main': MagicMock(verify_token=mock_verify)}):
        from app.main import verify_token
        result = verify_token(mock_request)
        assert result == ("test_user", "123")


def test_expired_token(expired_token):
    # Тест просроченного токена
    mock_verify = MagicMock(side_effect=HTTPException(
        status_code=401,
        detail="Token expired"
    ))
    mock_request = MagicMock(cookies={"session_id": expired_token})

    with patch.dict('sys.modules', {'app.main': MagicMock(verify_token=mock_verify)}):
        from app.main import verify_token
        with pytest.raises(HTTPException) as exc:
            verify_token(mock_request)

        assert exc.value.status_code == 401
        assert "expired" in str(exc.value.detail).lower()


def test_bruteforce_protection():
    # Создаем моки для try_login и соединения с БД
    mock_login = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        ("hashed_password", "user_uuid"),
        ("user_uuid", datetime.utcnow(), 4),
        None
    ]

    mock_module = MagicMock()
    mock_module.try_login = mock_login
    mock_module.conn = MagicMock()
    mock_module.conn.cursor.return_value = mock_cursor

    with patch.dict('sys.modules', {'app.main': mock_module}):
        from app.main import try_login

        # Первые 5 попыток возвращают 303
        mock_login.return_value.status_code = 303
        for _ in range(5):
            response = try_login({"login": "test_user", "password": "wrong"})
            assert response.status_code == 303

        # 6-я попытка должна быть заблокирована (403)
        mock_login.return_value.status_code = 403
        response = try_login({"login": "test_user", "password": "wrong"})
        assert response.status_code == 403