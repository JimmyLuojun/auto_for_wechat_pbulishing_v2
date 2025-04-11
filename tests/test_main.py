# tests/test_main.py
import pytest
import sys
from unittest.mock import MagicMock, ANY # ANY helps match complex args like callbacks
from pathlib import Path

# Import the function/module to test
# Assuming main.py contains the 'run' function
from auto_for_wechat_publishing import main

# Use marker to indicate these might be slower integration-style tests
# pytestmark = pytest.mark.integration

@pytest.fixture
def mock_dependencies(mocker):
    """Mock all major dependencies of the main.run function."""
    mocks = {
        "argparse": mocker.patch('argparse.ArgumentParser', return_value=MagicMock()),
        # Use correct paths relative to where they are imported in main.py
        "load_config": mocker.patch('auto_for_wechat_publishing.main.load_config'),
        "get_env": mocker.patch('auto_for_wechat_publishing.main.get_env_variable'),
        "setup_logging": mocker.patch('auto_for_wechat_publishing.main.setup_logging'),
        "get_access_token": mocker.patch('auto_for_wechat_publishing.main.get_access_token'),
        "extract_metadata": mocker.patch('auto_for_wechat_publishing.main.extract_metadata'),
        "upload_thumb": mocker.patch('auto_for_wechat_publishing.main.upload_thumb_media'),
        "extract_content": mocker.patch('auto_for_wechat_publishing.main.extract_markdown_content'),
        "process_html": mocker.patch('auto_for_wechat_publishing.main.process_html_content'),
        "build_payload": mocker.patch('auto_for_wechat_publishing.main.build_draft_payload'),
        "add_draft": mocker.patch('auto_for_wechat_publishing.main.add_draft'),
        # --- FIX: Make sys.exit raise SystemExit ---
        "sys_exit": mocker.patch('sys.exit', side_effect=SystemExit),
    }
    # Default successful return values
    mocks["argparse"].return_value.parse_args.return_value = MagicMock(
        markdown_file="path/to/article.md",
        config="config.ini",
        env=".env"
    )
    mocks["load_config"].return_value = {
        "LOGGING": {"level": "INFO", "log_file": None},
        "WECHAT_API": {"base_url": "https://fake.api"},
        "PATHS": {"css_template": "style.css"}
    }
    # Default side effect relies on default required=True in function signature
    mocks["get_env"].side_effect = lambda key, required=True: f"mock_{key}"
    mocks["get_access_token"].return_value = "mock_access_token"
    mocks["extract_metadata"].return_value = {
        "title": "Mock Title",
        "cover_image_path": "path/to/cover.jpg"
    }
    mocks["upload_thumb"].return_value = "mock_thumb_id_123"
    mocks["extract_content"].return_value = "## Mock Markdown Content"
    mocks["process_html"].return_value = "<style></style><h2>Mock HTML</h2>"
    mocks["build_payload"].return_value = {"articles": [{"title": "Mock Title", "...": "..."}]}
    mocks["add_draft"].return_value = "mock_draft_media_id_456"

    return mocks


def test_main_run_success_path(mock_dependencies, capsys):
    """Test the successful execution path of main.run."""

    main.run()

    # Assertions
    mock_dependencies["argparse"].return_value.parse_args.assert_called_once()
    mock_dependencies["load_config"].assert_called_once_with("config.ini", ".env")
    # --- FIX: Correct get_env assertion to match actual call ---
    mock_dependencies["get_env"].assert_any_call("WECHAT_APP_ID") # Rely on default required=True
    mock_dependencies["get_env"].assert_any_call("WECHAT_APP_SECRET") # Rely on default required=True
    mock_dependencies["setup_logging"].assert_called_once()
    mock_dependencies["get_access_token"].assert_called_once_with("mock_WECHAT_APP_ID", "mock_WECHAT_APP_SECRET", "https://fake.api")
    mock_dependencies["extract_metadata"].assert_called_once_with(Path("path/to/article.md"))
    mock_dependencies["upload_thumb"].assert_called_once_with("mock_access_token", "path/to/cover.jpg", "https://fake.api")
    mock_dependencies["extract_content"].assert_called_once_with(Path("path/to/article.md"))
    mock_dependencies["process_html"].assert_called_once_with(
        md_content="## Mock Markdown Content",
        css_path="style.css",
        markdown_file_path=Path("path/to/article.md"),
        image_uploader=ANY
    )
    mock_dependencies["build_payload"].assert_called_once_with(
        mock_dependencies["extract_metadata"].return_value,
        "<style></style><h2>Mock HTML</h2>",
        "mock_thumb_id_123"
    )
    mock_dependencies["add_draft"].assert_called_once_with(
        "mock_access_token",
        mock_dependencies["build_payload"].return_value,
        "https://fake.api"
    )

    # sys.exit should not have been called
    mock_dependencies["sys_exit"].assert_not_called()

    captured = capsys.readouterr()
    assert "Success! Article 'Mock Title' uploaded as draft." in captured.out
    assert "Draft Media ID: mock_draft_media_id_456" in captured.out


def test_main_run_config_load_error(mock_dependencies, capsys):
    """Test SystemExit if config loading fails."""
    config_error_msg = "Config file missing"
    mock_dependencies["load_config"].side_effect = FileNotFoundError(config_error_msg)

    # --- FIX: Expect SystemExit ---
    with pytest.raises(SystemExit) as e:
        main.run()

    # Optional: Check exit code if needed (SystemExit stores it)
    # assert e.value.code == 1

    # Check that sys.exit mock was called (indirectly via SystemExit)
    mock_dependencies["sys_exit"].assert_called_once()

    captured = capsys.readouterr()
    # Check the error message from the *first* except block
    assert f"Error: Configuration failed. {config_error_msg}" in captured.err
    assert "An unexpected error occurred" not in captured.err # Check outer block wasn't hit


def test_main_run_env_var_error(mock_dependencies, capsys):
    """Test SystemExit if required env var is missing."""
    get_env_error_msg = "Required environment variable 'WECHAT_APP_ID' not set."
    def get_env_side_effect(key, required=True): # Match signature
        if key == "WECHAT_APP_ID":
            # Raise error only if required=True (which is default)
            if required:
                 raise ValueError(get_env_error_msg)
        return f"mock_{key}"
    mock_dependencies["get_env"].side_effect = get_env_side_effect

    # --- FIX: Expect SystemExit ---
    with pytest.raises(SystemExit) as e:
        main.run()

    # assert e.value.code == 1
    mock_dependencies["sys_exit"].assert_called_once()
    captured = capsys.readouterr()
    assert f"Error: Configuration failed. {get_env_error_msg}" in captured.err
    assert "An unexpected error occurred" not in captured.err


def test_main_run_token_error(mock_dependencies, capsys):
    """Test SystemExit if getting access token fails."""
    token_error_msg = "API Token Fetch Failed"
    mock_dependencies["get_access_token"].side_effect = RuntimeError(token_error_msg)

    # --- FIX: Expect SystemExit ---
    with pytest.raises(SystemExit) as e:
        main.run()

    # assert e.value.code == 1
    # This error occurs in the *outer* try block, so sys.exit is still called once
    mock_dependencies["sys_exit"].assert_called_once()
    captured = capsys.readouterr()
    # Check the error message from the *outer* except block
    assert f"Error: Processing failed. {token_error_msg}" in captured.err
    assert "Error: Configuration failed" not in captured.err


def test_main_run_metadata_error(mock_dependencies, capsys):
    """Test SystemExit if metadata extraction fails."""
    metadata_error_msg = "Missing required field: title"
    mock_dependencies["extract_metadata"].side_effect = ValueError(metadata_error_msg)

    # --- FIX: Expect SystemExit ---
    with pytest.raises(SystemExit) as e:
        main.run()

    # assert e.value.code == 1
    mock_dependencies["sys_exit"].assert_called_once()
    captured = capsys.readouterr()
    assert f"Error: Processing failed. {metadata_error_msg}" in captured.err
    assert "Error: Configuration failed" not in captured.err


def test_main_run_thumb_upload_error(mock_dependencies, capsys):
     """Test SystemExit if thumbnail upload fails."""
     thumb_error_msg = "Thumb Upload API Error"
     mock_dependencies["upload_thumb"].side_effect = RuntimeError(thumb_error_msg)

     # --- FIX: Expect SystemExit ---
     with pytest.raises(SystemExit) as e:
         main.run()

     # assert e.value.code == 1
     mock_dependencies["sys_exit"].assert_called_once()
     captured = capsys.readouterr()
     assert f"Error: Processing failed. {thumb_error_msg}" in captured.err
     assert "Error: Configuration failed" not in captured.err


def test_main_run_html_processing_error(mock_dependencies, capsys):
     """Test SystemExit if html processing fails."""
     html_error_msg = "Content Image Upload Failed"
     mock_dependencies["process_html"].side_effect = RuntimeError(html_error_msg)

     # --- FIX: Expect SystemExit ---
     with pytest.raises(SystemExit) as e:
         main.run()

     # assert e.value.code == 1
     mock_dependencies["sys_exit"].assert_called_once()
     captured = capsys.readouterr()
     assert f"Error: Processing failed. {html_error_msg}" in captured.err
     assert "Error: Configuration failed" not in captured.err


def test_main_run_add_draft_error(mock_dependencies, capsys):
    """Test SystemExit if adding draft fails."""
    draft_error_msg = "Draft Add API Error"
    mock_dependencies["add_draft"].side_effect = RuntimeError(draft_error_msg)

    # --- FIX: Expect SystemExit ---
    with pytest.raises(SystemExit) as e:
        main.run()

    # assert e.value.code == 1
    mock_dependencies["sys_exit"].assert_called_once()
    captured = capsys.readouterr()
    assert f"Error: Processing failed. {draft_error_msg}" in captured.err
    assert "Error: Configuration failed" not in captured.err