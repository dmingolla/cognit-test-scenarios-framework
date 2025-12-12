"""
Simple logger with rotation for COGNIT test framework.
"""

import logging
from logging.handlers import RotatingFileHandler
import os

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Configure logger
logger = logging.getLogger("cognit_framework")
logger.setLevel(logging.DEBUG)

# Prevent duplicate handlers if logger is reinitialized
if not logger.handlers:
    # File handler with rotation (10MB per file, keep 5 backup files)
    log_file = os.path.join(LOGS_DIR, "cognit_framework.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler for important messages
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    
    # Format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# Export logger
__all__ = ['logger']

