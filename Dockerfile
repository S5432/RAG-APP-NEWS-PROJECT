# Use Python 3.12 slim image for smaller size
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install system dependencies required by Playwright Chromium
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    fonts-liberation \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgdk-pixbuf2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    libgbm1 \
    libxshmfence1 \
    libxcb1 \
    libxext6 \
    libxfixes3 \
    libglib2.0-0 \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browser binaries
RUN pip install --no-cache-dir playwright
RUN playwright install --with-deps

# Expose FastAPI default port
EXPOSE 8080

# Run the FastAPI application using uvicorn.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
