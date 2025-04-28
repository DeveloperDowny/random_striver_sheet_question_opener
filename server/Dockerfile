FROM python:3.11-slim

WORKDIR /app

# Install dependencies first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose API port
EXPOSE 8080

# Set environment variables (override with docker run -e)
ENV ENV_FILE_PATH=/app/.env

# Command to run the API server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]