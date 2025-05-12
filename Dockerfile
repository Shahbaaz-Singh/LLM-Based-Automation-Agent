# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies in a single layer and clean up unnecessary files
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    sqlite3 \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    && curl -fsSL https://deb.nodesource.com/setup_16.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Verify installation of Node.js and npm
RUN node --version && npm --version

# Install Prettier globally in a single layer and clean npm cache
RUN npm install -g prettier@3.4.2 && npm cache clean --force

# Copy only requirements.txt first to leverage caching for Python dependencies
COPY requirements.txt .

# Install Python dependencies separately to avoid reinstallation if only code changes
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files into the container (excluding unnecessary files via .dockerignore)
COPY . .

# Expose port 8000 for FastAPI
EXPOSE 8000

# Set environment variables
ENV AIPROXY_TOKEN=""
ENV PYTHONPATH=/app

# Command to run the FastAPI app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]