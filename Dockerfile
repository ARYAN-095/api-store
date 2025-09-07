# api-store/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system deps (optional but often needed, e.g. psycopg2, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose FastAPI port
EXPOSE 8085

# Default command for the API container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8085"]
