"""Module setting up the serial logger."""
import logging
import logging.handlers

from zigpy_zboss.config import SERIAL_LOG_FILE_NAME

SERIAL_LOGGER = logging.getLogger(__name__)

LOG_FORMAT = ("%(asctime)s [%(levelname)s]: %(message)s")
LOG_LEVEL = logging.DEBUG
default_log_file_path = "/tmp/" + SERIAL_LOG_FILE_NAME

SERIAL_LOGGER.setLevel(LOG_LEVEL)
serial_logger_file_handler = logging.handlers.RotatingFileHandler(
    default_log_file_path,
    maxBytes=1024 * 1024,
    backupCount=5
)
serial_logger_file_handler.setLevel(LOG_LEVEL)
serial_logger_file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
SERIAL_LOGGER.propagate = False
SERIAL_LOGGER.addHandler(serial_logger_file_handler)
