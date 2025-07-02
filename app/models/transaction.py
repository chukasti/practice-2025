class Transaction(BaseModel):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    account_id = Column(String, nullable=False)
    merchant_id = Column(String, nullable=True)
    status = Column(String, nullable=False)
