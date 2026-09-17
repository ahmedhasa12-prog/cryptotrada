FROM python:3.14-slim

WORKDIR /app

# Install Node.js for frontend build
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Build frontend
COPY frontend/ ./frontend/
RUN cd frontend && npm install && npm run build

# Copy backend and data
COPY main.py .
COPY web/ ./web/
COPY spot/ ./spot/
COPY data/ ./data/

# Expose port
EXPOSE 8001

# Start the app
CMD ["python3", "main.py"]
