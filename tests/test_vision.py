import pytest
from unittest.mock import patch, mock_open, MagicMock
from core.vision import describe_screen

def test_describe_screen_error_path_file_not_found():
    """Test that describe_screen handles file not found errors correctly."""
    result = describe_screen("non_existent_file.png", "What is this?")
    assert result == "I could not verify the screen visually, sir."

@patch('core.vision.httpx.post')
def test_describe_screen_error_path_network_error(mock_post):
    """Test that describe_screen handles network errors from httpx correctly."""
    # Mock file reading so it doesn't fail on open
    with patch("builtins.open", mock_open(read_data=b"fake_image_data")):
        mock_post.side_effect = Exception("Network Error")
        result = describe_screen("dummy_path.png", "What is this?")
        assert result == "I could not verify the screen visually, sir."

@patch('core.vision.httpx.post')
def test_describe_screen_error_path_http_error(mock_post):
    """Test that describe_screen handles HTTP errors from httpx.post correctly."""
    # Mock file reading so it doesn't fail on open
    with patch("builtins.open", mock_open(read_data=b"fake_image_data")):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        mock_post.return_value = mock_response

        result = describe_screen("dummy_path.png", "What is this?")
        assert result == "I could not verify the screen visually, sir."
