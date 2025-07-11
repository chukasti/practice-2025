from pydantic import BaseModel
from fastapi import FastAPI, Request, Response, status, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import secrets
import psycopg2
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from datetime import datetime
from starlette.responses import HTMLResponse, FileResponse, RedirectResponse
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

app = FastAPI()

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


def verify_token(request: Request)  -> tuple[str, str]:
    token = request.cookies.get("session_id")
    if not token:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("userid")
        true_user_id: str = payload.get("true_userid")
        if not user_id:
            raise JWTError()
        return user_id, true_user_id
    except:
        f=1

conn = psycopg2.connect("dbname=b port=5430 host=localhost user=postgres_user password=postgres_password")
#При установке в докер - поставить надежные данные для аутентификации
cur = conn.cursor()
#todo: сделать конфиг для второй базы данных
class LoginPass(BaseModel):
    login: str
    password: str

templates = Jinja2Templates(directory="audit_templates")

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.cookies.get("session_id") is not None:
        return RedirectResponse("/home")
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/", response_class=RedirectResponse)
def starting_page():
    return RedirectResponse("/home")
#todo: добавить home страницу аудита
#todo: добавить панель управления, в которую кафка будет передавать инциденты
#todo: сделать конфигурацию приложения, чтобы оно было доступно только из локальной сети
#todo:


@app.get("/home", response_class=HTMLResponse)
def home_page(request: Request, response: Response, token_data: tuple[str, str] = Depends(verify_token),
):
    user_id, true_user_id = token_data
    cur.execute("SELECT username, name_surname, role FROM users WHERE username = %s", (user_id,))
    row = cur.fetchone()
    user_id = row[0]
    name_surname = row[1]
    role = row[2]




    return templates.TemplateResponse("home.html", {
        "request": request,
        "fullname": name_surname,
        "role": role
    })



@app.post("/api/login")
def try_login(auth: LoginPass, request: Request):
    try:
        if auth.login and auth.password:
            now = datetime.now(timezone.utc)
            cur.execute("SELECT hashed_password, user_id FROM users WHERE username = %s", (auth.login,))
            row = cur.fetchone()
            if not row:
                return RedirectResponse(url="/login", status_code=status.HTTP_403_FORBIDDEN)
            stored_hash = row[0]
            true_user_id = row[1]
            cur.execute("SELECT user_id, last_attempt, attempt_value FROM bruteforce_protect WHERE user_id = %s", (true_user_id,))
            check_brute = cur.fetchone()
            if check_brute:
                attempt_time = check_brute[1]
                attempt_number = check_brute[2]
                if now - attempt_time >= timedelta(minutes=20):
                    cur.execute("DELETE FROM bruteforce_protect WHERE user_id = %s", (true_user_id,))
                    conn.commit()

                # 2) иначе, если попыток уже >= 5 — блокировка
                elif attempt_number >= 5:
                    return RedirectResponse(url="/login", status_code=status.HTTP_403_FORBIDDEN)

            if not pwd_context.verify(auth.password, stored_hash):

                cur.execute("SELECT user_id, last_attempt, attempt_value FROM bruteforce_protect WHERE user_id = %s", (true_user_id,))
                brute_row = cur.fetchone()
                if brute_row:
                    last_attempt, attempt_value = brute_row
                    cur.execute("UPDATE bruteforce_protect SET last_attempt = %s, attempt_value = %s WHERE user_id = %s",(now, attempt_value+1, true_user_id))
                    conn.commit()
                else:
                    cur.execute("INSERT INTO bruteforce_protect (user_id, last_attempt, attempt_value) VALUES (%s, %s, %s)", (true_user_id, now, 1))
                    conn.commit()
                #cur.execute("INSERT INTO bruteforce_protect user_id, last_attempt, attempt_value WHERE user_id = %s", (true_user_id,))
                brute = cur.fetchone()


                return RedirectResponse(url="/login", status_code=status.HTTP_403_FORBIDDEN)
            #cur.execute("INSERT INTO transactions (id, amount, timestamp, account_id, merchant_id, status) VALUES (%s, %s, %s, %s, %s, %s)", (tx.id, tx.amount, tx.timestamp, tx.account_id, tx.receiver_id, tx.status) )
            #conn.commit()
            expires_at = datetime.utcnow() + timedelta(minutes=20)
            payload = {
                "userid": auth.login,
                "true_userid": true_user_id,
                "exp": expires_at
        }
            token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
            response = RedirectResponse("/home", status_code=status.HTTP_303_SEE_OTHER)
            response.set_cookie(
                key="session_id",
                value=token,
                httponly=True,
                max_age=1200,
                expires=1200,
                samesite="lax",
                secure=False
                # Мы не будем использовать сертификаты шифрования TLS,
                # поэтому флаг secure в куках останется False,
                # дабы не нарушить работу приложения.
            )

            cur.execute(
                "INSERT INTO active_session (userid, token, expires_at) VALUES (%s, %s, %s)",
                (auth.login, token, expires_at)
            )
            conn.commit()

            return response

        return RedirectResponse(url="/login?error=invalid_credentials", status_code=303)
    except:
        f=1
        #убрать

@app.post("/api/logout")
async def logout(response: Response, request: Request, token_data: tuple[str, str] = Depends(verify_token),):
    user_id, true_user_id = token_data
    token = request.cookies.get("session_id")
    if token_data:
        cur.execute("DELETE FROM active_session WHERE token = %s", (token,))
        conn.commit()

    response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("session_id")
    return response