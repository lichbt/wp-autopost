import logging
import sys
from config import LOG_FULL_PATH, ensure_directories


def setup_logger(name: str = "content_automation") -> logging.Logger:
    """
    Configure logging to both console and file.
    
    Args:
        name: Logger name (default: content_automation)
    
    Returns:
        Configured logger instance
    """
    # Ensure log directory exists
    ensure_directories()
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Prevent duplicate handlers if already configured
    if logger.handlers:
        return logger
    
    # Create formatters
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    file_handler = logging.FileHandler(LOG_FULL_PATH, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# Global logger instance
logger = setup_logger()
