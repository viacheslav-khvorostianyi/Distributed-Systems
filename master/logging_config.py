import logging
import sys


def setup_logger(name: str = None) -> logging.Logger:
    """Set up and return a configured logger."""
    logger = logging.getLogger(name or __name__)

    if not logger.handlers:  # Avoid duplicate handlers
        logger.setLevel(logging.INFO)

        # Create console handler with formatting
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        # Add handler to logger
        logger.addHandler(handler)

    return logger