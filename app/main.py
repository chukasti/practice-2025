from enum import Enum
from pydantic import BaseModel
from fastapi import FastAPI, Request, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import secrets
from fastapi.responses import FileResponse
#from models.transaction import Transaction
#from api.v1.transactions import TransactionCreate
from datetime import datetime

from starlette.responses import HTMLResponse, FileResponse


class TransactionNew(BaseModel):
    id: int
    amount: int
    senderId: str
    receiverId: str

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


@app.post("/api/login")
async def try_login(rekvi: LoginPass, response: Response, request: Request):
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
        return "Вы успешно авторизованы."
    #добавить логирование неуспешных попыток авторизации
    return "Ошибка"

@app.post("/api/transaction")
async def send_transaction(transaction: TransactionNew):
    resulted = 1.0
    if transaction.amount > 0:
        resulted += transaction.amount
    #return {"resulted": resulted}
    return "Транзакция обработана"