FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

# התקנת תלויות
COPY backend/requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; else pip install --no-cache-dir fastapi uvicorn google-cloud-aiplatform vertexai; fi

# העתקת קבצי הקוד
COPY . .

# הפעלת שרת ה-FastAPI ב-Cloud Run
CMD exec uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT}
