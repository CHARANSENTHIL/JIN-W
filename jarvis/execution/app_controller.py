"""
JARVIS App Controller — open, close, and list applications on Windows.
"""
import os
import subprocess
import psutil
import pygetwindow as gw
from pathlib import Path

# Registry of common application names → executable paths / commands
APP_REGISTRY = {
    "vscode": [
        r"C:\Program Files\Microsoft VS Code\Code.exe",
        r"C:\Users\{user}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    ],
    "code": "vscode",  # alias
    "visual studio code": "vscode",
    "notepad": "notepad.exe",
    "notepad++": r"C:\Program Files\Notepad++\notepad++.exe",
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "google chrome": "chrome",
    "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "whatsapp": [
        r"C:\Users\{user}\AppData\Local\WhatsApp\WhatsApp.exe",
        r"C:\Program Files\WindowsApps\WhatsApp*\WhatsApp.exe",
    ],
    "spotify": r"C:\Users\{user}\AppData\Roaming\Spotify\Spotify.exe",
    "discord": r"C:\Users\{user}\AppData\Local\Discord\Update.exe --processStart Discord.exe",
    "telegram": r"C:\Users\{user}\AppData\Roaming\Telegram Desktop\Telegram.exe",
    "vlc": r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "task manager": "taskmgr.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "terminal": "wt.exe",  # Windows Terminal
    "windows terminal": "wt.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "word": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "excel": r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    "obs": r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
    "pycharm": r"C:\Program Files\JetBrains\PyCharm*\bin\pycharm64.exe",
    "steam": r"C:\Program Files (x86)\Steam\Steam.exe",
    "zoom": r"C:\Users\{user}\AppData\Roaming\Zoom\bin\Zoom.exe",
    "teams": r"C:\Users\{user}\AppData\Local\Microsoft\Teams\current\Teams.exe",
    "camera": "start microsoft.windows.camera:",
    "settings": "start ms-settings:",
}

# Process name patterns for closing apps
PROCESS_MAP = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "edge": "msedge.exe",
    "vscode": "Code.exe",
    "code": "Code.exe",
    "visual studio code": "Code.exe",
    "notepad": "notepad.exe",
    "notepad++": "notepad++.exe",
    "spotify": "Spotify.exe",
    "discord": "Discord.exe",
    "whatsapp": "WhatsApp.exe",
    "vlc": "vlc.exe",
    "task manager": "Taskmgr.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "calculator": "CalculatorApp.exe",
    "zoom": "Zoom.exe",
    "teams": "Teams.exe",
    "obs": "obs64.exe",
    "steam": "Steam.exe",
    "pycharm": "pycharm64.exe",
    "telegram": "Telegram.exe",
    "camera": "WindowsCamera.exe",
    "settings": "SystemSettings.exe",
}


class AppController:
    def __init__(self):
        self.username = os.environ.get("USERNAME", "User")

    def _resolve_path(self, path_template: str) -> str:
        """Replace {user} placeholder and resolve glob patterns."""
        path = path_template.replace("{user}", self.username)
        if "*" in path:
            import glob
            matches = glob.glob(path)
            if matches:
                return matches[0]
            return path
        return path

    def _find_executable(self, app_name: str) -> str | None:
        """Find the executable path for an app."""
        key = app_name.lower().strip()

        # Resolve aliases
        while isinstance(APP_REGISTRY.get(key), str) and not APP_REGISTRY[key].endswith(".exe") and not "\\" in APP_REGISTRY[key]:
            key = APP_REGISTRY[key]

        paths = APP_REGISTRY.get(key)
        if not paths:
            return None

        if isinstance(paths, str):
            paths = [paths]

        for p in paths:
            resolved = self._resolve_path(p)
            if os.path.exists(resolved):
                return resolved

        return None

    def open_app(self, app_name: str) -> dict:
        """
        Open an application by name.
        Returns a result dict with status and message.
        """
        app_lower = app_name.lower().strip()

        # Check if already running
        for proc in psutil.process_iter(["name"]):
            proc_name = proc.info["name"].lower()
            target = PROCESS_MAP.get(app_lower, "").lower()
            if target and proc_name == target:
                # Try to bring to focus
                try:
                    wins = gw.getWindowsWithTitle(app_name)
                    if wins:
                        wins[0].activate()
                except Exception:
                    pass
                return {
                    "status": "already_running",
                    "message": f"{app_name} is already running and brought to focus."
                }

        # Find and launch
        exe_path = self._find_executable(app_lower)
        if exe_path:
            try:
                subprocess.Popen(
                    [exe_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
                return {
                    "status": "success",
                    "message": f"✅ {app_name} launched successfully."
                }
            except Exception as e:
                return {"status": "error", "message": f"Failed to launch {app_name}: {e}"}
        else:
            # Try with shell — works for system apps and PATH apps
            cmd = app_lower
            key = app_lower
            # Resolve aliases
            while isinstance(APP_REGISTRY.get(key), str) and not APP_REGISTRY[key].endswith(".exe") and not "\\" in APP_REGISTRY[key] and not ":" in APP_REGISTRY[key]:
                key = APP_REGISTRY[key]
            
            reg_val = APP_REGISTRY.get(key)
            if isinstance(reg_val, str):
                cmd = reg_val
            elif isinstance(reg_val, list) and reg_val:
                cmd = reg_val[0]

            try:
                subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return {
                    "status": "success",
                    "message": f"✅ {app_name} launched via shell."
                }
            except Exception as e:
                return {
                    "status": "not_found",
                    "message": f"Could not find or launch '{app_name}'. Is it installed? (Error: {e})"
                }

    def close_app(self, app_name: str) -> dict:
        """
        Close an application by name (terminates all matching processes).
        """
        app_lower = app_name.lower().strip()
        target_proc = PROCESS_MAP.get(app_lower, app_lower + ".exe").lower()

        killed = []
        for proc in psutil.process_iter(["pid", "name"]):
            if proc.info["name"].lower() == target_proc:
                try:
                    proc.terminate()
                    killed.append(proc.info["pid"])
                except psutil.AccessDenied:
                    proc.kill()
                except Exception:
                    pass

        if killed:
            return {
                "status": "success",
                "message": f"✅ {app_name} closed (PIDs: {killed})."
            }
        return {
            "status": "not_running",
            "message": f"{app_name} was not running."
        }

    def list_running_apps(self) -> list[str]:
        """Return list of unique running process names."""
        seen = set()
        apps = []
        for proc in psutil.process_iter(["name"]):
            name = proc.info["name"]
            if name and name not in seen:
                seen.add(name)
                apps.append(name)
        return sorted(apps)

    def is_running(self, app_name: str) -> bool:
        """Check if an app is currently running."""
        app_lower = app_name.lower().strip()
        target = PROCESS_MAP.get(app_lower, app_lower + ".exe").lower()
        return any(
            p.info["name"].lower() == target
            for p in psutil.process_iter(["name"])
        )
