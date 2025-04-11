# auto_for_wechat_publishing/utils/logging_setup.py
"""
logging_setup.py

Initializes and configures logging for the application.

Dependencies:
    - logging

Input: optional log file path
Output: configured logger
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path # Import Path

DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

def setup_logging(log_level_str: str = 'INFO', log_file: str | None = None, log_format: str = DEFAULT_FORMAT):
    """Sets up the logging configuration."""
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    # Get the root logger
    # It's generally better practice to configure a specific logger for your app
    # rather than the root logger directly, but we'll stick to the root logger
    # as per the original code for now.
    logger = logging.getLogger()

    # *** DO NOT REMOVE EXISTING HANDLERS HERE ***
    # Let pytest and caplog manage handlers during tests.
    # In a real app, you might want logic to prevent adding duplicate handlers
    # if setup_logging could be called multiple times, but for typical usage
    # where it's called once at startup, this is fine.

    # Ensure root logger's level is set AT LEAST to the desired level
    # If it's already lower (e.g., DEBUG), leave it, otherwise set it.
    if logger.level == logging.NOTSET or logger.level > log_level:
         logger.setLevel(log_level)

    # Create formatter
    formatter = logging.Formatter(log_format)

    # --- Console Handler ---
    # Check if a similar console handler already exists to avoid duplicates in non-test scenarios
    has_console_handler = any(
        isinstance(h, logging.StreamHandler) and h.stream == sys.stdout
        for h in logger.handlers
    )
    if not has_console_handler:
        console_handler = logging.StreamHandler(sys.stdout)
        # Set handler level - messages below this won't pass through this handler
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        added_console = True
    else:
        added_console = False
        logger.debug("Console handler already exists. Skipping add.")


    # --- File Handler ---
    added_file = False
    if log_file:
        log_file_path = Path(log_file).resolve()
        # Check if a similar file handler already exists
        has_file_handler = any(
            isinstance(h, RotatingFileHandler) and Path(h.baseFilename).resolve() == log_file_path
            for h in logger.handlers
        )

        if not has_file_handler:
            try:
                # Ensure parent directory exists before creating handler
                log_file_path.parent.mkdir(parents=True, exist_ok=True)

                # Use RotatingFileHandler for larger applications
                file_handler = RotatingFileHandler(
                    log_file_path, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
                )
                file_handler.setLevel(log_level) # Set handler level
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
                added_file = True
            except Exception as e:
                # Log error using the logger itself (which should have at least the console handler)
                logger.error(f"Failed to configure file logging for {log_file}: {e}. Logging to console only.")
        else:
             logger.debug(f"File handler for {log_file} already exists. Skipping add.")


    # Log confirmation message AFTER potentially adding handlers
    if added_console or added_file:
         config_msg_parts = [f"Logging configured. Level: {log_level_str}."]
         if added_console and added_file:
             config_msg_parts.append(f"Outputting to console and file: {log_file}")
         elif added_file:
              config_msg_parts.append(f"Outputting to file: {log_file}")
         elif added_console:
              config_msg_parts.append("Outputting to console only.")
         logger.info(" ".join(config_msg_parts))


    # Suppress noisy libraries if needed
    # logging.getLogger("requests").setLevel(logging.WARNING)
    # logging.getLogger("urllib3").setLevel(logging.WARNING)