"""
Application Launcher Router
────────────────────────────────────────────────────────────────────────────────
Opens desktop applications via voice command or API.
Supports Windows, macOS, and Linux.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import platform
import shutil
from typing import Optional, List

router = APIRouter(tags=["App"])


class LaunchAppRequest(BaseModel):
    """Request to launch an application"""
    app_name: str
    args: Optional[List[str]] = None


class LaunchAppResponse(BaseModel):
    """Response from launching an application"""
    status: str
    app: str
    command: str
    message: str


# Common application mappings (Windows)
WINDOWS_APP_MAP = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "terminal": "wt.exe",
    "windows terminal": "wt.exe",
    "vscode": "code.exe",
    "visual studio code": "code.exe",
    "outlook": "outlook.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "teams": "teams.exe",
    "spotify": "spotify.exe",
    "discord": "discord.exe",
    "slack": "slack.exe",
}

# Common application mappings (macOS)
MACOS_APP_MAP = {
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "firefox": "Firefox",
    "safari": "Safari",
    "edge": "Microsoft Edge",
    "microsoft edge": "Microsoft Edge",
    "terminal": "Terminal",
    "finder": "Finder",
    "vscode": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
    "outlook": "Microsoft Outlook",
    "word": "Microsoft Word",
    "excel": "Microsoft Excel",
    "powerpoint": "Microsoft PowerPoint",
    "teams": "Microsoft Teams",
    "spotify": "Spotify",
    "discord": "Discord",
    "slack": "Slack",
}

# Common application mappings (Linux)
LINUX_APP_MAP = {
    "chrome": "google-chrome",
    "google chrome": "google-chrome",
    "firefox": "firefox",
    "terminal": "gnome-terminal",
    "file manager": "nautilus",
    "vscode": "code",
    "visual studio code": "code",
}


def get_app_command(app_name: str) -> str:
    """Get the actual command to launch an application"""
    system = platform.system()
    app_lower = app_name.lower()
    
    if system == "Windows":
        return WINDOWS_APP_MAP.get(app_lower, app_name)
    elif system == "Darwin":  # macOS
        return MACOS_APP_MAP.get(app_lower, app_name)
    else:  # Linux
        return LINUX_APP_MAP.get(app_lower, app_name)


def is_app_available(app_command: str) -> bool:
    """Check if an application is available on the system"""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        # For macOS, check if application exists in Applications folder
        try:
            result = subprocess.run(
                ["osascript", "-e", f'tell application "System Events" to exists application "{app_command}"'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() == "true"
        except:
            return False
    else:
        # For Windows/Linux, check if command exists in PATH
        return shutil.which(app_command) is not None


@router.get("/status")
async def get_status():
    """Get app launcher status"""
    return {
        "status": "ok",
        "module": "App Launcher",
        "platform": platform.system(),
        "available_apps": len(WINDOWS_APP_MAP) if platform.system() == "Windows" else 
                         len(MACOS_APP_MAP) if platform.system() == "Darwin" else
                         len(LINUX_APP_MAP)
    }


@router.post("/launch", response_model=LaunchAppResponse)
async def launch_app(request: LaunchAppRequest):
    """
    Launch a desktop application
    
    Examples:
        - POST /api/personal/app/launch {"app_name": "chrome"}
        - POST /api/personal/app/launch {"app_name": "notepad", "args": ["test.txt"]}
    """
    app_name = request.app_name
    args = request.args or []
    
    # Get the actual command for this platform
    app_command = get_app_command(app_name)
    
    # Check if app is available (optional - may slow down)
    # if not is_app_available(app_command):
    #     raise HTTPException(
    #         status_code=404,
    #         detail=f"Application '{app_name}' not found on this system"
    #     )
    
    try:
        system = platform.system()
        
        if system == "Windows":
            # Windows: Start process detached
            subprocess.Popen(
                [app_command] + args,
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
            
        elif system == "Darwin":  # macOS
            # macOS: Use 'open' command
            if app_command in MACOS_APP_MAP.values():
                # Application bundle name
                subprocess.Popen(
                    ["open", "-a", app_command] + args,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                # Direct command
                subprocess.Popen(
                    [app_command] + args,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
        else:  # Linux
            # Linux: Start process with nohup
            subprocess.Popen(
                [app_command] + args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        
        return LaunchAppResponse(
            status="launched",
            app=app_name,
            command=app_command,
            message=f"Successfully launched {app_name}"
        )
        
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Application '{app_name}' not found. Command: {app_command}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to launch {app_name}: {str(e)}"
        )


@router.get("/list")
async def list_apps():
    """List available applications for current platform"""
    system = platform.system()
    
    if system == "Windows":
        app_map = WINDOWS_APP_MAP
    elif system == "Darwin":
        app_map = MACOS_APP_MAP
    else:
        app_map = LINUX_APP_MAP
    
    return {
        "platform": system,
        "applications": [
            {"name": name, "command": cmd}
            for name, cmd in sorted(app_map.items())
        ]
    }
