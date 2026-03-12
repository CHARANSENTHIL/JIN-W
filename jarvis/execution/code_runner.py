"""
JARVIS Code Runner — execute Python scripts and shell commands with self-heal.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class CodeRunner:
    def __init__(self, self_healer=None):
        self.self_healer = self_healer
        self.max_retries = 3

    def run_python(self, path: str, timeout: int = 30) -> dict:
        """
        Run a Python script and return stdout/stderr.
        Automatically triggers self-heal on failure.
        """
        full_path = str(Path(os.path.expandvars(path)).resolve())
        if not os.path.exists(full_path):
            return {"status": "error", "message": f"File not found: {full_path}"}

        for attempt in range(1, self.max_retries + 1):
            try:
                result = subprocess.run(
                    [sys.executable, full_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=os.path.dirname(full_path)
                )
                if result.returncode == 0:
                    return {
                        "status": "success",
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": 0,
                        "message": f"✅ Script ran successfully.\n{result.stdout[:500] if result.stdout else '(no output)'}"
                    }
                else:
                    error_msg = result.stderr or result.stdout
                    if self.self_healer and attempt < self.max_retries:
                        fix = self.self_healer.attempt_fix(
                            task=f"Run Python script: {full_path}",
                            error=error_msg
                        )
                        if fix.get("applied"):
                            continue
                    return {
                        "status": "error",
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode,
                        "message": f"❌ Script failed (attempt {attempt}/{self.max_retries}):\n{error_msg[:500]}"
                    }
            except subprocess.TimeoutExpired:
                return {"status": "timeout", "message": f"Script timed out after {timeout}s"}
            except Exception as e:
                return {"status": "error", "message": f"Execution error: {e}"}

        return {"status": "error", "message": "Maximum retries reached. Could not fix the error."}

    def run_python_string(self, code: str, timeout: int = 30) -> dict:
        """
        Run a Python code string directly (via temp file).
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp_path = f.name
        try:
            result = self.run_python(tmp_path, timeout=timeout)
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return result

    def run_command(self, command: str, timeout: int = 30, cwd: str = None) -> dict:
        """
        Run a shell command (PowerShell on Windows).
        Returns stdout, stderr, return code.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=cwd
                )
                if result.returncode == 0:
                    return {
                        "status": "success",
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": 0,
                        "message": f"✅ Command executed.\n{result.stdout[:500] if result.stdout else '(no output)'}"
                    }
                else:
                    error_msg = result.stderr or result.stdout
                    if self.self_healer and attempt < self.max_retries:
                        fix = self.self_healer.attempt_fix(
                            task=f"Shell command: {command}",
                            error=error_msg
                        )
                        if fix.get("applied"):
                            command = fix.get("new_command", command)
                            continue
                    return {
                        "status": "error",
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode,
                        "message": f"❌ Command failed:\n{error_msg[:500]}"
                    }
            except subprocess.TimeoutExpired:
                return {"status": "timeout", "message": f"Command timed out after {timeout}s"}
            except Exception as e:
                return {"status": "error", "message": f"Command execution error: {e}"}

        return {"status": "error", "message": "Maximum retries reached."}

    def install_package(self, package: str) -> dict:
        """Install a Python package using pip."""
        result = self.run_command(f"{sys.executable} -m pip install {package}", timeout=120)
        if result["status"] == "success":
            result["message"] = f"✅ Installed: {package}"
        return result
