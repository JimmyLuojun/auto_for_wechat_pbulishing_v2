# tests/wechat/test_api.py
import pytest
import requests
import stat # Import the stat module for file mode constants
from pathlib import Path
from unittest.mock import MagicMock, mock_open
# Adjust import path based on your project structure
from auto_for_wechat_publishing.wechat.api import (
    upload_content_image,
    upload_thumb_media,
    add_draft,
    _check_response, # Can test helper directly if needed
)

# --- Fixtures ---
@pytest.fixture
def mock_requests_post(mocker):
    """Fixture to mock requests.post."""
    mock = mocker.patch('requests.post')
    mock.return_value = MagicMock(spec=requests.Response)
    # Default successful response setup
    mock.return_value.raise_for_status = MagicMock()
    mock.return_value.json.return_value = {"errcode": 0, "errmsg": "ok"}
    mock.return_value.request = MagicMock()
    mock.return_value.request.url = "http://mock.url"
    return mock

@pytest.fixture
def mock_open_file(mocker):
     """Fixture to mock open()."""
     # Make sure mock_open has necessary methods if needed, like __iter__
     m = mock_open(read_data=b'file_content')
     # Add __iter__ manually if needed for context manager usage in some libs
     # m.return_value.__iter__ = lambda self: iter(self.readline, '')
     return mocker.patch('builtins.open', m)


@pytest.fixture
def dummy_file(tmp_path):
     """Create a dummy file for testing uploads."""
     f = tmp_path / "dummy.jpg"
     f.write_bytes(b'-dummy-content-') # Add some content
     return f

@pytest.fixture
def mock_path_stat(mocker):
    """Fixture factory to mock pathlib.Path.stat with specific size/mode."""
    def _mock_stat(file_size: int):
        mock_stat_result = MagicMock()
        # Simulate a regular file
        mock_stat_result.st_mode = stat.S_IFREG
        mock_stat_result.st_size = file_size
        return mocker.patch('pathlib.Path.stat', return_value=mock_stat_result)
    return _mock_stat

# --- Tests for _check_response (Keep as before) ---

def test_check_response_success():
     mock_response = MagicMock(spec=requests.Response)
     mock_response.raise_for_status = MagicMock()
     expected_data = {"errcode": 0, "errmsg": "ok", "extra": "data"}
     mock_response.json.return_value = expected_data
     assert _check_response(mock_response) == expected_data
     mock_response.raise_for_status.assert_called_once()
     mock_response.json.assert_called_once()

def test_check_response_http_error():
    mock_response = MagicMock(spec=requests.Response)
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Error")
    mock_response.request = MagicMock()
    mock_response.request.url = "http://test.url/fail"
    with pytest.raises(RuntimeError, match="Network error during API call"):
        _check_response(mock_response)

def test_check_response_wechat_error():
    mock_response = MagicMock(spec=requests.Response)
    mock_response.raise_for_status = MagicMock()
    error_data = {"errcode": 40002, "errmsg": "invalid grant_type"}
    mock_response.json.return_value = error_data
    mock_response.request = MagicMock()
    mock_response.request.url = "http://test.url/apierror"
    with pytest.raises(RuntimeError, match="WeChat API error.*40002 - invalid grant_type"):
        _check_response(mock_response)

def test_check_response_invalid_json():
     mock_response = MagicMock(spec=requests.Response)
     mock_response.raise_for_status = MagicMock()
     mock_response.json.side_effect = ValueError("JSON decode error")
     mock_response.text = "invalid json text"
     mock_response.request = MagicMock()
     mock_response.request.url = "http://test.url/badjson"
     with pytest.raises(RuntimeError, match="Invalid response.*invalid json text"):
          _check_response(mock_response)


# --- Tests for upload_content_image ---

def test_upload_content_image_success(mock_requests_post, mock_open_file, dummy_file, mock_path_stat):
    """Test successful upload of a content image."""
    access_token = "ACCESS_TOKEN"
    base_url = "https://api.test.com"
    expected_url = "http://mmbiz.qpic.cn/mmbiz/..."
    image_path = dummy_file.with_suffix(".png") # Ensure valid suffix
    image_path.touch() # Create the file with the new suffix

    # --- Use Fixture Factory for stat mock ---
    mock_stat = mock_path_stat(file_size=500 * 1024) # 500KB

    mock_response = mock_requests_post.return_value
    mock_response.json.return_value = {"errcode": 0, "errmsg": "ok", "url": expected_url}

    result_url = upload_content_image(access_token, image_path, base_url)

    assert result_url == expected_url
    expected_api_url = f"{base_url}/cgi-bin/media/uploadimg"
    mock_requests_post.assert_called_once()
    call_args, call_kwargs = mock_requests_post.call_args
    assert call_args[0] == expected_api_url
    assert call_kwargs.get("params") == {"access_token": access_token}
    assert "files" in call_kwargs
    mock_open_file.assert_called_with(image_path, 'rb')
    # Verify stat was called (by is_file and size check)
    assert mock_stat.call_count > 0


def test_upload_content_image_file_not_found(tmp_path):
    """Test FileNotFoundError if image doesn't exist."""
    non_existent_file = tmp_path / "not_found.png"
    with pytest.raises(FileNotFoundError, match="Content image not found"):
        upload_content_image("token", non_existent_file)


def test_upload_content_image_invalid_type(dummy_file):
    """Test ValueError for invalid file type."""
    invalid_path = dummy_file.with_suffix(".gif") # Change to invalid suffix
    # --- ADDED FILE CREATION ---
    invalid_path.touch() # Make sure the .gif file exists for is_file() check

    with pytest.raises(ValueError, match="Invalid content image type"):
        upload_content_image("token", invalid_path)


def test_upload_content_image_too_large(dummy_file, mock_path_stat):
    """Test ValueError for image size > 1MB."""
    image_path = dummy_file.with_suffix(".jpg")
    image_path.touch()
    # --- Use Fixture Factory for stat mock ---
    mock_stat = mock_path_stat(file_size=2 * 1024 * 1024) # 2MB

    with pytest.raises(ValueError, match="exceeds 1MB limit"):
        upload_content_image("token", image_path)
    # Verify stat was called
    assert mock_stat.call_count > 0


def test_upload_content_image_api_error(mock_requests_post, mock_open_file, dummy_file, mock_path_stat):
     """Test handling of WeChat API error during content image upload."""
     image_path = dummy_file.with_suffix(".png")
     image_path.touch()
     # --- Use Fixture Factory for stat mock ---
     mock_stat = mock_path_stat(file_size=100) # Small size

     mock_response = mock_requests_post.return_value
     mock_response.json.return_value = {"errcode": 41005, "errmsg": "media data missing"}
     mock_response.raise_for_status = MagicMock()

     with pytest.raises(RuntimeError, match="WeChat API error.*41005"):
          upload_content_image("token", image_path)
     assert mock_stat.call_count > 0


# --- Tests for upload_thumb_media ---

def test_upload_thumb_media_success(mock_requests_post, mock_open_file, dummy_file, mock_path_stat):
    """Test successful upload of a thumbnail."""
    access_token = "ACCESS_TOKEN_THUMB"
    base_url = "https://api.test.com"
    expected_media_id = "THUMB_MEDIA_ID_123"
    thumb_path = dummy_file.with_suffix(".jpg") # Ensure valid suffix
    thumb_path.touch()

    # --- Use Fixture Factory for stat mock ---
    mock_stat = mock_path_stat(file_size=50 * 1024) # 50KB

    mock_response = mock_requests_post.return_value
    mock_response.json.return_value = {"errcode": 0, "errmsg": "ok", "media_id": expected_media_id}

    result_id = upload_thumb_media(access_token, thumb_path, base_url)

    assert result_id == expected_media_id
    expected_api_url = f"{base_url}/cgi-bin/material/add_material"
    mock_requests_post.assert_called_once()
    call_args, call_kwargs = mock_requests_post.call_args
    assert call_args[0] == expected_api_url
    assert call_kwargs.get("params") == {"access_token": access_token, "type": "thumb"}
    assert "files" in call_kwargs
    mock_open_file.assert_called_with(thumb_path, 'rb')
    assert mock_stat.call_count > 0


def test_upload_thumb_media_invalid_type(dummy_file):
    """Test ValueError for non-JPG thumbnail type."""
    invalid_path = dummy_file.with_suffix(".png") # PNG is invalid for thumb
    # --- ADDED FILE CREATION ---
    invalid_path.touch() # Ensure file exists for is_file() check

    with pytest.raises(ValueError, match="Invalid thumbnail image type"):
        upload_thumb_media("token", invalid_path)


def test_upload_thumb_media_too_large(dummy_file, mock_path_stat):
    """Test ValueError for thumbnail size > 64KB."""
    thumb_path = dummy_file.with_suffix(".jpg")
    thumb_path.touch()
    # --- Use Fixture Factory for stat mock ---
    mock_stat = mock_path_stat(file_size=70 * 1024) # 70KB

    with pytest.raises(ValueError, match="exceeds 64KB limit"):
        upload_thumb_media("token", thumb_path)
    assert mock_stat.call_count > 0

# Add tests for FileNotFoundError and API errors similar to content image tests
def test_upload_thumb_media_file_not_found(tmp_path):
    """Test FileNotFoundError if thumb image doesn't exist."""
    non_existent_file = tmp_path / "not_found.jpg"
    with pytest.raises(FileNotFoundError, match="Thumbnail image not found"):
        upload_thumb_media("token", non_existent_file)

def test_upload_thumb_media_api_error(mock_requests_post, mock_open_file, dummy_file, mock_path_stat):
     """Test handling of WeChat API error during thumb upload."""
     thumb_path = dummy_file.with_suffix(".jpg")
     thumb_path.touch()
     mock_stat = mock_path_stat(file_size=10 * 1024) # 10KB

     mock_response = mock_requests_post.return_value
     mock_response.json.return_value = {"errcode": 40007, "errmsg": "invalid media_id"}
     mock_response.raise_for_status = MagicMock()

     with pytest.raises(RuntimeError, match="WeChat API error.*40007"):
          upload_thumb_media("token", thumb_path)
     assert mock_stat.call_count > 0


# --- Tests for add_draft (Keep as before) ---

def test_add_draft_success(mock_requests_post):
    access_token = "ACCESS_TOKEN_DRAFT"
    base_url = "https://api.test.com"
    draft_payload = {"articles": [{"title": "Test", "content": "..."}]}
    expected_media_id = "DRAFT_MEDIA_ID_789"
    mock_response = mock_requests_post.return_value
    mock_response.json.return_value = {"errcode": 0, "errmsg": "ok", "media_id": expected_media_id}
    result_id = add_draft(access_token, draft_payload, base_url)
    assert result_id == expected_media_id
    expected_api_url = f"{base_url}/cgi-bin/draft/add"
    mock_requests_post.assert_called_once_with(
        expected_api_url,
        params={"access_token": access_token},
        json=draft_payload,
        timeout=30
    )

def test_add_draft_invalid_payload():
    with pytest.raises(ValueError, match="Draft payload must contain an 'articles' list"):
        add_draft("token", {"title": "Wrong structure"})
    with pytest.raises(ValueError, match="Draft payload must contain an 'articles' list"):
         add_draft("token", {"articles": "not_a_list"})

def test_add_draft_api_error(mock_requests_post):
     draft_payload = {"articles": [{"title": "Test", "content": "..."}]}
     mock_response = mock_requests_post.return_value
     mock_response.json.return_value = {"errcode": 40018, "errmsg": "invalid button name size"}
     mock_response.raise_for_status = MagicMock()
     with pytest.raises(RuntimeError, match="WeChat API error.*40018"):
          add_draft("token", draft_payload)