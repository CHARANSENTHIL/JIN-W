"""
JARVIS Vision Layer — screen capture, OCR, error detection, and UI interaction.
"""
import os
import re
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TESSERACT_PATH = os.getenv("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
SCREENSHOT_DIR = os.path.abspath("./jarvis/.screenshots")


class ScreenReader:
    def __init__(self):
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        self._setup_tesseract()

    def _setup_tesseract(self):
        """Configure pytesseract path."""
        try:
            import pytesseract
            if os.path.exists(TESSERACT_PATH):
                pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
            self._ocr_available = True
        except ImportError:
            print("[Vision] pytesseract not installed — OCR disabled")
            self._ocr_available = False

    def take_screenshot(self, filename: str = None) -> str:
        """
        Capture the entire screen.
        Returns the file path of the saved screenshot.
        """
        try:
            import mss
            from PIL import Image

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = filename or f"screenshot_{ts}.png"
            path = os.path.join(SCREENSHOT_DIR, filename)

            with mss.mss() as sct:
                monitor = sct.monitors[0]  # All monitors combined
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                img.save(path)

            return path
        except Exception as e:
            print(f"[Vision] Screenshot failed: {e}")
            return ""

    def ocr_screen(self, screenshot_path: str = None) -> str:
        """
        Run OCR on the screen (or a given screenshot).
        Returns extracted text.
        """
        if not self._ocr_available:
            return ""

        try:
            import pytesseract
            from PIL import Image

            if screenshot_path and os.path.exists(screenshot_path):
                img = Image.open(screenshot_path)
            else:
                # Take a fresh screenshot
                path = self.take_screenshot()
                if not path:
                    return ""
                img = Image.open(path)

            text = pytesseract.image_to_string(img)
            return text
        except Exception as e:
            print(f"[Vision] OCR failed: {e}")
            return ""

    def find_error(self, screenshot_path: str = None) -> dict:
        """
        Scan screen for common error patterns.
        Returns detected errors with context.
        """
        text = self.ocr_screen(screenshot_path)
        if not text:
            return {"found": False, "errors": []}

        # Common error patterns
        error_patterns = [
            r"(?i)(error|exception|traceback|failed|failure|crash|fatal)",
            r"(?i)(ModuleNotFoundError|ImportError|SyntaxError|TypeError|ValueError|AttributeError)",
            r"(?i)(cannot find|not found|does not exist|permission denied|access denied)",
            r"(?i)(connection refused|timeout|unreachable)",
        ]

        found_errors = []
        lines = text.splitlines()
        for i, line in enumerate(lines):
            for pattern in error_patterns:
                if re.search(pattern, line):
                    # Include context lines
                    start = max(0, i - 1)
                    end = min(len(lines), i + 3)
                    context = "\n".join(lines[start:end]).strip()
                    if context and context not in found_errors:
                        found_errors.append(context)
                    break

        return {
            "found": len(found_errors) > 0,
            "errors": found_errors[:5],  # limit to 5 error blocks
            "full_text": text
        }

    def find_text_on_screen(self, search_text: str, screenshot_path: str = None) -> bool:
        """Check if specific text appears on screen."""
        screen_text = self.ocr_screen(screenshot_path)
        return search_text.lower() in screen_text.lower()

    def click_element(self, text: str) -> bool:
        """
        Find a UI element by its text (via OCR bounding box) and click it.
        """
        if not self._ocr_available:
            return False
        try:
            import pytesseract
            from PIL import Image
            import pyautogui

            path = self.take_screenshot()
            img = Image.open(path)
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

            for i, word in enumerate(data["text"]):
                if text.lower() in word.lower() and int(data["conf"][i]) > 50:
                    x = data["left"][i] + data["width"][i] // 2
                    y = data["top"][i] + data["height"][i] // 2
                    pyautogui.click(x, y)
                    return True

            return False
        except Exception as e:
            print(f"[Vision] click_element failed: {e}")
            return False

    def type_at_cursor(self, text: str, delay: float = 0.05):
        """Type text at the current cursor position."""
        try:
            import pyautogui
            pyautogui.typewrite(text, interval=delay)
        except Exception as e:
            print(f"[Vision] type_at_cursor failed: {e}")

    def get_latest_screenshot_path(self) -> str | None:
        """Return the path of the most recent screenshot."""
        try:
            files = sorted(Path(SCREENSHOT_DIR).glob("*.png"), key=lambda f: f.stat().st_mtime, reverse=True)
            return str(files[0]) if files else None
        except Exception:
            return None
