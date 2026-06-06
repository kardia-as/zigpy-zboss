"""Module setting up the serial logger."""
import logging
import logging.handlers
import sys

from zigpy_zboss.config import SERIAL_LOG_FILE_NAME

SERIAL_LOGGER = logging.getLogger(__name__)

LOG_FORMAT = ("%(asctime)s [%(levelname)s]: %(message)s")
LOG_LEVEL = logging.DEBUG

# Use a separate log file when running under pytest to avoid polluting the
# real HA serial log with mock traffic from the test suite.
# pytest is already in sys.modules by the time conftest.py imports zigpy_zboss.
_under_pytest = "pytest" in sys.modules
_log_prefix = "pytest-" if _under_pytest else ""
default_log_file_path = "/tmp/" + _log_prefix + SERIAL_LOG_FILE_NAME

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
