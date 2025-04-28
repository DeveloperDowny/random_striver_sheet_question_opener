# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Use --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . .

# Make port 8080 available to the world outside this container
# Cloud Run expects the container to listen on the port defined by the PORT env var (default 8080)
# While this specific bot uses polling and doesn't listen for HTTP requests directly from Cloud Run,
# defining a PORT is standard practice for Cloud Run services.
# The bot itself will initiate outbound connections to Telegram.
ENV PORT=8080

# Run telegram_bot.py when the container launches
# Use python -u for unbuffered output, helpful for logging
CMD ["python", "-u", "telegram_bot.py"]