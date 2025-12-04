# Use the Python 3.10 image as the base image
FROM python:3.10

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

# Copy the requirements.txt file into the container
COPY ./bot/requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Ensure redis asyncio client is installed (explicit, to avoid cached-broken builds)
RUN pip install --no-cache-dir redis==5.0.1
RUN pip install aiogoogletrans asyncurban ipinfo strgen forex-python bitlyshortener

# At runtime, this will be the default command, but it's overridden by the docker-compose.yml command
CMD ["python", "bot.py"]
