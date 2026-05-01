import logging
import pyautogui
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

logger = logging.getLogger("SPARK_MEDIA")

def control_media(action: str, value: int = None) -> str:
    """Controls Windows volume and media playback."""
    try:
        if action == "playpause":
            pyautogui.press("playpause")
            return "Playback toggled."
        elif action == "next":
            pyautogui.press("nexttrack")
            return "Skipped to next track."
        elif action == "prev":
            pyautogui.press("prevtrack")
            return "Going to previous track."
        elif action in ["mute", "unmute", "volume"]:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            
            if action == "mute":
                volume.SetMute(1, None)
                return "System muted."
            elif action == "unmute":
                volume.SetMute(0, None)
                return "System unmuted."
            elif action == "volume" and value is not None:
                # Value should be 0 to 100
                target_vol = max(0, min(100, value))
                # pycaw volume scalar is 0.0 to 1.0
                volume.SetMasterVolumeLevelScalar(target_vol / 100.0, None)
                return f"Volume set to {target_vol}%."
        return "Unknown media command."
    except Exception as e:
        logger.error(f"Media control error: {e}")
        return "I encountered an error managing the audio system."
