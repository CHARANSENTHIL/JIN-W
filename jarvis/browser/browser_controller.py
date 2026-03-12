"""
JARVIS Browser Controller — base Playwright browser for task automation.
Uses Microsoft Edge (pre-installed on Windows). Runs in a SEPARATE context from WhatsApp Web.
"""
import os
import time
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

BROWSER_SESSION_DIR = os.path.abspath("./jarvis/.browser_session")


class BrowserController:
    """
    Shared Playwright browser instance for running browser automation tasks.
    Keeps browser alive between tasks for performance.
    """

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        os.makedirs(BROWSER_SESSION_DIR, exist_ok=True)

    def start(self):
        """Launch Microsoft Edge and create a persistent context."""
        self.playwright = sync_playwright().start()
        self.context = self.playwright.chromium.launch_persistent_context(
            BROWSER_SESSION_DIR,
            channel="msedge",          # Use installed Microsoft Edge
            headless=self.headless,
            args=["--no-sandbox", "--window-size=1280,900"],
            viewport={"width": 1280, "height": 900},
        )
        self.page = self.context.new_page() if not self.context.pages else self.context.pages[0]
        return self

    def new_page(self) -> Page:
        """Open a new tab."""
        return self.context.new_page()

    def goto(self, url: str, wait: str = "networkidle") -> bool:
        """Navigate to a URL and wait for it to load."""
        try:
            self.page.goto(url, wait_until=wait, timeout=30000)
            return True
        except Exception as e:
            print(f"[Browser] Navigation failed: {e}")
            return False

    def click(self, selector: str, timeout: int = 5000) -> bool:
        """Click an element by selector."""
        try:
            self.page.click(selector, timeout=timeout)
            return True
        except Exception as e:
            print(f"[Browser] Click failed ({selector}): {e}")
            return False

    def fill(self, selector: str, text: str) -> bool:
        """Fill an input field."""
        try:
            self.page.fill(selector, text)
            return True
        except Exception as e:
            print(f"[Browser] Fill failed ({selector}): {e}")
            return False

    def get_text(self, selector: str) -> str:
        """Get text content of an element."""
        try:
            return self.page.inner_text(selector, timeout=5000)
        except Exception:
            return ""

    def screenshot(self, filename: str = "browser_screenshot.png") -> str:
        """Take screenshot of the current page."""
        path = os.path.join(BROWSER_SESSION_DIR, filename)
        try:
            self.page.screenshot(path=path, full_page=False)
            return path
        except Exception as e:
            print(f"[Browser] Screenshot failed: {e}")
            return ""

    def wait_for(self, selector: str, timeout: int = 10000) -> bool:
        """Wait for an element to appear."""
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False

    def scroll_to_bottom(self):
        """Scroll to the bottom of the page."""
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.5)

    def close(self):
        """Close browser and playwright."""
        try:
            if self.context:
                self.context.close()
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass
