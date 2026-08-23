FROM python:3.11-slim

# מניעת קובצי pyc והזרמת לוגים מיידית
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

# התקנת ספריות מערכת בסיסיות
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# העתקת requirements מתוך תיקיית backend והתקנה
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# העתקת קוד ה-backend ומפרט ה-OpenAPI
COPY backend/ ./backend/
COPY openapi.yaml ./openapi.yaml

# חשיפת הפורט עבור Cloud Run
EXPOSE 8080

# הפעלת FastAPI על 0.0.0.0 ופורט 8080
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
