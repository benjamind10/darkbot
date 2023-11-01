# db.py
import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Connection parameters
params = {
    "dbname": os.getenv("DBNAME"),
    "user": os.getenv("DBUSER"),
    "password": os.getenv("DBPASS"),
    "host": os.getenv("DBHOST"),
    "port": int(os.getenv("DBPORT")),
}


def get_connection():
    return psycopg2.connect(**params)
