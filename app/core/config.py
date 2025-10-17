from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field("HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(20, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    postgres_host: str = Field("db", env="POSTGRES_HOST")
    postgres_port: int = Field(..., env="POSTGRES_PORT")
    postgres_db: str = Field(..., env="POSTGRES_DB")
    postgres_user: str = Field(..., env="POSTGRES_USER")
    postgres_password: str = Field(..., env="POSTGRES_PASSWORD")

    kafka_bootstrap_servers: str = Field("kafka:9092", env="KAFKA_BOOTSTRAP_SERVERS")
    kafka_transaction_topic: str = Field("incidents", env="KAFKA_TOPIC")

    allowed_hosts: str = Field("127.0.0.1,localhost,0.0.0.0", env="ALLOWED_HOSTS")
    allowed_ips: str = Field("127.0.0.1,192.168.1.0/24", env="ALLOWED_IPS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"


settings = Settings()
