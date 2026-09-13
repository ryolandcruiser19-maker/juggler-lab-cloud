FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONPATH=/app:/app/scripts \
    CLOUD_MODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    nginx \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN playwright install --with-deps chromium

COPY . .

RUN python scripts/inject_manifest.py

RUN rm -f /etc/nginx/sites-enabled/default \
    && cp /app/nginx.conf /etc/nginx/nginx.conf

EXPOSE 8080

CMD ["sh", "-c", "uvicorn sync_api:app --host 0.0.0.0 --port 8000 & streamlit run app_ui_v8.py --server.address=0.0.0.0 --server.port=8501 & nginx -g 'daemon off;'"]
