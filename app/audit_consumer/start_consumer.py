from kafka import KafkaConsumer
import psycopg2
import json
import threading
from datetime import datetime
from settings import settings  # импортируй свою конфигурацию
import logging

logger = logging.getLogger("audit_consumer")

def get_db_connection():
    return psycopg2.connect(
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        host=settings.postgres_host,
        port=settings.postgres_port
    )

def save_to_audit_db(event: dict):
    try:
        conn = get_db_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_logs
                    (tx_id, account_id, receiver_id, amount, status, timestamp, source_ip, raw_payload)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        event.get("transaction_id"),
                        event.get("account_id"),
                        event.get("receiver_id"),
                        event.get("amount"),
                        event.get("status"),
                        event.get("timestamp"),
                        event.get("source_ip"),
                        json.dumps(event)
                    )
                )
    except Exception as e:
        logger.error(f"Ошибка при записи в audit_logs: {e}")
    finally:
        if conn:
            conn.close()

def start_consumer():
    consumer = KafkaConsumer(
        settings.kafka_transaction_topic,
        bootstrap_servers=[settings.kafka_bootstrap_servers],
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="audit-group"
    )

    logger.info("Kafka consumer started")
    for message in consumer:
        event = message.value
        logger.info(f"Получено сообщение из Kafka: {event}")
        save_to_audit_db(event)
