# tests/core/test_html_processor.py
import pytest
from pathlib import Path
from unittest.mock import MagicMock, call
from bs4 import BeautifulSoup # Using BeautifulSoup for parsing AND asserting
# Adjust import path if necessary
from auto_for_wechat_publishing.core.html_processor import process_html_content

# Define dummy uploader for tests that can be easily mocked
def dummy_image_uploader(image_path: Path) -> str:
    """Dummy uploader for testing."""
    return f"http://wechat.example.com/uploaded/{image_path.name}"

@pytest.fixture
def mock_read_css(mocker):
     """Fixture to mock reading the CSS file."""
     # Target 'read_file' within the module where process_html_content uses it
     return mocker.patch(
        'auto_for_wechat_publishing.core.html_processor.read_file',
        return_value="p { color: green; }" # Default mock CSS
    )

@pytest.fixture
def setup_files(tmp_path):
    """Fixture to create dummy CSS and image files for tests."""
    css_path = tmp_path / "styles/style.css"
    css_path.parent.mkdir()
    css_path.write_text("h1 { color: red; }")

    md_dir = tmp_path / "articles"
    md_dir.mkdir()
    md_path = md_dir / "article.md"

    img_dir = md_dir / "images" # Relative to markdown file
    img_dir.mkdir()
    content_image_path = img_dir / "test_image.png"
    content_image_path.touch()

    abs_img_path = tmp_path / "absolute_image.jpg" # Absolute path image
    abs_img_path.touch()


    return {
        "css_path": css_path,
        "md_path": md_path,
        "md_dir": md_dir,
        "content_image_path": content_image_path, # The actual file Path obj
        "content_image_relative_src": "images/test_image.png", # How it's referenced in MD
        "abs_img_path": abs_img_path,
        "abs_image_src": str(abs_img_path) # How it's referenced in MD
    }

# --- Test Functions ---

def test_process_html_no_images(mocker, setup_files, mock_read_css):
     """Test basic MD conversion and CSS injection without images."""
     md_content = "# Title\n\nParagraph."
     expected_md_output_fragment = "<h1>Title</h1>\n<p>Paragraph.</p>"
     css_content = "h1 { color: red; }"
     mock_read_css.return_value = css_content
     expected_output = f"<style>\n{css_content}\n</style>\n<html><body>{expected_md_output_fragment}</body></html>"

     mock_uploader = mocker.Mock(wraps=dummy_image_uploader)

     result = process_html_content(
         md_content=md_content,
         css_path=setup_files["css_path"],
         markdown_file_path=setup_files["md_path"],
         image_uploader=mock_uploader
     )

     assert result == expected_output
     mock_uploader.assert_not_called()
     # CSS read *should* happen in the success path
     mock_read_css.assert_called_once_with(setup_files["css_path"])


def test_process_html_with_relative_local_image(mocker, setup_files, mock_read_css):
    """Test finding, uploading, and replacing a relative local image."""
    md_content = f"![Alt text]({setup_files['content_image_relative_src']})"
    css_content = "h1 { color: red; }"
    mock_read_css.return_value = css_content
    expected_wechat_url = f"http://wechat.example.com/uploaded/{setup_files['content_image_path'].name}"

    mock_uploader = mocker.Mock(return_value=expected_wechat_url)

    result = process_html_content(
         md_content=md_content,
         css_path=setup_files["css_path"],
         markdown_file_path=setup_files["md_path"],
         image_uploader=mock_uploader
    )

    mock_uploader.assert_called_once_with(setup_files['content_image_path'].resolve())
    # CSS read *should* happen in the success path
    mock_read_css.assert_called_once_with(setup_files["css_path"])

    soup = BeautifulSoup(result, 'lxml')
    img_tag = soup.find('img')
    assert img_tag is not None, "<img> tag not found in processed HTML"
    assert img_tag.get('src') == expected_wechat_url
    assert img_tag.get('alt') == "Alt text"
    assert setup_files['content_image_relative_src'] not in result
    assert f"<style>\n{css_content}\n</style>" in result


def test_process_html_with_absolute_local_image(mocker, setup_files, mock_read_css):
    """Test finding, uploading, and replacing an absolute local image."""
    md_content = f"![Abs Image]({setup_files['abs_image_src']})"
    css_content = "h1 { color: red; }"
    mock_read_css.return_value = css_content
    expected_wechat_url = f"http://wechat.example.com/uploaded/{setup_files['abs_img_path'].name}"

    mock_uploader = mocker.Mock(return_value=expected_wechat_url)

    result = process_html_content(
         md_content=md_content,
         css_path=setup_files["css_path"],
         markdown_file_path=setup_files["md_path"],
         image_uploader=mock_uploader
    )

    mock_uploader.assert_called_once_with(setup_files['abs_img_path'].resolve())
    # CSS read *should* happen in the success path
    mock_read_css.assert_called_once_with(setup_files["css_path"])

    soup = BeautifulSoup(result, 'lxml')
    img_tag = soup.find('img')
    assert img_tag is not None, "<img> tag not found in processed HTML"
    assert img_tag.get('src') == expected_wechat_url
    assert img_tag.get('alt') == "Abs Image"


def test_process_html_ignores_web_images(mocker, setup_files, mock_read_css):
    """Test that http/https URLs are not processed."""
    web_url = "https://example.com/image.png"
    md_content = f"![Web Image]({web_url})"
    css_content = "h1 { color: red; }"
    mock_read_css.return_value = css_content
    mock_uploader = mocker.Mock(wraps=dummy_image_uploader)

    result = process_html_content(
         md_content=md_content,
         css_path=setup_files["css_path"],
         markdown_file_path=setup_files["md_path"],
         image_uploader=mock_uploader
    )

    mock_uploader.assert_not_called()
    # CSS read *should* happen in the success path
    mock_read_css.assert_called_once_with(setup_files["css_path"])

    soup = BeautifulSoup(result, 'lxml')
    img_tag = soup.find('img')
    assert img_tag is not None, "<img> tag not found in processed HTML"
    assert img_tag.get('src') == web_url


def test_process_html_image_upload_fails(mocker, setup_files, mock_read_css):
    """Test that errors during image upload are propagated."""
    md_content = f"![Alt]({setup_files['content_image_relative_src']})"
    # Don't strictly need to mock CSS return value here, as it won't be read
    # mock_read_css.return_value = "h1 { color: red; }"
    mock_uploader = mocker.Mock(side_effect=RuntimeError("API upload failed"))

    with pytest.raises(RuntimeError, match="API upload failed"):
         process_html_content(
             md_content=md_content,
             css_path=setup_files["css_path"],
             markdown_file_path=setup_files["md_path"],
             image_uploader=mock_uploader
         )
    # Check uploader was called
    mock_uploader.assert_called_once_with(setup_files['content_image_path'].resolve())
    # --- REMOVED ASSERTION ---
    # CSS read should NOT have happened because the error occurred before it
    # mock_read_css.assert_called_once_with(setup_files["css_path"]) # REMOVED


def test_process_html_local_image_not_found(mocker, setup_files, mock_read_css):
    """Test FileNotFoundError if a local image reference is broken."""
    broken_relative_src = "images/not_really_here.png"
    md_content = f"![Broken]({broken_relative_src})"
    # Don't strictly need to mock CSS return value here
    # mock_read_css.return_value = "h1 { color: red; }"
    mock_uploader = mocker.Mock()

    expected_missing_path = (setup_files['md_dir'] / broken_relative_src).resolve()
    match_string = f"Image referenced in markdown not found: {expected_missing_path}"

    with pytest.raises(FileNotFoundError, match=match_string):
         process_html_content(
             md_content=md_content,
             css_path=setup_files["css_path"],
             markdown_file_path=setup_files["md_path"],
             image_uploader=mock_uploader
         )
    # Check uploader wasn't called
    mock_uploader.assert_not_called()
    # --- REMOVED ASSERTION ---
    # CSS read should NOT have happened because the error occurred before it
    # mock_read_css.assert_called_once_with(setup_files["css_path"]) # REMOVED


def test_process_html_css_not_found(mocker, setup_files):
    """Test FileNotFoundError if the CSS file doesn't exist."""
    md_content = "# Title"
    non_existent_css = setup_files["css_path"].parent / "wrong.css"
    mock_uploader = mocker.Mock()

    # Target 'read_file' within the html_processor module
    mock_read = mocker.patch(
        'auto_for_wechat_publishing.core.html_processor.read_file',
        side_effect=FileNotFoundError(f"File not found: {non_existent_css}")
    )

    with pytest.raises(FileNotFoundError, match=f"File not found: {non_existent_css}"):
        process_html_content(
            md_content=md_content,
            css_path=non_existent_css,
            markdown_file_path=setup_files["md_path"],
            image_uploader=mock_uploader
        )
    # Verify that the attempt to read the CSS file was made
    mock_read.assert_called_once_with(non_existent_css)
    mock_uploader.assert_not_called()