# study_bites/logger.py
import logging
import os

log_dir = os.path.join(os.getcwd(), 'logs')
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, 'app.log')

# Create logger
logger = logging.getLogger("study_bites")
logger.setLevel(logging.INFO)

# Avoid adding handlers multiple times
if not logger.hasHandlers():
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Optional: also log to stderr
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
