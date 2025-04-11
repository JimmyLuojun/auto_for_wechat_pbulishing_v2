# tests/utils/test_logging_setup.py
import pytest
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler # Import for isinstance check
# Adjust import path if necessary based on your project structure
from auto_for_wechat_publishing.utils.logging_setup import setup_logging, DEFAULT_FORMAT

# CORRECTED Fixture to reset logging state before each test
@pytest.fixture(autouse=True)
def reset_logging_state():
    """Reset root logger level AND remove handlers added DURING the test."""
    root_logger = logging.getLogger()
    original_level = root_logger.level
    # Store handlers present BEFORE the test runs
    # IMPORTANT: Copy the list, don't store a reference
    handlers_before = root_logger.handlers[:]

    yield # Run the test

    # Restore original level
    root_logger.setLevel(original_level)
    # Remove handlers added DURING the test
    handlers_after = root_logger.handlers[:]
    handlers_to_remove = [h for h in handlers_after if h not in handlers_before]
    for handler in handlers_to_remove:
        # Close file handlers before removing
        if isinstance(handler, logging.FileHandler):
            # Ensure handler is properly closed before removal
            try:
                handler.close()
            except Exception:
                # Ignore errors during close, main goal is removal
                pass
        root_logger.removeHandler(handler)


# --- Test Functions ---

def test_setup_logging_defaults(caplog):
    """Test setup_logging with defaults (INFO level, stdout)."""
    caplog.set_level(logging.INFO)

    setup_logging()
    root_logger = logging.getLogger()

    assert root_logger.level == logging.INFO
    stream_handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler) and h.stream == sys.stdout]
    assert len(stream_handlers) >= 1
    handler = stream_handlers[0]
    assert handler.formatter is not None
    assert handler.formatter._fmt == DEFAULT_FORMAT

    test_message = "Default setup test message"
    logging.info(test_message)
    assert test_message in caplog.text


def test_setup_logging_custom_level_debug(caplog):
    """Test that a custom log level (DEBUG) is properly set."""
    caplog.set_level(logging.DEBUG)

    setup_logging(log_level_str='DEBUG')
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG

    test_message = "Debug level test message"
    logging.debug(test_message)
    assert test_message in caplog.text


def test_setup_logging_with_file(tmp_path, caplog):
    """Test setup_logging with a log file specified."""
    log_file = tmp_path / "app.log"
    caplog.set_level(logging.WARNING)

    setup_logging(log_level_str="WARNING", log_file=str(log_file))
    root_logger = logging.getLogger()

    assert root_logger.level == logging.WARNING
    stream_handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler) and h.stream == sys.stdout]
    file_handlers = [h for h in root_logger.handlers if isinstance(h, RotatingFileHandler)]

    assert len(stream_handlers) >= 1
    assert len(file_handlers) == 1

    file_handler = file_handlers[0]
    assert Path(file_handler.baseFilename) == log_file.resolve()
    assert file_handler.formatter._fmt == DEFAULT_FORMAT
    assert file_handler.level == logging.WARNING

    test_warning = "This should go to file and console"
    logging.warning(test_warning)

    assert test_warning in caplog.text
    assert log_file.exists()
    log_content = log_file.read_text()
    assert test_warning in log_content

    test_info = "This is just info"
    logging.info(test_info)
    assert test_info not in caplog.text
    log_content_after_info = log_file.read_text()
    assert test_info not in log_content_after_info


def test_setup_logging_file_error(tmp_path, mocker, caplog):
    """Test that if file logging fails, console logging continues to work."""
    log_dir = tmp_path / "no_permission_dir"
    log_file_path = log_dir / "app.log"

    # Mock 'any' to bypass duplicate check
    mock_any = mocker.patch('builtins.any', return_value=False)

    # --- FINAL MOCK PATH ATTEMPT ---
    # Patch the name 'RotatingFileHandler' directly within the setup_logging module's scope.
    # This requires knowing the full path to the setup_logging module.
    MODULE_PATH = "auto_for_wechat_publishing.utils.logging_setup"
    mock_rfh_constructor = mocker.patch(
        f"{MODULE_PATH}.RotatingFileHandler", # Target the name inside the module under test
        side_effect=OSError("Simulated OS Error on file creation/access")
    )

    caplog.set_level(logging.INFO) # Capture INFO and ERROR messages

    # Call the function under test
    setup_logging(log_level_str="INFO", log_file=str(log_file_path))

    root_logger = logging.getLogger()

    # Ensure 'any' was checked
    assert mock_any.called

    # Assert that the attempt to create the handler was made
    # The mock constructor itself should have been called
    mock_rfh_constructor.assert_called_once_with(
        log_file_path, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
    )

    # Check that NO file handler was actually added to the root logger
    actual_file_handlers = [
        h for h in root_logger.handlers
        if isinstance(h, logging.handlers.RotatingFileHandler) and not isinstance(h, mocker.MagicMock) # Exclude mocks
    ]
    assert len(actual_file_handlers) == 0

    # Check that the console handler IS still present
    stream_handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler) and h.stream == sys.stdout]
    assert len(stream_handlers) >= 1

    # Verify that the specific ERROR message about the failure was logged
    assert "Failed to configure file logging" in caplog.text
    assert "Simulated OS Error on file creation/access" in caplog.text

    # Verify that the SUCCESS message for file logging was NOT logged
    assert f"Outputting to console and file: {log_file_path}" not in caplog.text

    # Ensure console logging still works for messages logged *after* setup
    test_message = "Console logging still works after file error"
    logging.info(test_message)
    assert test_message in caplog.text