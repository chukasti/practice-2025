from enum import Enum
from pydantic import BaseModel
from fastapi import FastAPI
#from models.transaction import Transaction
#from api.v1.transactions import TransactionCreate
from datetime import datetime


class TransactionNew(BaseModel):
    id: int
    amount: int
    senderId: str
    receiverId: str




app = FastAPI()


@app.post("/api/transaction")
async def send_transaction(transaction: TransactionNew):
    resulted = 1.0
    if transaction.amount > 0:
        resulted += transaction.amount
    return {"resulted": resulted}

