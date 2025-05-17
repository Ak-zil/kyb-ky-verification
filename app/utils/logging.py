import logging
import sys
from typing import Any, Dict, Optional

from app.core.config import settings


class CustomFormatter(logging.Formatter):
    """Custom formatter adding colors to the logs"""
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: grey + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger"""
    logger = logging.getLogger(name)
    
    # Set level from settings
    level = getattr(logging, settings.LOG_LEVEL)
    logger.setLevel(level)
    
    # Add handler if not already added
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(CustomFormatter())
        logger.addHandler(handler)
    
    return logger


def log_request(request_data: Dict[str, Any], context: Optional[str] = None) -> None:
    """Log an API request"""
    logger = get_logger("api")
    context_str = f" [{context}]" if context else ""
    logger.info(f"Request{context_str}: {request_data}")


def log_response(response_data: Dict[str, Any], context: Optional[str] = None) -> None:
    """Log an API response"""
    logger = get_logger("api")
    context_str = f" [{context}]" if context else ""
    logger.info(f"Response{context_str}: {response_data}")


def log_error(error: Exception, context: Optional[str] = None) -> None:
    """Log an error"""
    logger = get_logger("error")
    context_str = f" [{context}]" if context else ""
    logger.error(f"Error{context_str}: {str(error)}", exc_info=True)