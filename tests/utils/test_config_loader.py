# tests/utils/test_config_loader.py
import pytest
import os
from pathlib import Path
from auto_for_wechat_publishing.utils.config_loader import load_config, get_env_variable

# Use pytest's tmp_path fixture for creating temporary files
def test_load_config_success(tmp_path):
    """Test loading a valid config file."""
    config_file = tmp_path / "test_config.ini"
    config_content = """
[PATHS]
input_dir = data/input

[WECHAT_API]
base_url = https://api.test.com
"""
    config_file.write_text(config_content, encoding='utf-8')

    # Test without .env initially
    loaded_config = load_config(str(config_file))
    expected_config = {
        "PATHS": {"input_dir": "data/input"},
        "WECHAT_API": {"base_url": "https://api.test.com"}
    }
    assert loaded_config == expected_config

def test_load_config_with_env(tmp_path, monkeypatch):
    """Test loading config with .env file present."""
    config_file = tmp_path / "test_config.ini"
    config_content = "[SETTINGS]\nlevel = INFO"
    config_file.write_text(config_content, encoding='utf-8')

    env_file = tmp_path / ".env"
    env_content = "MY_VAR=test_value\nOTHER_VAR=123"
    env_file.write_text(env_content, encoding='utf-8')

    # Mock os.getenv if needed, but load_dotenv should handle it if called correctly
    # monkeypatch.setenv("MY_VAR", "env_value") # Can also test system env vars

    loaded_config = load_config(str(config_file), str(env_file))

    # Verify INI content loaded
    assert loaded_config == {"SETTINGS": {"level": "INFO"}}
    # Verify .env loaded into environment
    assert os.getenv("MY_VAR") == "test_value"
    assert os.getenv("OTHER_VAR") == "123"

    # Clean up env vars potentially set by load_dotenv
    monkeypatch.delenv("MY_VAR", raising=False)
    monkeypatch.delenv("OTHER_VAR", raising=False)


def test_load_config_file_not_found(tmp_path):
    """Test loading fails if config file doesn't exist."""
    non_existent_path = tmp_path / "non_existent_config.ini"
    with pytest.raises(FileNotFoundError, match="Configuration file not found"):
        load_config(str(non_existent_path))

def test_load_config_invalid_ini(tmp_path):
    """Test loading a malformed INI file."""
    config_file = tmp_path / "malformed.ini"
    config_content = "[SECTION\nkey=value" # Missing closing bracket
    config_file.write_text(config_content, encoding='utf-8')
    # configparser raises specific errors, wrapped in ValueError by our loader
    with pytest.raises(ValueError, match="Failed to parse config file"):
        load_config(str(config_file))

# --- Tests for get_env_variable ---

def test_get_env_variable_success(monkeypatch):
    """Test getting an existing environment variable."""
    var_name = "TEST_ENV_VAR"
    expected_value = "hello_world"
    monkeypatch.setenv(var_name, expected_value)
    assert get_env_variable(var_name, required=True) == expected_value
    assert get_env_variable(var_name, required=False) == expected_value

def test_get_env_variable_missing_required(monkeypatch):
    """Test getting a missing required variable raises ValueError."""
    var_name = "MISSING_REQUIRED_VAR"
    monkeypatch.delenv(var_name, raising=False) # Ensure it's not set
    with pytest.raises(ValueError, match=f"Required environment variable '{var_name}' not set."):
        get_env_variable(var_name, required=True)

def test_get_env_variable_missing_optional(monkeypatch):
    """Test getting a missing optional variable returns None."""
    var_name = "MISSING_OPTIONAL_VAR"
    monkeypatch.delenv(var_name, raising=False)
    assert get_env_variable(var_name, required=False) is None 