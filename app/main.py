from pydantic import BaseModel
from fastapi import FastAPI, Request, Response, status, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import secrets
import psycopg2
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
#from models.transaction import Transaction
#from api.v1.transactions import TransactionCreate
from datetime import datetime
from starlette.responses import HTMLResponse, FileResponse, RedirectResponse
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


#Настройка логгера
def setup_logger():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger("bank_app")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler = RotatingFileHandler(
        filename=log_dir / "transactions.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logger()

SECRET_KEY = "_caE+)3J3^8Lb&u$xaPVemEJj8RpV3"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 20
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
#!!!ОБЯЗАТЕЛЬНО СЕКРЕТНЫЙ КЛЮЧ УБРАТЬ ИЗ КОДА В ENVIRONMENT!!!

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_token(request: Request):
    token = request.cookies.get("session_id")
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("userid")
        if not user_id:
            raise JWTError()
        return user_id
    except JWTError:
        logger.warning('Invalid or expired token')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


conn = psycopg2.connect("dbname=postgres_db port=5430 host=localhost user=postgres_user password=postgres_password")
#При установке в докер - поставить надежные данные для аутентификации
cur = conn.cursor()
class TransactionNew(BaseModel):
    id: int
    amount: float
    timestamp: str
    account_id: str
    receiver_id: str
    status: str

class LoginPass(BaseModel):
    login: str
    password: str



app = FastAPI()

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    logger.warning(f"404 Not Found: {request.url}")
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "error": "Страница не найдена", "code" : 404},
        status_code=404
    )

@app.exception_handler(500)
async def server_error_handler(request: Request, exc: HTTPException):
    logger.warning(f"500 Server Error: {str(exc)}")
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "error": "Внутренняя ошибка сервера", "code" : 500},
        status_code=500
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"error": "Некорректные данные", "details" : str(exc)},
    )

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/favicon.ico")
def read_favicon():
    return FileResponse(path="favicon.ico", media_type="image/x-icon")


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return RedirectResponse("/home")

@app.get("/images/image1.jpg")
def read_image():
    return FileResponse(path="images/image1.jpg")

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.cookies.get("session_id") is not None:
        return RedirectResponse("/home")
    logger.debug('Accessing login page')
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/api/logout")
async def logout(response: Response, request: Request):
    try:
        token = request.cookies.get("session_id")
        if token:
            user_id = verify_token(token)
            logger.info(f"User {user_id} logging out")
            cur.execute("DELETE FROM active_session WHERE token = %s", (token,))
            conn.commit()

        response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie("session_id")
        return response
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise

@app.get("/send_money", response_class=HTMLResponse)
def panel_page(request: Request, user_id: str = Depends(verify_token)):
    cur.execute("SELECT username, name_surname, balance FROM users WHERE username = %s", (user_id,))
    row = cur.fetchone()
    user_id = row[0]
    name_surname = row[1]
    balance = row[2]
    if user_id is not None and name_surname:
        return templates.TemplateResponse("sending_page.html", {
            "request": request,
            "fullname": name_surname,
            "balance": balance
        })
    logger.warning("user_id or name_surname is empty")
    return RedirectResponse("/login")



@app.get("/home", response_class=HTMLResponse)
def home_page(request: Request, user_id: str = Depends(verify_token)):
    try:
        cur.execute("SELECT username, name_surname, balance FROM users WHERE username = %s", (user_id,))
        row = cur.fetchone()
        if not row:
            logger.error(f"User {user_id} not found in database")
            return RedirectResponse("/login")

        user_id = row[0]
        name_surname = row[1]
        balance = row[2]

        logger.debug(f"User {user_id} accessing home page")

        return templates.TemplateResponse("home.html", {
            "request": request,
            "fullname": name_surname,
            "balance": balance
        })
    except Exception as e:
        logger.error(f"Home page error: {str(e)}")
        raise

@app.post("/api/login")
def try_login(auth: LoginPass, request: Request):
    try:
        if auth.login and auth.password:
            cur.execute("SELECT hashed_password FROM users WHERE username = %s", (auth.login,))
            row = cur.fetchone()
            if not row:
                logger.warning(f"Failed login attempt - user not found: {auth.login}")
                return RedirectResponse(url="/login", status_code=status.HTTP_403_FORBIDDEN)
            stored_hash = row[0]
            if not pwd_context.verify(auth.password, stored_hash):
                logger.warning(f"Failed login attempt - invalid password for user: {auth.login}")
                return RedirectResponse(url="/login", status_code=status.HTTP_403_FORBIDDEN)
            #cur.execute("INSERT INTO transactions (id, amount, timestamp, account_id, receiver_id, status) VALUES (%s, %s, %s, %s, %s, %s)", (tx.id, tx.amount, tx.timestamp, tx.account_id, tx.receiver_id, tx.status) )
            #conn.commit()
            expires_at = datetime.utcnow() + timedelta(minutes=20)
            payload = {
                "userid": auth.login,
                "exp": expires_at
        }
            token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
            logger.info(f"Successful login: {auth.login}")
            response = RedirectResponse("/home", status_code=status.HTTP_303_SEE_OTHER)
            response.set_cookie(
                key="session_id",
                value=token,
                httponly=True,
                max_age=1200,
                expires=1200,
                samesite="lax",
                secure=False
            )

            cur.execute(
                "INSERT INTO active_session (userid, token, expires_at) VALUES (%s, %s, %s)",
                (auth.login, token, expires_at)
            )
            conn.commit()

            return response

        logger.warning("Login attempt with empty credentials")
        return RedirectResponse(url="/login?error=invalid_credentials", status_code=303)

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise


@app.post("/api/transaction")
async def send_transaction(tx: TransactionNew, request: Request, user_id: str = Depends(verify_token)):

    # 2. Валидация данных
    if tx.amount <= 0:
        logger.warning(f"Invalid amount from {user_id}: {tx.amount}")
        return JSONResponse(
            status_code=400,
            content={"error": "Сумма должна быть положительной"}
        )
    
    if tx.receiver_id == user_id:
        logger.warning(f"Attempt to send money yourself")
        return JSONResponse(
            status_code=400,
            content={"error": "Вы не можете перевести деньги самому себе"}
        )

    try:
        # Начало транзакции
        conn.autocommit = False
        cur = conn.cursor()

        # 3. Проверка получателя и баланса в одной транзакции
        cur.execute("""
            SELECT u.balance, m.id IS NOT NULL as merchant_exists 
            FROM users u
            LEFT JOIN merchants m ON m.id = %s
            WHERE u.username = %s
            FOR UPDATE
            """,
                    (tx.receiver_id, user_id)
                    )

        result = cur.fetchone()
        if not result:
            logger.warning(f"User not found: {user_id}")
            return JSONResponse(
                status_code=404,
                content={"error": "Пользователь не найден"}
            )

        balance, merchant_exists = result
        if not merchant_exists:
            logger.warning(f"Invalid merchant: {tx.receiver_id}")
            return JSONResponse(
                status_code=400,
                content={"error": "Получатель не найден"}
            )

        if balance < tx.amount:
            logger.warning(f"Insufficient funds: {user_id}")
            return JSONResponse(
                status_code=400,
                content={"error": "Недостаточно средств", "balance": balance}
            )

        # 4. Генерация уникального ID транзакции
        transaction_id = None
        for _ in range(3):  # 3 попытки генерации уникального ID
            temp_id = secrets.token_urlsafe(12)
            cur.execute("SELECT id FROM transactions WHERE id = %s", (temp_id,))
            if not cur.fetchone():
                transaction_id = temp_id
                break

        if not transaction_id:
            raise Exception("Failed to generate unique transaction ID")

        # 5. Выполнение транзакции
        now = datetime.now(timezone.utc)

        cur.execute(
            "UPDATE users SET balance = balance - %s WHERE username = %s",
            (tx.amount, user_id)
        )

        cur.execute(
            """INSERT INTO transactions 
               (id, amount, timestamp, account_id, receiver_id, status) 
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (transaction_id, tx.amount, now.isoformat(), user_id, tx.receiver_id, "completed")
        )

        conn.commit()
        logger.info(f"Transaction {transaction_id} completed for {user_id}")

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "transaction_id": transaction_id,
                "new_balance": balance - tx.amount
            }
        )

    except psycopg2.DatabaseError as db_error:
        conn.rollback()
        logger.error(f"Database error: {str(db_error)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Ошибка базы данных"}
        )

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Внутренняя ошибка сервера"}
        )

    finally:
        try:
            conn.autocommit = True
            if 'cur' in locals():
                cur.close()
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")