from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Регистрация — хэшируем
password_plain = "admin"
password_hashed = pwd_context.hash(password_plain)
# Сохраняем password_hashed в БД
print(password_hashed)

# Аутентификация — проверка
user_input = "supersecret"
is_valid = pwd_context.verify(user_input, password_hashed)
print(is_valid)  # True
