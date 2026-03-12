"""
JARVIS File Manager — create, read, write, delete files and directories.
Uses LLaMA to generate code when writing code files.
"""
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Language → file extension mapping
LANG_EXTENSIONS = {
    "python": ".py", "py": ".py",
    "javascript": ".js", "js": ".js",
    "typescript": ".ts", "ts": ".ts",
    "java": ".java",
    "c": ".c",
    "cpp": ".cpp", "c++": ".cpp",
    "html": ".html",
    "css": ".css",
    "json": ".json",
    "yaml": ".yaml", "yml": ".yaml",
    "bash": ".sh", "shell": ".sh",
    "powershell": ".ps1",
    "sql": ".sql",
    "markdown": ".md", "md": ".md",
    "text": ".txt", "txt": ".txt",
}


class FileManager:
    def __init__(self, intent_parser=None):
        self.parser = intent_parser  # For code generation via LLaMA

    def _expand(self, path: str) -> str:
        """Expand environment variables and normalize path."""
        return str(Path(os.path.expandvars(os.path.expanduser(path))).resolve())

    def create_file(self, path: str, content: str = "") -> dict:
        """Create a file with optional content. Creates parent dirs automatically."""
        try:
            full_path = self._expand(path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {
                "status": "success",
                "message": f"✅ File created: {full_path}",
                "path": full_path
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to create file: {e}"}

    def write_code(self, path: str, language: str, description: str) -> dict:
        """Generate code using LLaMA and write it to a file."""
        if not self.parser:
            return {"status": "error", "message": "IntentParser not available for code generation"}

        # Determine extension if not specified
        full_path = self._expand(path)
        _, ext = os.path.splitext(full_path)
        if not ext:
            lang_key = language.lower()
            ext = LANG_EXTENSIONS.get(lang_key, ".txt")
            full_path += ext

        try:
            code = self.parser.generate_code(language=language, description=description)
            return self.create_file(full_path, code)
        except Exception as e:
            return {"status": "error", "message": f"Code generation failed: {e}"}

    def read_file(self, path: str) -> dict:
        """Read and return file contents."""
        try:
            full_path = self._expand(path)
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return {
                "status": "success",
                "path": full_path,
                "content": content,
                "size_bytes": os.path.getsize(full_path),
                "lines": content.count("\n") + 1
            }
        except FileNotFoundError:
            return {"status": "error", "message": f"File not found: {path}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to read file: {e}"}

    def delete_file(self, path: str) -> dict:
        """Delete a file."""
        try:
            full_path = self._expand(path)
            os.remove(full_path)
            return {"status": "success", "message": f"✅ Deleted: {full_path}"}
        except FileNotFoundError:
            return {"status": "error", "message": f"File not found: {path}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to delete: {e}"}

    def move_file(self, src: str, dst: str) -> dict:
        """Move or rename a file."""
        try:
            full_src = self._expand(src)
            full_dst = self._expand(dst)
            shutil.move(full_src, full_dst)
            return {"status": "success", "message": f"✅ Moved: {full_src} → {full_dst}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to move file: {e}"}

    def copy_file(self, src: str, dst: str) -> dict:
        """Copy a file."""
        try:
            full_src = self._expand(src)
            full_dst = self._expand(dst)
            os.makedirs(os.path.dirname(full_dst), exist_ok=True)
            shutil.copy2(full_src, full_dst)
            return {"status": "success", "message": f"✅ Copied: {full_src} → {full_dst}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to copy file: {e}"}

    def create_dir(self, path: str) -> dict:
        """Create a directory (and parents)."""
        try:
            full_path = self._expand(path)
            os.makedirs(full_path, exist_ok=True)
            return {"status": "success", "message": f"✅ Directory created: {full_path}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to create directory: {e}"}

    def list_dir(self, path: str = ".") -> dict:
        """List directory contents."""
        try:
            full_path = self._expand(path)
            items = []
            for entry in os.scandir(full_path):
                items.append({
                    "name": entry.name,
                    "type": "dir" if entry.is_dir() else "file",
                    "size_bytes": entry.stat().st_size if entry.is_file() else None,
                })
            return {
                "status": "success",
                "path": full_path,
                "items": items,
                "count": len(items)
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to list directory: {e}"}

    def append_to_file(self, path: str, content: str) -> dict:
        """Append text to an existing file."""
        try:
            full_path = self._expand(path)
            with open(full_path, "a", encoding="utf-8") as f:
                f.write(content)
            return {"status": "success", "message": f"✅ Appended to: {full_path}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to append: {e}"}
