# logging_config.py
"""
Logging configuration for P2P Management System
This module sets up logging to both a file and the console with a clean format.

"""

import logging
import os


def setup_logging(log_filename='application.log', log_level=logging.INFO, log_dir='logs'):
    """
    Configure application logging with file and console output.
    
    Args:
        log_filename: Name of the log file
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory to store log files
    
    Returns:
        logging.Logger: Configured root logger
    """
    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)
    
    # Get root logger and clear existing handlers
    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    logger.setLevel(log_level)
    
    # Create clean, readable formatter
    formatter = logging.Formatter(
        '%(asctime)s:%(name)s:%(levelname)s:%(message)s'
    )
    
    # File handler for persistent logging
    file_handler = logging.FileHandler(
        os.path.join(log_dir, log_filename),
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler for real-time monitoring
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Reduce external library noise
    external_loggers = ['aiohttp', 'websockets', 'asyncio']
    for logger_name in external_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    return logger