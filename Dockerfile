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

# Install only the dependencies listed in pyproject.toml. Installing the
# project itself (`pip install .`) would put a frozen copy of the code into
# site-packages as the `bot` package, which goes stale as soon as ./bot is
# bind-mounted with newer code (see PR #34).
COPY pyproject.toml ./
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))" > /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Copy the bot source into the working directory so the image also runs
# without the docker-compose bind mount.
COPY bot/ ./

# docker-compose.yml overrides this with the same command
CMD ["python", "main.py"]
