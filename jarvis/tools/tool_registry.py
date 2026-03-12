"""JARVIS Tool Registry — stores and runs dynamically created Python tools."""
import os
import sys
import importlib.util
from dotenv import load_dotenv

load_dotenv()

TOOLS_DIR = os.path.abspath(os.getenv("TOOLS_DIR", "./jarvis/tools/generated"))


class ToolRegistry:
    def __init__(self):
        os.makedirs(TOOLS_DIR, exist_ok=True)
        self._tools = {}

    def register(self, name: str, path: str):
        """Register a tool by name and file path."""
        self._tools[name.lower()] = path

    def list_tools(self) -> list[str]:
        """List all registered tools."""
        files = [f.stem for f in __import__("pathlib").Path(TOOLS_DIR).glob("*.py")]
        return files

    def run_tool(self, name: str, *args) -> dict:
        """Dynamically import and run a tool's main() function."""
        path = os.path.join(TOOLS_DIR, f"{name}.py")
        if not os.path.exists(path):
            return {"status": "error", "message": f"Tool '{name}' not found. Available: {self.list_tools()}"}
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "main"):
                result = module.main(*args)
                return {"status": "success", "message": f"Tool '{name}' ran successfully.", "data": str(result)}
            return {"status": "error", "message": f"Tool '{name}' has no main() function."}
        except Exception as e:
            return {"status": "error", "message": f"Tool '{name}' failed: {e}"}
