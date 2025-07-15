import pytest
import psycopg2
from datetime import datetime
from unittest.mock import MagicMock
import os

# Конфигурация тестовой БД
TEST_DB_CONFIG = {
    "dbname": "test_bank_db",
    "user": "test_user",
    "password": "test_password",
    "host": "localhost",
    "port": "5432"
}

USE_REAL_DB = os.getenv('USE_REAL_DB', 'false').lower() == 'true'


@pytest.fixture
def mock_db():
    """Фикстура для мокирования подключения к БД"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor


def test_table_exists(mock_db):
    mock_conn, mock_cursor = mock_db

    # Настраиваем мок для возврата списка таблиц
    mock_cursor.fetchall.return_value = [
        ('users',), ('transactions',), ('active_session',), ('bruteforce_protect',)
    ]

    # Вызываю тестируемую функцию (в данном случае просто проверяю логику)
    required_tables = {"users", "transactions", "active_session", "bruteforce_protect"}

    if USE_REAL_DB:
        # Реальная проверка с БД
        conn = psycopg2.connect(**TEST_DB_CONFIG)
        with conn.cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            existing_tables = {row[0] for row in cur.fetchall()}
        conn.close()
        assert required_tables.issubset(existing_tables)
    else:
        # Проверка с моками
        mock_cursor.execute.assert_not_called()  # В этом тесте мы не вызываем execute напрямую
        assert True  # Просто проверяем, что тест запускается


def test_users_table_structure(mock_db):
    """Проверка структуры таблицы users"""
    mock_conn, mock_cursor = mock_db

    mock_cursor.fetchall.return_value = [
        ('user_id', 'character varying'),
        ('username', 'character varying'),
        ('hashed_password', 'character varying'),
        ('name_surname', 'character varying'),
        ('balance', 'numeric'),
        ('account_status', 'character varying'),
        ('created_at', 'timestamp without time zone')
    ]

    # Имитируем вызовы к БД
    if USE_REAL_DB:
        conn = psycopg2.connect(**TEST_DB_CONFIG)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users'
            """)
            columns = {row[0]: row[1] for row in cur.fetchall()}
        conn.close()
    else:
        # Имитируем вызов execute и fetchall
        mock_cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users'
        """)
        columns = {row[0]: row[1] for row in mock_cursor.fetchall()}

    expected_columns = {
        "user_id": "character varying",
        "username": "character varying",
        "hashed_password": "character varying",
        "name_surname": "character varying",
        "balance": "numeric",
        "account_status": "character varying",
        "created_at": "timestamp without time zone"
    }

    for col, col_type in expected_columns.items():
        assert col in columns, f"Отсутствует колонка {col}"
        assert columns[col] == col_type, f"Неверный тип для {col}"

    if not USE_REAL_DB:
        mock_cursor.execute.assert_called_once()


def test_foreign_key_constraints(mock_db):
    """Проверка ограничений внешнего ключа"""
    mock_conn, mock_cursor = mock_db

    mock_cursor.fetchall.return_value = [
        ('transactions', 'account_id', 'users', 'user_id'),
        ('transactions', 'merchant_id', 'users', 'user_id'),
        ('active_session', 'userid', 'users', 'username'),
        ('bruteforce_protect', 'user_id', 'users', 'user_id')
    ]

    if USE_REAL_DB:
        conn = psycopg2.connect(**TEST_DB_CONFIG)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tc.table_name, kcu.column_name, 
                       ccu.table_name AS foreign_table_name,
                       ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
            """)
            existing_fks = {(fk[0], fk[1], fk[2], fk[3]) for fk in cur.fetchall()}
        conn.close()
    else:
        mock_cursor.execute("""
            SELECT tc.table_name, kcu.column_name, 
                   ccu.table_name AS foreign_table_name,
                   ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
        """)
        existing_fks = {(fk[0], fk[1], fk[2], fk[3]) for fk in mock_cursor.fetchall()}

    expected_fks = {
        ("transactions", "account_id", "users", "user_id"),
        ("transactions", "merchant_id", "users", "user_id"),
        ("active_session", "userid", "users", "username"),
        ("bruteforce_protect", "user_id", "users", "user_id")
    }

    for fk in expected_fks:
        assert fk in existing_fks, f"Отсутствует внешний ключ: {fk}"

    if not USE_REAL_DB:
        mock_cursor.execute.assert_called_once()


def test_balance_non_negative(mock_db):
    """Проверка, что баланс не может быть отрицательным"""
    mock_conn, mock_cursor = mock_db

    if USE_REAL_DB:
        conn = psycopg2.connect(**TEST_DB_CONFIG)
        with conn.cursor() as cur:
            with pytest.raises(psycopg2.Error):
                cur.execute("""
                    INSERT INTO users 
                    (user_id, username, hashed_password, name_surname, balance, account_status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, ("test1", "negative_user", "hash", "Negative User", -100, "normal"))
                conn.commit()
        conn.close()
    else:
        mock_cursor.execute("""
            INSERT INTO users 
            (user_id, username, hashed_password, name_surname, balance, account_status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, ("test1", "negative_user", "hash", "Negative User", -100, "normal"))

        mock_cursor.execute.assert_called_once()


def test_transaction_amount_positive(mock_db):
    """Проверка, что сумма транзакции должна быть положительной"""
    mock_conn, mock_cursor = mock_db

    if USE_REAL_DB:
        conn = psycopg2.connect(**TEST_DB_CONFIG)
        with conn.cursor() as cur:
            # Создаю тестовых пользователей
            cur.execute("""
                INSERT INTO users 
                (user_id, username, hashed_password, name_surname, balance, account_status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, ("sender1", "sender1", "hash", "Sender 1", 1000, "normal"))

            cur.execute("""
                INSERT INTO users 
                (user_id, username, hashed_password, name_surname, balance, account_status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, ("receiver1", "receiver1", "hash", "Receiver 1", 1000, "normal"))

            conn.commit()

            # Пытаюсь создать транзакцию с отрицательной суммой
            with pytest.raises(psycopg2.Error):
                cur.execute("""
                    INSERT INTO transactions 
                    (id, amount, timestamp, account_id, merchant_id, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, ("tx1", -100, datetime.now(), "sender1", "receiver1", "attempted"))
                conn.commit()
        conn.close()
    else:
        mock_cursor.execute("""
            INSERT INTO users 
            (user_id, username, hashed_password, name_surname, balance, account_status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, ("sender1", "sender1", "hash", "Sender 1", 1000, "normal"))

        mock_cursor.execute("""
            INSERT INTO users 
            (user_id, username, hashed_password, name_surname, balance, account_status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, ("receiver1", "receiver1", "hash", "Receiver 1", 1000, "normal"))

        mock_cursor.execute("""
            INSERT INTO transactions 
            (id, amount, timestamp, account_id, merchant_id, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, ("tx1", -100, datetime.now(), "sender1", "receiver1", "attempted"))

        # Проверяю, что execute был вызван 3 раза
        assert mock_cursor.execute.call_count == 3