FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8080

# התקנת כל הספריות הדרושות
RUN pip install --no-cache-dir fastapi uvicorn google-cloud-aiplatform vertexai cachetools tenacity pydantic requests

# העתקת קבצי הקוד
COPY . .

# הפעלת Uvicorn עם קישור מדויק לפורט של Cloud Run
CMD ["sh", "-c", "uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
