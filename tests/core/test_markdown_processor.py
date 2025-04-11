# tests/core/test_markdown_processor.py
"""Tests for the markdown content extraction."""

import pytest
from pathlib import Path
# Adjust import path based on your project structure and how tests are run
from auto_for_wechat_publishing.core.markdown_processor import extract_markdown_content

@pytest.fixture
def mock_read_file(mocker):
    """Fixture to mock the read_file utility function."""
    # Target read_file as imported within the markdown_processor module
    return mocker.patch('auto_for_wechat_publishing.core.markdown_processor.read_file')


def test_extract_content_with_frontmatter(mock_read_file, tmp_path):
    """Test extracting content when valid frontmatter exists."""
    md_filepath = tmp_path / "article.md"
    mock_full_content = """---
title: Test Title
author: Tester
---
# Header

This is the content.
It has multiple lines.
"""
    # Expected result is only the content AFTER the second '---'
    expected_markdown = "# Header\n\nThis is the content.\nIt has multiple lines."
    mock_read_file.return_value = mock_full_content

    content = extract_markdown_content(md_filepath)
    # The function strips the result, ensure comparison accounts for this if needed
    assert content == expected_markdown.strip()
    mock_read_file.assert_called_once_with(md_filepath)


def test_extract_content_without_frontmatter(mock_read_file, tmp_path):
    """Test extracting content when no frontmatter exists."""
    md_filepath = tmp_path / "plain.md"
    mock_full_content = "# Header\n\nJust content.\nNo frontmatter here."
    # Expected result is the entire content, stripped
    expected_markdown = mock_full_content.strip()
    mock_read_file.return_value = mock_full_content

    content = extract_markdown_content(md_filepath)
    assert content == expected_markdown
    mock_read_file.assert_called_once_with(md_filepath)


def test_extract_content_only_frontmatter(mock_read_file, tmp_path):
    """Test extracting content when only frontmatter exists."""
    md_filepath = tmp_path / "only_fm.md"
    mock_full_content = "---\ntitle: Test Title\nauthor: Test\n---"
    # Expect empty string when only frontmatter is present
    expected_markdown = ""
    mock_read_file.return_value = mock_full_content

    content = extract_markdown_content(md_filepath)
    assert content == expected_markdown
    mock_read_file.assert_called_once_with(md_filepath)


def test_extract_content_malformed_frontmatter(mock_read_file, tmp_path):
     """Test extracting content when frontmatter delimiter is wrong."""
     md_filepath = tmp_path / "malformed.md"
     # Starts with --- but doesn't have closing --- properly separated
     mock_full_content = "---\ntitle: Test Title\nActual content here\n"
     # Current logic treats this as content because split doesn't yield 3 parts
     expected_markdown = mock_full_content.strip()
     mock_read_file.return_value = mock_full_content

     content = extract_markdown_content(md_filepath)
     assert content == expected_markdown
     mock_read_file.assert_called_once_with(md_filepath)


def test_extract_content_empty_file(mock_read_file, tmp_path):
    """Test extracting content from an empty file."""
    md_filepath = tmp_path / "empty.md"
    mock_full_content = ""
    expected_markdown = ""
    mock_read_file.return_value = mock_full_content

    content = extract_markdown_content(md_filepath)
    assert content == expected_markdown
    mock_read_file.assert_called_once_with(md_filepath)


def test_extract_content_file_not_found(mocker, tmp_path):
    """Test FileNotFoundError if the markdown file itself does not exist."""
    md_filepath = tmp_path / "non_existent.md"
    # Mock read_file within the markdown_processor module's scope
    mock_read = mocker.patch(
        'auto_for_wechat_publishing.core.markdown_processor.read_file',
        side_effect=FileNotFoundError(f"File not found: {md_filepath}")
    )
    with pytest.raises(FileNotFoundError):
        extract_markdown_content(md_filepath)
    mock_read.assert_called_once_with(md_filepath)