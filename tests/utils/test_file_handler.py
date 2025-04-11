# tests/utils/test_file_handler.py
import pytest
from pathlib import Path
from auto_for_wechat_publishing.utils.file_handler import read_file, write_file

# --- Tests for read_file ---

def test_read_file_success(tmp_path):
    """Test reading an existing file."""
    test_file = tmp_path / "read_test.txt"
    expected_content = "Hello, world!\nLine two."
    test_file.write_text(expected_content, encoding='utf-8')
    content = read_file(test_file) # Pass Path object
    assert content == expected_content

def test_read_file_not_found(tmp_path):
    """Test reading a non-existent file raises FileNotFoundError."""
    non_existent_file = tmp_path / "not_here.txt"
    with pytest.raises(FileNotFoundError, match=f"File not found: {non_existent_file}"):
        read_file(non_existent_file)

def test_read_file_handles_read_error(tmp_path, mocker):
    """Test that read errors are wrapped in RuntimeError."""
    test_file = tmp_path / "read_error.txt"
    test_file.touch() # Create file

    # Mock Path.read_text to raise an arbitrary error
    mock_read_text = mocker.patch("pathlib.Path.read_text", side_effect=OSError("Disk read error"))

    with pytest.raises(RuntimeError, match="Failed to read file"):
        read_file(test_file)
    mock_read_text.assert_called_once()

# --- Tests for write_file ---

def test_write_file_success(tmp_path):
    """Test writing content to a new file creates it and parents."""
    output_dir = tmp_path / "output"
    test_file = output_dir / "subdir" / "write_test.txt"
    content_to_write = "Content to be written.\nLine two."

    assert not test_file.exists()
    assert not output_dir.exists()

    write_file(test_file, content_to_write) # Pass Path object

    assert test_file.exists()
    assert test_file.read_text(encoding='utf-8') == content_to_write
    assert output_dir.is_dir()
    assert (output_dir / "subdir").is_dir()

def test_write_file_overwrite(tmp_path):
    """Test overwriting an existing file."""
    test_file = tmp_path / "overwrite_test.txt"
    initial_content = "Initial content."
    new_content = "New overwritten content."
    test_file.write_text(initial_content) # Create with initial content

    write_file(test_file, new_content)

    assert test_file.read_text(encoding='utf-8') == new_content

def test_write_file_handles_write_error(tmp_path, mocker):
    """Test that write errors are wrapped in RuntimeError."""
    test_file = tmp_path / "write_error.txt"
    # Mock Path.write_text to raise an error
    mock_write_text = mocker.patch("pathlib.Path.write_text", side_effect=OSError("Disk write error"))
    # Mock parent creation just in case (though it might not be reached)
    mocker.patch("pathlib.Path.mkdir")

    with pytest.raises(RuntimeError, match="Failed to write to file"):
        write_file(test_file, "content")
    mock_write_text.assert_called_once() 