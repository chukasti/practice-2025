from enum import Enum
from pydantic import BaseModel
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
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

@app.post("/api/transaction")
async def send_transaction(transaction: TransactionNew):
    resulted = 1.0
    if transaction.amount > 0:
        resulted += transaction.amount
    #return {"resulted": resulted}
    return "Транзакция обработана"