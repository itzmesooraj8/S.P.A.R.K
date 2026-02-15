import os
import shutil
import sys
from pydub import AudioSegment

def ensure_ffmpeg():
    """
    Locates FFmpeg and ensures it's in the system PATH and registered with Pydub.
    This fixes the 'RuntimeWarning: Couldn't find ffmpeg' error without a reboot.
    """
    # 1. Check if already in PATH
    if shutil.which("ffmpeg"):
        print("[SYSTEM] FFmpeg found in PATH.")
        return

    # 2. Known standard paths (WinGet, Chocolatey, Manual)
    # We use the specific path found in the user's previous system checks
    possible_paths = [
        r"C:\Users\itzme\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin",
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin"
    ]

    ffmpeg_exe = None
    for path in possible_paths:
        exe_path = os.path.join(path, "ffmpeg.exe")
        if os.path.exists(exe_path):
            ffmpeg_exe = exe_path
            # Add to PATH for subprocess calls
            os.environ["PATH"] += os.pathsep + path
            print(f"[SYSTEM] Manually added FFmpeg to PATH: {path}")
            break
    
    # 3. Register with Pydub
    if ffmpeg_exe:
        AudioSegment.converter = ffmpeg_exe
        print(f"[SYSTEM] Pydub converter set to: {ffmpeg_exe}")
    else:
        print("[SYSTEM] ⚠️ FFmpeg not found in standard locations. Audio may fail.")

