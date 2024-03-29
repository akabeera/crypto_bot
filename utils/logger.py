import os
import logging
import logging.config

logger = logging.getLogger(__name__)

def configureLogger(logLevel: str):
    log_directory = "logs"

    # Ensure the directory exists
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    logging.config.fileConfig("./config/logging.conf", disable_existing_loggers=False)

    if not logLevel: 
        return
    
    numeric_level = getattr(logging, logLevel.upper(), None)
    if  not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % logLevel)

    logging.getLogger().setLevel(numeric_level)

configureLogger("INFO")