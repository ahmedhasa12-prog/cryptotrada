# ── Stage 1: Build Vue frontend ────────────────────────────────────────────
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python runtime ────────────────────────────────────────────────
FROM python:3.13-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source (excluding files listed in .dockerignore)
COPY . .

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Ensure persistent-volume mount point and logs dir exist
RUN mkdir -p /app/data /app/logs

EXPOSE 8000

CMD ["python", "main.py"]
