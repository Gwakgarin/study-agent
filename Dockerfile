# --- 1) Build the React frontend ---
FROM node:20-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- 2) Python API that also serves the built frontend ---
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY server.py ./
# Sample SQLD notes behind the "try a sample subject" button.
COPY eval/corpus/ ./eval/corpus/
COPY --from=frontend /frontend/dist ./frontend/dist

# Notes, FAISS indexes and tracker.db live here; mount a volume to keep them.
RUN mkdir -p data
VOLUME ["/app/data"]

EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
