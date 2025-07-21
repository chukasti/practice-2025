import os
import secrets
from urllib.parse import quote_plus
import ipaddress
from dotenv import load_dotenv
import logging
from typing import Optional, Tuple, List
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request, Response, HTTPException, Depends, status, Form
from fastapi.security import OAuth2PasswordBearer
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt
from passlib.context import CryptContext
import psycopg2
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from kafka import KafkaConsumer
import json
from pydantic import Field


# Настройка логгера
logger = logging.getLogger("security")
logger.setLevel(logging.WARNING)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

load_dotenv()

class Settings(BaseSettings):
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field("HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(20, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    postgres_audit_host: str = Field("db", env="POSTGRES_AUDIT_HOST")
    postgres_audit_port: int = Field(..., env="POSTGRES_AUDIT_PORT")
    postgres_audit_db: str = Field(..., env="POSTGRES_AUDIT_DB")
    postgres_audit_user: str = Field(..., env="POSTGRES_AUDIT_USER")
    postgres_audit_password: str = Field(..., env="POSTGRES_AUDIT_PASSWORD")

    kafka_bootstrap_servers: str = Field("kafka:9092", env="KAFKA_BOOTSTRAP_SERVERS")
    kafka_topic: str = Field("incidents", env="KAFKA_TOPIC")

    allowed_hosts: str = Field("127.0.0.1,localhost", env="ALLOWED_HOSTS")
    allowed_ips: str = Field("127.0.0.1,192.168.1.0/24", env="ALLOWED_IPS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"


#SECRET_KEY="_caE+)3J3^8Lb&u$xaPVemEJj8RpV3"
# Инициализация
settings = Settings()






# Реализация CSRF защиты
class CSRFProtect:
    def __init__(self):
        self.cookie_name = "csrf_token"

    def generate_token(self) -> str:
        return secrets.token_urlsafe(32)

    async def validate_request(self, request: Request):
        if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
            return

        json_data = await request.json()
        form_token = json_data.get("csrf_token")

        cookie_token = request.cookies.get(self.cookie_name)

        if not any([form_token]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing"
            )

        if not cookie_token or (form_token != cookie_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid CSRF token"
            )

csrf = CSRFProtect()


class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, csrf_protect: CSRFProtect):
        super().__init__(app)
        self.csrf_protect = csrf_protect

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if not request.cookies.get(self.csrf_protect.cookie_name):
            token = self.csrf_protect.generate_token()
            response.set_cookie(
                key=self.csrf_protect.cookie_name,
                value=token,
                httponly=False,
                samesite="strict",
                secure=False,
                path="/",
                max_age=3600
            )

        return response


csrf_protect = CSRFProtect()


app = FastAPI(middleware=[
    Middleware(CSRFMiddleware, csrf_protect=csrf_protect)
])


SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 20
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Подключение к Kafka
try:
    kafka_consumer = KafkaConsumer(
        settings.kafka_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        auto_offset_reset='earliest',
        enable_auto_commit=False,
        consumer_timeout_ms=1000
    )
except Exception as e:
    logger.error(f"Failed to connect to Kafka: {e}")
    raise


def get_db_connection():
    try:
        conn_str = (
            f"dbname='{settings.postgres_audit_db}' user=audit_user password='{settings.postgres_audit_password}' host=localhost port=5431")
        conn = psycopg2.connect(conn_str)
        #conn = psycopg2.connect("dbname=audit_db port=5431 host=localhost user=audit_user password=audit_password")
        conn.autocommit = False
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


class LoginPass(BaseModel):
    login: str
    password: str


class Incident(BaseModel):
    id: str
    timestamp: datetime
    severity: str
    description: str
    status: str


templates = Jinja2Templates(directory="audit_templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- Вспомогательные функции ---
def get_csrf_token(request: Request) -> Optional[str]:
    return request.cookies.get(csrf_protect.cookie_name)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def verify_origin(request: Request):
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        referer = request.headers.get("referer")
        if not referer or not any(
                referer.startswith(f"http://{host}")
                for host in settings.allowed_hosts.split(",")
        ):
            logger.warning(f"Invalid referer: {referer}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid request source"
            )


async def verify_token(request: Request) -> Tuple[str, str, str]:
    token = request.cookies.get("session_id")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"}
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("userid")
        true_user_id: str = payload.get("true_userid")

        if not user_id:
            raise JWTError()

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT role FROM users WHERE username = %s", (user_id,))
                role = cur.fetchone()[0]
                return user_id, true_user_id, role

    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"}
        )


# Middleware для проверки IP
@app.middleware("http")
async def check_local_network(request: Request, call_next):
    client_ip = request.client.host
    allowed_networks = settings.allowed_ips.split(",")

    try:
        if not any(
                ipaddress.ip_address(client_ip) in ipaddress.ip_network(net)
                for net in allowed_networks
        ):
            logger.warning(f"Blocked non-local access attempt from {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    except ValueError as e:
        logger.error(f"Invalid IP address: {client_ip} - {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid client IP"
        )

    return await call_next(request)


# Роуты
@app.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse("/home")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, response: Response):
    if request.cookies.get("session_id"):
        return RedirectResponse("/home", status_code=status.HTTP_303_SEE_OTHER)


    csrf_token= csrf.generate_token()
    response = templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "csrf_token": csrf_token,
            "warning": "Приложение работает без HTTPS. Не используйте реальные данные!"
        }
    )
    response.set_cookie(
        key=csrf.cookie_name,
        value=csrf_token,
        httponly=True,
        samesite="strict"
    )
    return response


@app.post("/api/login")
async def login(
        request: Request, auth: LoginPass):
    await verify_origin(request)
    await csrf_protect.validate_request(request)

    try:
        if not auth.login or not auth.password:
            return RedirectResponse(
                "/login?error=empty_fields",
                status_code=status.HTTP_303_SEE_OTHER
            )

        now = datetime.now(timezone.utc)

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Проверка учетных данных
                cur.execute(
                    "SELECT hashed_password, user_id, role FROM users WHERE username = %s",
                    (auth.login,)
                )
                user_data = cur.fetchone()

                if not user_data:
                    return RedirectResponse(
                        "/login?error=invalid_credentials",
                        status_code=status.HTTP_303_SEE_OTHER
                    )

                stored_hash, true_user_id, role = user_data

                # Проверка защиты от брутфорса
                cur.execute(
                    """SELECT attempt_value FROM bruteforce_protect 
                    WHERE user_id = %s AND last_attempt > %s""",
                    (true_user_id, now - timedelta(minutes=20))
                )
                brute_data = cur.fetchone()

                if brute_data and brute_data[0] >= 5:
                    return RedirectResponse(
                        "/login?error=too_many_attempts",
                        status_code=status.HTTP_303_SEE_OTHER
                    )


                if not pwd_context.verify(auth.password, stored_hash):
                    if brute_data:
                        cur.execute(
                            """UPDATE bruteforce_protect 
                            SET attempt_value = attempt_value + 1, last_attempt = %s 
                            WHERE user_id = %s""",
                            (now, true_user_id)
                        )
                    else:
                        cur.execute(
                            """INSERT INTO bruteforce_protect 
                            (user_id, last_attempt, attempt_value) 
                            VALUES (%s, %s, 1)""",
                            (true_user_id, now)
                        )
                    conn.commit()
                    return RedirectResponse(
                        "/login?error=invalid_credentials",
                        status_code=status.HTTP_303_SEE_OTHER
                    )


                expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                token = create_access_token({
                    "userid": auth.login,
                    "true_userid": true_user_id,
                    "exp": expires_at
                })


                cur.execute(
                    "DELETE FROM bruteforce_protect WHERE user_id = %s",
                    (true_user_id,)
                )


                cur.execute(
                    """INSERT INTO active_session 
                    (userid, token, expires_at) 
                    VALUES (%s, %s, %s)""",
                    (auth.login, token, expires_at)
                )
                conn.commit()


                response = RedirectResponse(
                    "/home",
                    status_code=status.HTTP_303_SEE_OTHER
                )
                response.set_cookie(
                    key="session_id",
                    value=token,
                    httponly=True,
                    max_age=1200,
                    samesite="strict",
                    secure=False,
                    path="/"
                )

                # Установка нового CSRF токена
                csrf_token = csrf_protect.generate_token()
                response.set_cookie(
                    key=csrf_protect.cookie_name,
                    value=csrf_token,
                    httponly=False,
                    samesite="strict",
                    secure=False,
                    path="/",
                    max_age=3600
                )

                return response

    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/home", response_class=HTMLResponse)
async def home_page(
        request: Request,
        user_data: Tuple[str, str, str] = Depends(verify_token)
):
    user_id, true_user_id, role = user_data

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT username, name_surname, role FROM users WHERE username = %s",
                (user_id,)
            )
            username, name_surname, role = cur.fetchone()
    #Получение инцидентов из бд аудита
    incidents: List[Incident] = []
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                SELECT id, timestamp, account_id, amount, status, source_ip, raw_payload
                FROM audit_logs
                ORDER BY timestamp DESC
                LIMIT %s
                """,(20,))
                for record in cur:
                    incidents.append(Incident(
                        id=record[0],
                        timestamp=record[1],
                        severity=record[2],
                        description=record[3],
                        status=record[4]
                    ))
    except Exception as e:
        logger.error(f"Failed to fetch incidents from DB: {e}")
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "fullname": name_surname,
            "role": role,
            "incidents": incidents,
            "csrf_token": get_csrf_token(request)
        }
    )



    # Получение инцидентов из Kafka
#    incidents: List[Incident] = []
#    try:
#        for _ in range(5):
#            msg = next(kafka_consumer)
#            if msg:
#                incidents.append(Incident(**msg.value))
#    except StopIteration:
#        pass
    #todo: события должны читаться из БД аудита, потому что...
    #todo: ...main app передает логи в кафку, кафка передаёт логи в ...
    #todo: ...БД аудита.

    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "fullname": name_surname,
            "role": role,
            "incidents": incidents,
            "csrf_token": get_csrf_token(request)
        }
    )


@app.post("/api/logout")
async def logout(
        request: Request,
        user_data: Tuple[str, str, str] = Depends(verify_token)
):
    token = request.cookies.get("session_id")
    if token:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM active_session WHERE token = %s",
                    (token,)
                )
                conn.commit()

    response = RedirectResponse(
        "/login",
        status_code=status.HTTP_303_SEE_OTHER
    )
    response.delete_cookie("session_id")
    response.delete_cookie(csrf_protect.cookie_name)
    return response


@app.get("/audit", response_class=HTMLResponse)
async def audit_page(
        request: Request,
        user_data: Tuple[str, str, str] = Depends(verify_token)
):
    user_id, true_user_id, role = user_data

    if role != "auditor":
        return templates.TemplateResponse(
            "not_enough_privileges.html",
            {"request": request}
        )

    return templates.TemplateResponse(
        "audit.html",
        {
            "request": request,
            "csrf_token": get_csrf_token(request)
        }
    )


@app.post("/api/incidents")
async def get_incidents(
        request: Request,
        user_data: Tuple[str, str, str] = Depends(verify_token)
):
    await verify_origin(request)
    await csrf_protect.validate_request(request)

    incidents = []
    try:
        for _ in range(20):
            msg = next(kafka_consumer)
            if msg:
                incidents.append(msg.value)
    except StopIteration:
        pass

    return JSONResponse(content=incidents)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )