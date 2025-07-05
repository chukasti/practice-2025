from enum import Enum
from pydantic import BaseModel
from fastapi import FastAPI, Request, Response, status, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import secrets
import psycopg2
from fastapi.responses import FileResponse
#from models.transaction import Transaction
#from api.v1.transactions import TransactionCreate
from datetime import datetime
from starlette.responses import HTMLResponse, FileResponse, RedirectResponse
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = "_caE+)3J3^8Lb&u$xaPVemEJj8RpV3"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 20
#!!!ОБЯЗАТЕЛЬНО СЕКРЕТНЫЙ КЛЮЧ УБРАТЬ ИЗ КОДА В ENVIRONMENT!!!

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise JWTError()
        return user_id
    except JWTError:
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
    merchant_id: str
    status: str

class LoginPass(BaseModel):
    login: str
    password: str

def cookie_detection(request: Request):
    g = 0
    session = request.cookies.get("session_id")
    if session:
        g += 1
    return g


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/favicon.ico")
def read_favicon():
    return FileResponse(path="favicon.ico", media_type="image/x-icon")


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/images/image1.jpg")
def read_image():
    return FileResponse(path="images/image1.jpg")

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/panel", response_class=HTMLResponse)
def panel_page():
    return 1

@app.get("/home", response_class=HTMLResponse)
def home_page(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.post("/api/login")
async def try_login(rekvi: LoginPass, response: Response, request: Request, tx: TransactionNew):
    login = "makaka"
    password = "777"
    token = secrets.token_hex(32)
    if rekvi.login == login and rekvi.password == password and cookie_detection(request) == 0:
        response.set_cookie(
            key="session_id",
            value=token,
            httponly=True,
            max_age=1800,
            samesite="lax",
            secure=False
        )
        cur.execute("INSERT INTO transactions (id, amount, timestamp, account_id, merchant_id, status) VALUES (%s, %s, %s, %s, %s, %s)", (tx.id, tx.amount, tx.timestamp, tx.account_id, tx.merchant_id, tx.status) )
        conn.commit()
        response.status_code = 303
        response.headers["Location"] = "/home"
        return response
    #добавить логирование неуспешных попыток авторизации
    return RedirectResponse(url="/login", status_code=status.HTTP_403_FORBIDDEN)

@app.post("/api/transaction")
async def send_transaction(tx: TransactionNew, request: Request):
    if tx.amount and tx.merchant_id:
        request.cookies.get("session_id")

        now = datetime.now(timezone.utc)
        cur.execute(
            "INSERT INTO transactions (id, amount, timestamp, account_id, merchant_id, status) VALUES (%s, %s, %s, %s, %s, %s)",
            (tx.id, tx.amount, now.isoformat(), tx.account_id, tx.merchant_id, tx.status))
        conn.commit()