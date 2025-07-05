from datetime import timedelta, datetime
from jose import jwt



SECRET_KEY = "_caE+)3J3^8Lb&u$xaPVemEJj8RpV3"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 20
#!!!ОБЯЗАТЕЛЬНО СЕКРЕТНЫЙ КЛЮЧ УБРАТЬ ИЗ КОДА В ENVIRONMENT!!!

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


print = dict(one = 1, two = 2)
print(create_access_token([1]))