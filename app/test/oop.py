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

class Car:
    wheels = 4  # атрибут класса

    def __init__(self, color):
        self.color = color  # атрибут экземпляра

# создаём экземпляр
my_car = Car("red")
print(my_car.color)
print(my_car)


app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = "_caE+)3J3^8Lb&u$xaPVemEJj8RpV3"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 20
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_token(request: Request, token: str = Depends(oauth2_scheme)):
    try:
        token = request.cookies.get("session_id")
        if not token:
            return RedirectResponse("/login")
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


@app.get("/send_money", response_class=HTMLResponse)
def panel_page(request: Request):
    user_id = verify_token()

