FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

# התקנת curl לבדיקות תקינות
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# התקנת הספריות הדרושות ישירות (ללא תלות ב-requirements.txt)
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    google-cloud-aiplatform \
    cachetools \
    tenacity \
    pydantic \
    httpx

# העתקת הקוד הקיים ברפוזיטורי
COPY backend/ ./backend/
COPY openapi.yaml ./openapi.yaml

EXPOSE 8080

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
