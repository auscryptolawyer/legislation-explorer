import logging
import os
import sys
import json
from datetime import datetime

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        if record.__dict__.get("extra_info"):
            log_record.update(record.extra_info)
        return json.dumps(log_record)

def setup_logging():
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    dev_mode = os.environ.get("DEV_MODE", "True").lower() == "true"

    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Clear existing handlers to avoid duplicate logs in reloaded environments
    if logger.hasHandlers():
        logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if dev_mode:
        formatter = logging.Formatter(
            "%(levelname)s:     %(name)s - %(message)s (%(filename)s:%(lineno)d)"
        )
    else:
        formatter = JsonFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Configure uvicorn access logger to use our handler
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers.clear()
    uvicorn_access_logger.addHandler(handler)
    uvicorn_access_logger.propagate = False # Prevent logs from going to root logger again

    # Disable uvicorn default handler to prevent duplicate logging
    from uvicorn.config import LOGGING_CONFIG
    LOGGING_CONFIG["formatters"]["default"]["fmt"] = "%(message)s" # This won't be used if propagate is False

    # Example of how to get a logger in other modules
    # logger = logging.getLogger(__name__)

# Call setup_logging when this module is imported
setup_logging()
