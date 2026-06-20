FROM python:3.11-slim

WORKDIR /app

COPY aegis-credit/backend/requirements.txt .
RUN pip install -r requirements.txt

COPY aegis-credit/backend/ .

EXPOSE 8080

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
