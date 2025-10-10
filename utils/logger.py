import os
import logging
import logging.config

from datetime import datetime

logger = logging.getLogger(__name__)

def configureLogger(logLevel: str):
    log_directory = "logs"

    # Ensure the directory exists
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    log_filename = f"{log_directory}/crypto_bot_{datetime.now().strftime('%Y%m%d')}.log"

    logging.config.fileConfig("./config/logging.conf", defaults={'logfilename': log_filename}, disable_existing_loggers=False)

    if not logLevel: 
        return
    
    numeric_level = getattr(logging, logLevel.upper(), None)
    if  not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % logLevel)

    # Set root logger to INFO to quiet third-party libraries
    logging.getLogger().setLevel(logging.INFO)
    
    # Only set DEBUG for our bot's modules
    if numeric_level == logging.DEBUG:
        logging.getLogger('strategies').setLevel(logging.DEBUG)
        logging.getLogger('utils').setLevel(logging.DEBUG)
        logging.getLogger('crypto_bot').setLevel(logging.DEBUG)
        logging.getLogger('__main__').setLevel(logging.DEBUG)
    else:
        # For other levels, apply to our modules too
        logging.getLogger('strategies').setLevel(numeric_level)
        logging.getLogger('utils').setLevel(numeric_level)
        logging.getLogger('crypto_bot').setLevel(numeric_level)
        logging.getLogger('__main__').setLevel(numeric_level)

# Configure logger with level from environment variable, default to INFO
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
configureLogger(LOG_LEVEL)