"""Configuration module for loading settings from .env and settings.ini."""

import os
from configparser import ConfigParser
from pathlib import Path
from typing import Dict, Any

import dotenv

# Load environment variables
dotenv.load_dotenv()

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

def load_settings() -> Dict[str, Any]:
    """Load settings from settings.ini and .env files."""
    config = ConfigParser()
    config.read(PROJECT_ROOT / "config" / "settings.ini")

    # Convert config to dictionary
    settings = {
        "paths": dict(config["paths"]),
        "wechat": dict(config["wechat"]),
        "content": dict(config["content"]),
    }

    # Add environment variables
    settings["wechat"]["app_id"] = os.getenv("WECHAT_APPID")
    settings["wechat"]["secret"] = os.getenv("WECHAT_SECRET")

    # Convert numeric values
    settings["wechat"]["token_expiry"] = int(settings["wechat"]["token_expiry"])
    settings["content"]["max_image_size"] = int(settings["content"]["max_image_size"])

    return settings

# Load settings when module is imported
SETTINGS = load_settings() 