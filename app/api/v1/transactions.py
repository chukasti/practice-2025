class TransactionCreate(BaseModel):
    amount: float
    timestamp: datetime
    account_id: str
    merchant_id: Optional[str] = None
    status: str
