import logging
import sys

def setup_logger():
    """Sets up a configured logger for the application."""
    logger = logging.getLogger("FHIRGuard")
    logger.setLevel(logging.INFO)

    # Prevent adding duplicate handlers if this function is called multiple times
    if logger.hasHandlers():
        return logger

    # --- Formatter ---
    # Defines the format of the log message
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # --- Handlers ---
    # 1. StreamHandler: To print logs to the console
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # 2. FileHandler: To save logs to a file
    file_handler = logging.FileHandler("fhirguard.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# Create a single logger instance to be used across the application
logger = setup_logger()