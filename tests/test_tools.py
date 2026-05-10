import sys
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

from core.tools import SparkTools

@pytest.fixture
def tools():
    return SparkTools()

def test_type_text_blacklisted_window(tools):
    with patch('win32gui.GetForegroundWindow', return_value=1234), \
         patch('win32gui.GetWindowText', return_value="Command Prompt"):
        result = tools.type_text("some test")
        assert "Security override: Refusing to type" in result

def test_type_text_safe_window(tools):
    with patch('win32gui.GetForegroundWindow', return_value=5678), \
         patch('win32gui.GetWindowText', return_value="Notepad"), \
         patch('pyautogui.write') as mock_write:
        result = tools.type_text("safe text")
        assert "Text has been typed" in result
        mock_write.assert_called_once_with("safe text", interval=0.01)

def test_type_text_exception(tools):
    with patch('win32gui.GetForegroundWindow', side_effect=Exception("win32gui error")):
        result = tools.type_text("test")
        assert "Typing failed: win32gui error" in result
