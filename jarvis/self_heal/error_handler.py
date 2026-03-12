"""
JARVIS Self-Healing System — automatically diagnoses and fixes task failures.
"""
import os
import sys
import re
import subprocess
from dotenv import load_dotenv

load_dotenv()

# Common error → fix patterns (fast path before calling LLaMA)
KNOWN_FIXES = {
    r"ModuleNotFoundError: No module named '(\w+)'": {
        "fix_type": "install_package",
        "template": "pip install {0}"
    },
    r"pip: command not found": {
        "fix_type": "install_package",
        "template": f"{sys.executable} -m pip install {{0}}"
    },
    r"'(\w+)' is not recognized as an internal or external command": {
        "fix_type": "install_tool",
        "template": "winget install {0}"
    },
    r"PermissionError": {
        "fix_type": "run_as_admin",
        "template": "runas /user:Administrator \"{command}\""
    },
    r"FileNotFoundError: \[Errno 2\].*'(.*?)'": {
        "fix_type": "create_path",
        "template": "mkdir {0}"
    },
}


class ErrorHandler:
    def __init__(self, intent_parser=None, code_runner=None):
        self.parser = intent_parser
        self.runner = code_runner
        self.max_retries = 3

    def attempt_fix(self, task: str, error: str) -> dict:
        """
        Attempt to fix an error automatically.
        1. Try known fix patterns first (fast path).
        2. Fall back to LLaMA for analysis if no pattern matches.
        Returns: {"applied": True/False, "fix": "...", "new_command": "..."}
        """
        # Fast path — known error patterns
        for pattern, fix_info in KNOWN_FIXES.items():
            match = re.search(pattern, error)
            if match:
                result = self._apply_known_fix(fix_info, match, task, error)
                if result.get("applied"):
                    return result

        # LLaMA path
        if self.parser:
            return self._llama_fix(task, error)

        return {"applied": False, "fix": "No fix available", "new_command": None}

    def _apply_known_fix(self, fix_info: dict, match, task: str, error: str) -> dict:
        """Apply a known pattern fix."""
        fix_type = fix_info["fix_type"]
        try:
            args = match.groups()
            fix_cmd = fix_info["template"].format(*args, command=task) if args else fix_info["template"].format(command=task)
        except (IndexError, KeyError):
            fix_cmd = fix_info["template"]

        print(f"[SelfHeal] Applying fix: {fix_cmd}")

        if fix_type == "install_package":
            result = subprocess.run(
                f"{sys.executable} -m pip install {args[0] if args else ''}",
                shell=True, capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                return {"applied": True, "fix": f"Installed package: {args[0] if args else ''}", "new_command": task}

        elif fix_type == "create_path":
            path = args[0] if args else ""
            if path:
                os.makedirs(path, exist_ok=True)
                return {"applied": True, "fix": f"Created directory: {path}", "new_command": task}

        return {"applied": False, "fix": "Known fix pattern did not succeed"}

    def _llama_fix(self, task: str, error: str) -> dict:
        """Ask LLaMA to diagnose and suggest a fix."""
        try:
            fix_suggestion = self.parser.suggest_fix(task, error)
            fix_type = fix_suggestion.get("fix_type", "")
            fix_command = fix_suggestion.get("fix_command", "")

            print(f"[SelfHeal] LLaMA suggests: {fix_suggestion.get('analysis', 'unknown issue')}")
            print(f"[SelfHeal] Fix type: {fix_type} | Command: {fix_command}")

            if fix_command:
                if fix_type == "install_package":
                    result = subprocess.run(
                        f"{sys.executable} -m pip install {fix_command}",
                        shell=True, capture_output=True, text=True, timeout=120
                    )
                    if result.returncode == 0:
                        return {
                            "applied": True,
                            "fix": f"Installed: {fix_command}",
                            "new_command": task
                        }
                elif fix_type == "modify_command":
                    return {
                        "applied": True,
                        "fix": fix_suggestion.get("explanation", ""),
                        "new_command": fix_command
                    }
                else:
                    result = subprocess.run(
                        fix_command, shell=True, capture_output=True, text=True, timeout=30
                    )
                    if result.returncode == 0:
                        return {
                            "applied": True,
                            "fix": fix_suggestion.get("explanation", ""),
                            "new_command": task
                        }

            return {
                "applied": False,
                "fix": fix_suggestion.get("analysis", "Could not fix automatically"),
                "new_command": None
            }
        except Exception as e:
            return {"applied": False, "fix": f"Self-heal error: {e}", "new_command": None}

    def wrap(self, fn, task_description: str, *args, **kwargs):
        """
        Decorator-style wrapper: run fn(*args, **kwargs), auto-retry on failure.
        """
        for attempt in range(1, self.max_retries + 1):
            result = fn(*args, **kwargs)
            if isinstance(result, dict) and result.get("status") == "error":
                error_msg = result.get("message", "Unknown error")
                print(f"[SelfHeal] Attempt {attempt} failed: {error_msg}")
                if attempt < self.max_retries:
                    fix = self.attempt_fix(task=task_description, error=error_msg)
                    if not fix.get("applied"):
                        break
                else:
                    break
            else:
                return result
        return result
