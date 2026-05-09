# Use the Python 3.12 image as the base image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /usr/local/share/bot

# Install PostgreSQL development libraries and system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    libffi-dev \
    libsodium-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy package metadata and source into the container
COPY pyproject.toml README.md ./
COPY bot ./bot

# Install the Python dependencies
RUN pip install --no-cache-dir .

# At runtime, this will be the default command, but it's overridden by the docker-compose.yml command
CMD ["python", "bot.py"]
