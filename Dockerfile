FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY elasticache_scanner/ ./elasticache_scanner/
COPY pyproject.toml .
COPY README.md .

# Install the package
RUN pip install -e .

# Create directory for AWS credentials (to be mounted)
RUN mkdir -p /root/.aws

# Create directory for output files
RUN mkdir -p /app/output

# Set default output directory
ENV OUTPUT_DIR=/app/output

# Default command
ENTRYPOINT ["python", "-m", "elasticache_scanner"]
CMD ["--help"]