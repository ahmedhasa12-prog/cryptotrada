FROM python:3.14-slim AS builder

WORKDIR /app

# Install Node.js 20
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Build frontend
COPY frontend/ ./frontend/
RUN cd frontend && npm install && npm run build

# Copy backend
COPY main.py .
COPY web/ ./web/
COPY spot/ ./spot/
COPY data/ ./data/
COPY .env.example .

# Expose port
EXPOSE 8001

# Start
CMD ["python3", "main.py"]
