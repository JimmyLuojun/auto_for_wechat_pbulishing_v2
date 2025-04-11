# tests/wechat/test_auth.py
import pytest
import requests
import time
from unittest.mock import MagicMock
from auto_for_wechat_publishing.wechat.auth import get_access_token, _token_cache # Import cache for reset

# Fixture to reset cache before each test
@pytest.fixture(autouse=True)
def reset_token_cache():
    _token_cache["access_token"] = None
    _token_cache["expires_at"] = 0
    yield # Run the test
    _token_cache["access_token"] = None
    _token_cache["expires_at"] = 0


@pytest.fixture
def mock_requests_get(mocker):
    """Fixture to mock requests.get."""
    mock = mocker.patch('requests.get')
    mock.return_value = MagicMock(spec=requests.Response)
    return mock

def test_get_access_token_success(mock_requests_get, mocker):
    """Test successful fetching of a new token."""
    app_id = "test_id"
    app_secret = "test_secret"
    base_url = "https://api.test.com"
    expected_token = "TOKEN_12345"
    expires_in = 7200
    mock_response = mock_requests_get.return_value
    mock_response.json.return_value = {
        "access_token": expected_token,
        "expires_in": expires_in
        # Implicitly errcode=0, errmsg="ok"
    }
    mock_response.raise_for_status = MagicMock() # Mock OK status

    # Mock time.time() for cache setting verification
    current_time = time.time()
    mocker.patch('time.time', return_value=current_time)

    token = get_access_token(app_id, app_secret, base_url)

    assert token == expected_token
    mock_requests_get.assert_called_once_with(
        f"{base_url}/cgi-bin/token",
        params={
            "grant_type": "client_credential",
            "appid": app_id,
            "secret": app_secret,
        },
        timeout=10
    )
    mock_response.raise_for_status.assert_called_once()
    mock_response.json.assert_called_once()

    # Verify cache state
    assert _token_cache["access_token"] == expected_token
    assert _token_cache["expires_at"] == current_time + expires_in


def test_get_access_token_uses_cache(mock_requests_get, mocker):
    """Test that a valid cached token is returned without API call."""
    cached_token = "CACHED_TOKEN"
    future_expiry = time.time() + 5000 # Expires far in the future
    _token_cache["access_token"] = cached_token
    _token_cache["expires_at"] = future_expiry

    token = get_access_token("id", "secret", "url")

    assert token == cached_token
    mock_requests_get.assert_not_called() # API should not be called


def test_get_access_token_refreshes_expired_cache(mock_requests_get, mocker):
    """Test that an expired token triggers a new API call."""
    expired_time = time.time() - 100 # Expired in the past
    _token_cache["access_token"] = "EXPIRED_TOKEN"
    _token_cache["expires_at"] = expired_time

    # Setup mock response for the new call
    new_token = "NEW_FRESH_TOKEN"
    mock_response = mock_requests_get.return_value
    mock_response.json.return_value = {"access_token": new_token, "expires_in": 7200}
    mock_response.raise_for_status = MagicMock()

    current_time = time.time()
    mocker.patch('time.time', return_value=current_time)

    token = get_access_token("id", "secret", "url")

    assert token == new_token
    mock_requests_get.assert_called_once() # API *should* be called
    assert _token_cache["access_token"] == new_token
    assert _token_cache["expires_at"] > current_time # New expiry time


def test_get_access_token_refreshes_near_expiry_cache(mock_requests_get, mocker):
    """Test that a token nearing expiry (within buffer) triggers refresh."""
    near_expiry_time = time.time() + 100 # Expires soon, within 300s buffer
    _token_cache["access_token"] = "NEAR_EXPIRY_TOKEN"
    _token_cache["expires_at"] = near_expiry_time

    # Setup mock response for the new call
    new_token = "NEW_BUFFER_TOKEN"
    mock_response = mock_requests_get.return_value
    mock_response.json.return_value = {"access_token": new_token, "expires_in": 7200}
    mock_response.raise_for_status = MagicMock()

    current_time = time.time()
    mocker.patch('time.time', return_value=current_time)

    token = get_access_token("id", "secret", "url")

    assert token == new_token
    mock_requests_get.assert_called_once() # API *should* be called
    assert _token_cache["access_token"] == new_token


def test_get_access_token_missing_credentials():
    """Test ValueError if app_id or app_secret is missing."""
    with pytest.raises(ValueError, match="App ID and App Secret must be provided"):
        get_access_token("", "secret", "url")
    with pytest.raises(ValueError, match="App ID and App Secret must be provided"):
        get_access_token("id", "", "url")


def test_get_access_token_network_error(mock_requests_get):
    """Test RuntimeError on requests.exceptions.RequestException."""
    mock_requests_get.side_effect = requests.exceptions.ConnectionError("Network unreachable")

    with pytest.raises(RuntimeError, match="Network error fetching access token"):
        get_access_token("id", "secret", "url")


def test_get_access_token_http_error(mock_requests_get):
    """Test RuntimeError on HTTP error status."""
    mock_response = mock_requests_get.return_value
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Client Error")

    with pytest.raises(RuntimeError, match="Network error fetching access token"): # raise_for_status triggers RequestException path
        get_access_token("id", "secret", "url")


def test_get_access_token_timeout_error(mock_requests_get):
    """Test RuntimeError on requests.exceptions.Timeout."""
    mock_requests_get.side_effect = requests.exceptions.Timeout("Request timed out")

    with pytest.raises(RuntimeError, match="Request timed out"):
        get_access_token("id", "secret", "url")


def test_get_access_token_invalid_json(mock_requests_get):
    """Test RuntimeError if response is not valid JSON."""
    mock_response = mock_requests_get.return_value
    mock_response.raise_for_status = MagicMock()
    mock_response.json.side_effect = ValueError("Decoding JSON failed") # Simulate json() error
    mock_response.text = "This is not JSON"

    with pytest.raises(RuntimeError, match="Invalid response from token API: This is not JSON"):
        get_access_token("id", "secret", "url")


def test_get_access_token_wechat_api_error(mock_requests_get):
    """Test RuntimeError on WeChat API error (errcode != 0)."""
    mock_response = mock_requests_get.return_value
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "errcode": 40001,
        "errmsg": "invalid credential"
    }

    with pytest.raises(RuntimeError, match="WeChat API error fetching token: 40001 - invalid credential"):
        get_access_token("id", "secret", "url")


def test_get_access_token_missing_keys_in_response(mock_requests_get):
    """Test RuntimeError if expected keys are missing in success response."""
    mock_response = mock_requests_get.return_value
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"expires_in": 7200} # Missing access_token

    with pytest.raises(RuntimeError, match="Unexpected response format from token API"):
        get_access_token("id", "secret", "url")

    mock_response.json.return_value = {"access_token": "TOKEN"} # Missing expires_in
    with pytest.raises(RuntimeError, match="Unexpected response format from token API"):
        get_access_token("id", "secret", "url") 