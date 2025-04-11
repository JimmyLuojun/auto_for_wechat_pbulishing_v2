# src/auto_for_wechat_publishing/utils/config_loader.py
"""
config_loader.py

Loads configuration settings from an INI file.

Dependencies:
    - configparser

Input: path to config.ini file
Output: configuration dictionary
"""

"""
config_loader.py

Loads configuration settings from an INI file and environment variables.
"""

import configparser
import logging
import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def load_config(config_path: str, env_path: str | None = None) -> Dict[str, Any]:
    """Loads configuration from INI file and merges .env variables."""
    # Load .env file first if specified
    if env_path:
        env_p = Path(env_path)
        if env_p.is_file():
            load_dotenv(dotenv_path=env_p, override=True)
            logger.info(f"Loaded environment variables from {env_path}")
        else:
            logger.warning(f".env file not found at {env_path}, relying on environment.")
    else:
        # Default location if not specified
        default_env_path = Path('.') / '.env'
        if default_env_path.is_file():
             load_dotenv(dotenv_path=default_env_path, override=True)
             logger.info(f"Loaded environment variables from default .env file")


    config_file = Path(config_path)
    if not config_file.is_file():
        logger.error(f"Config file not found: {config_path}")
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    config = configparser.ConfigParser()
    try:
        config.read(config_path, encoding='utf-8')
    except configparser.Error as e:
        logger.error(f"Failed to parse config file {config_path}: {e}")
        raise ValueError(f"Failed to parse config file {config_path}") from e

    config_dict: Dict[str, Any] = {
        section: dict(config.items(section)) for section in config.sections()
        }

    # Optionally add environment variables under a specific key or merge them
    # For simplicity, let's keep them separate for now, accessed via os.getenv
    # You could merge them like:
    # config_dict['ENV'] = dict(os.environ)

    logger.info(f"Config loaded successfully from {config_path}")
    return config_dict

def get_env_variable(var_name: str, required: bool = True) -> str | None:
    """Gets an environment variable, raising error if required and not found."""
    value = os.getenv(var_name)
    if required and value is None:
        logger.error(f"Required environment variable '{var_name}' not set.")
        raise ValueError(f"Required environment variable '{var_name}' not set.")
    return value
