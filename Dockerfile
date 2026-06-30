FROM python:3.11-slim

WORKDIR /app

# psycopg2-binary needs libpq at runtime on slim images
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 && rm -rf /var/lib/apt/lists/*

COPY aegis-credit/backend/requirements.txt .
RUN echo "bust:20260630" && pip install --no-cache-dir -r requirements.txt

COPY aegis-credit/backend/ .

EXPOSE 8080

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
