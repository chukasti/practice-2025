import requests
from passlib.context import CryptContext

user_id = input("Введите user_id (минимальное значение 1): ")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password_plain = input("Введите пароль: ")
password_hashed = pwd_context.hash(password_plain)
username = input("Введите username: ")
role = input("Введите роль (admin или user): ")
name_surname = input("Введите имя и фамилию: ")
balance=input("Введите, сколько денег хотите иметь на счету: ")
account_status=input("Введите статус аккаунта [normal или restricted]: ")


payload = {
  "user_id": f"{user_id}",
  "hashed_password": f"{password_hashed}",
  "username": f"{username}",
  "role": "admin",
  "name_surname": "admin admin",
  "balance": "100000",
  "account_status": "normal"
}

response = requests.post("http://127.0.0.1:8000/api/register", json=payload)
print(response.status_code)
print(response.text)