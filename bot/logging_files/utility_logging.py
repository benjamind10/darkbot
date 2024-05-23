import logging
from logging.handlers import RotatingFileHandler


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")

file_handler = RotatingFileHandler(
    "./logs/utility.log", maxBytes=10 * 1024 * 1024, backupCount=1
)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
