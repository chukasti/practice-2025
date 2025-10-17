FROM python:3.12

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .
CMD ["sh", "-c", "\
  sleep 5 && \
  cd /app/alembic_audit && alembic upgrade head && \
  cd /app/alembic_db && alembic upgrade head && cd /app && \
  exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4\
"]