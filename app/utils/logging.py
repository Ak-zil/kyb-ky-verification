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


# Global flag to track if logging has been setup
_logging_configured = False


def setup_logging(log_level: str = None) -> None:
    """
    Setup root logging configuration for the entire application
    
    Args:
        log_level: Log level to use (defaults to settings.LOG_LEVEL)
    """
    global _logging_configured
    
    if _logging_configured:
        return
    
    log_level = log_level or settings.LOG_LEVEL
    
    # Get root logger
    root_logger = logging.getLogger()
    
    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set root logger level
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Set formatter
    console_handler.setFormatter(CustomFormatter())
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    logging.getLogger("arq").setLevel(logging.INFO)
    logging.getLogger("verification_worker").setLevel(logging.INFO)
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("aiomysql").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    
    # Mark as configured
    _logging_configured = True
    
    # Test logging
    root_logger.info("🚀 Logging system initialized")

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