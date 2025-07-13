from pydantic import BaseModel
from fastapi import FastAPI, Request, Response, status, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import psycopg2
from fastapi.responses import FileResponse
from datetime import datetime
from starlette.responses import HTMLResponse, FileResponse, RedirectResponse
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext


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
    return RedirectResponse("/home")

@app.get("/images/image1.jpg")
def read_image():
    return FileResponse(path="images/image1.jpg")

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.cookies.get("session_id") is not None:
        return RedirectResponse("/home")
    print(request.cookies.get("session_id"))
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/api/logout")
async def logout(response: Response, request: Request):
    token = request.cookies.get("session_id")
    if token:
        cur.execute("DELETE FROM active_session WHERE token = %s", (token,))
        conn.commit()
    response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("session_id")
    return response


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
    return RedirectResponse("/login")


@app.get("/home", response_class=HTMLResponse)
def home_page(request: Request, user_id: str = Depends(verify_token)):
    if isinstance(user_id, RedirectResponse):
        return user_id
    cur.execute("SELECT username, name_surname, balance FROM users WHERE username = %s", (user_id,))
    row = cur.fetchone()
    user_id = row[0]
    name_surname = row[1]
    balance = row[2]
    if user_id is not None and name_surname:
        return templates.TemplateResponse("home_old.html", {
            "request": request,
            "fullname": name_surname,
            "balance": balance
        })
    return RedirectResponse("/login")

@app.post("/api/login")
def try_login(auth: LoginPass, request: Request):
    if auth.login and auth.password:
        cur.execute("SELECT hashed_password FROM users WHERE username = %s", (auth.login,))
        row = cur.fetchone()
        if not row:
            return RedirectResponse(url="/login", status_code=status.HTTP_403_FORBIDDEN)
        stored_hash = row[0]
        if not pwd_context.verify(auth.password, stored_hash):
            return RedirectResponse(url="/login", status_code=status.HTTP_403_FORBIDDEN)
        #cur.execute("INSERT INTO transactions (id, amount, timestamp, account_id, merchant_id, status) VALUES (%s, %s, %s, %s, %s, %s)", (tx.id, tx.amount, tx.timestamp, tx.account_id, tx.merchant_id, tx.status) )
        #conn.commit()
        expires_at = datetime.utcnow() + timedelta(minutes=20)
        payload = {
            "userid": auth.login,
            "exp": expires_at
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        response = RedirectResponse("/home", status_code=status.HTTP_303_SEE_OTHER)
        response.status_code = 303
        response.headers["Location"] = "/home"
        response.set_cookie(
            key="session_id",
            value=token,
            httponly=True,
            max_age=1200,
            expires=1200,
            samesite="lax",
            secure=False
        )
        cur.execute("INSERT INTO active_session (userid, token, expires_at) VALUES (%s, %s, %s)", (auth.login, token, expires_at))
        return response
    #добавить логирование неуспешных попыток авторизации
    return RedirectResponse(url="/login?error=invalid_credentials", status_code=303)

@app.post("/api/transaction")
async def send_transaction(tx: TransactionNew, request: Request, response: Response, user_id: str = Depends(verify_token)):
    #session_id = request.cookies.get("session_id")
    #if not session_id:
        #return RedirectResponse("/login")
    #user_id = verify_token(session_id)
    cur.execute("SELECT username, name_surname, balance FROM users WHERE username = %s", (user_id,))
    row = cur.fetchone()
    user_id = row[0]
    name_surname = row[1]
    balance = row[2]
    if tx.amount and tx.receiver_id:
        cur.execute("SELECT user_id, name_surname FROM users WHERE user_id = %s", (tx.receiver_id,))
        rec = cur.fetchone()
        rec_id = rec[0]
        rec_name = rec[1]
        if tx.amount > 0.0:
            cur.execute("UPDATE accounts SET balance = balance + %s WHERE user_id = %s", (tx.amount, rec_id))
            conn.commit()
            cur.execute("UPDATE accounts SET balance = balance - %s WHERE user_id = %s", (tx.amount, user_id))
        now = datetime.now(timezone.utc)
        cur.execute(
            "INSERT INTO transactions (id, amount, timestamp, account_id, merchant_id, status) VALUES (%s, %s, %s, %s, %s, %s)",
            (tx.id, tx.amount, now.isoformat(), user_id, tx.merchant_id, tx.status))
        conn.commit()