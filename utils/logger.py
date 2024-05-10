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

    logging.getLogger().setLevel(numeric_level)

configureLogger("INFO")