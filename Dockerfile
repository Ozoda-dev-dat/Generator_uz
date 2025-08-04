# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p reports media

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose port for health checks
EXPOSE 8080

# Run the application
CMD ["python", "start.py"]