import sys
import json
import pytest
from unittest.mock import MagicMock, patch

# Mock modules to run on linux without actual tools
win32gui_mock = MagicMock()
sys.modules['win32gui'] = win32gui_mock

pyautogui_mock = MagicMock()
sys.modules['pyautogui'] = pyautogui_mock

pil_mock = MagicMock()
sys.modules['PIL'] = pil_mock

pyperclip_mock = MagicMock()
sys.modules['pyperclip'] = pyperclip_mock

from tools.weather import get_weather

def test_get_weather_success_similar_feels_like():
    mock_data = {
        'current_condition': [{
            'temp_C': '25',
            'FeelsLikeC': '26',
            'weatherDesc': [{'value': 'Sunny'}],
            'humidity': '50'
        }]
    }
    mock_json = json.dumps(mock_data).encode('utf-8')

    mock_resp = MagicMock()
    mock_resp.read.return_value = mock_json
    mock_resp.__enter__.return_value = mock_resp

    with patch('urllib.request.urlopen', return_value=mock_resp):
        result = get_weather("London")

    assert "It is currently 25°C and sunny in London, sir." in result
    assert "Humidity is at 50%." in result
    assert "However, it feels more like" not in result

def test_get_weather_success_diff_feels_like():
    mock_data = {
        'current_condition': [{
            'temp_C': '10',
            'FeelsLikeC': '5',
            'weatherDesc': [{'value': 'Partly Cloudy'}],
            'humidity': '70'
        }]
    }
    mock_json = json.dumps(mock_data).encode('utf-8')

    mock_resp = MagicMock()
    mock_resp.read.return_value = mock_json
    mock_resp.__enter__.return_value = mock_resp

    with patch('urllib.request.urlopen', return_value=mock_resp):
        result = get_weather("New York")

    assert "It is currently 10°C and partly cloudy in New York, sir." in result
    assert "However, it feels more like 5°C." in result
    assert "Humidity is at 70%." in result

def test_get_weather_default_location():
    mock_data = {
        'current_condition': [{
            'temp_C': '30',
            'FeelsLikeC': '35',
            'weatherDesc': [{'value': 'Clear'}],
            'humidity': '80'
        }]
    }
    mock_json = json.dumps(mock_data).encode('utf-8')

    mock_resp = MagicMock()
    mock_resp.read.return_value = mock_json
    mock_resp.__enter__.return_value = mock_resp

    with patch('urllib.request.urlopen', return_value=mock_resp):
        result = get_weather()

    assert "in Palakkad, sir" in result
    assert "feels more like 35°C" in result

def test_get_weather_network_exception():
    with patch('urllib.request.urlopen', side_effect=Exception("Network down")):
        result = get_weather("Tokyo")

    assert result == "I am unable to reach the meteorological satellites for Tokyo at this time, sir."
