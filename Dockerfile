# Use the Python 3.10 image as the base image
FROM python:3.10

# Set the working directory inside the container
WORKDIR /usr/local/share/app

# Install PostgreSQL development libraries
RUN apt-get update && apt-get install -y libpq-dev gcc && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install psycopg2-binary

# Copy the requirements.txt file into the container
COPY ./app/requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# At runtime, this will be the default command, but it's overridden by the docker-compose.yml command
CMD ["python", "bot.py"]
