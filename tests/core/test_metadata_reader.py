# tests/core/test_metadata_reader.py
import pytest
from pathlib import Path
import yaml # Keep for YAMLError check if needed
# Adjust import path based on your project structure
from auto_for_wechat_publishing.core.metadata_reader import extract_metadata, REQUIRED_FIELDS

# Use pytest-mock's mocker fixture and tmp_path

@pytest.fixture
def mock_read_file(mocker):
    """Fixture to mock the read_file utility function."""
    # Target read_file within the module where extract_metadata uses it
    return mocker.patch('auto_for_wechat_publishing.core.metadata_reader.read_file')

@pytest.fixture
def mock_read_file_raises_not_found(mocker):
     """Fixture to mock read_file raising FileNotFoundError."""
     return mocker.patch(
         'auto_for_wechat_publishing.core.metadata_reader.read_file',
         side_effect=FileNotFoundError("Mock File Not Found")
     )


def test_extract_metadata_success(mock_read_file, tmp_path):
    """Test extracting valid metadata including cover path validation."""
    md_filepath = tmp_path / "article.md"
    # Create dummy cover image file relative to tmp_path
    cover_file = tmp_path / "data/input/cover.jpg"
    cover_file.parent.mkdir(parents=True, exist_ok=True)
    cover_file.touch()
    # --- FIX: Use Absolute Path in mock YAML data ---
    cover_path_in_yaml = str(cover_file.resolve()) # Use the absolute path string

    mock_content = f"""---
title: My Article Title
author: Author Name
cover_image_path: "{cover_path_in_yaml}" # Use quotes for safety if path contains special chars
extra_field: Some Value
---
Article content starts here.
"""
    md_filepath.write_text(mock_content, encoding='utf-8')
    mock_read_file.return_value = mock_content

    # Let the real Path check work against the absolute path
    metadata = extract_metadata(md_filepath)

    expected_metadata = {
        "title": "My Article Title",
        "author": "Author Name",
        # The function returns the path string exactly as read from YAML
        "cover_image_path": cover_path_in_yaml,
        "extra_field": "Some Value"
    }
    assert metadata == expected_metadata
    mock_read_file.assert_called_once_with(md_filepath)


def test_extract_metadata_missing_required_field(mocker, mock_read_file, tmp_path):
    """Test extraction fails if a required field (e.g., title) is missing."""
    md_filepath = tmp_path / "missing_field.md"
    # Create the dummy cover file path used in mock_content for the check to pass
    dummy_cover_path = tmp_path / "dummy/path/exists.jpg"
    dummy_cover_path.parent.mkdir(parents=True, exist_ok=True)
    dummy_cover_path.touch()
    # --- FIX: Use Absolute Path in mock YAML data ---
    cover_path_in_yaml = str(dummy_cover_path.resolve())

    mock_content = f"""---
author: Author Name
cover_image_path: "{cover_path_in_yaml}"
---
Content.
"""
    md_filepath.write_text(mock_content, encoding='utf-8')
    mock_read_file.return_value = mock_content

    # Let the real Path check work against the absolute path
    with pytest.raises(ValueError, match="Missing or empty required metadata fields: \\['title'\\]"):
        extract_metadata(md_filepath)


def test_extract_metadata_cover_image_path_not_found(mock_read_file, tmp_path):
     """Test extraction fails if cover_image_path does not exist."""
     md_filepath = tmp_path / "cover_not_found.md"
     # This path won't exist relative to CWD or within tmp_path
     non_existent_cover = "data/input/non_existent.jpg"
     mock_content = f"""---
title: Test Title
cover_image_path: {non_existent_cover}
---
Content.
"""
     md_filepath.write_text(mock_content, encoding='utf-8')
     mock_read_file.return_value = mock_content

     # Let the real Path check fail naturally
     # The error message comes from the check within extract_metadata now
     with pytest.raises(FileNotFoundError, match=f"Cover image specified in metadata not found: {non_existent_cover}"):
          extract_metadata(md_filepath)


def test_extract_metadata_no_frontmatter(mock_read_file, tmp_path):
    """Test extraction fails with ValueError if there's no YAML frontmatter."""
    md_filepath = tmp_path / "no_frontmatter.md"
    mock_content="No frontmatter here."
    md_filepath.write_text(mock_content, encoding='utf-8')
    mock_read_file.return_value = mock_content

    with pytest.raises(ValueError, match="Missing YAML frontmatter"):
         extract_metadata(md_filepath)

def test_extract_metadata_invalid_yaml(mock_read_file, tmp_path):
    """Test extraction fails with ValueError for invalid YAML syntax."""
    md_filepath = tmp_path / "invalid_yaml.md"
    mock_content="---\ntitle: Valid Title\ninvalid yaml: here: because of colon\n---\nContent."
    md_filepath.write_text(mock_content, encoding='utf-8')
    mock_read_file.return_value = mock_content

    with pytest.raises(ValueError, match="Invalid YAML format in metadata"):
         extract_metadata(md_filepath)

def test_extract_metadata_empty_yaml_block(mock_read_file, tmp_path):
    """Test empty YAML block fails due to missing required fields."""
    md_filepath = tmp_path / "empty_yaml.md"
    mock_content="---\n---\nContent."
    md_filepath.write_text(mock_content, encoding='utf-8')
    mock_read_file.return_value = mock_content

    # Check against updated REQUIRED_FIELDS if necessary
    with pytest.raises(ValueError, match="Missing or empty required metadata fields: \\['title', 'cover_image_path'\\]"):
         extract_metadata(md_filepath)

def test_extract_metadata_yaml_not_dict(mock_read_file, tmp_path):
    """Test error if YAML is valid but not a dictionary."""
    md_filepath = tmp_path / "yaml_list.md"
    mock_content="---\n- item1\n- item2\n---\nContent."
    md_filepath.write_text(mock_content, encoding='utf-8')
    mock_read_file.return_value = mock_content

    with pytest.raises(ValueError, match="YAML frontmatter must be a dictionary"):
        extract_metadata(md_filepath)


# This test now uses a dedicated fixture for clarity
def test_extract_metadata_file_not_found(mock_read_file_raises_not_found, tmp_path):
    """Test FileNotFoundError if the markdown file itself does not exist."""
    md_filepath = tmp_path / "non_existent.md"
    # The fixture mock_read_file_raises_not_found handles the side effect
    with pytest.raises(FileNotFoundError, match="Mock File Not Found"): # Match fixture's error
        extract_metadata(md_filepath)
    # Check the mock (from the fixture) was called
    mock_read_file_raises_not_found.assert_called_once_with(md_filepath)