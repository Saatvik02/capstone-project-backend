# Base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install pip & upgrade
RUN pip install --upgrade pip

# Copy requirements first (for better Docker caching)
COPY requirements.txt .

# Install Python packages
RUN pip install -r requirements.txt

# Copy the entire project
COPY . .

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "-m" ,"manage", "runserver"]
