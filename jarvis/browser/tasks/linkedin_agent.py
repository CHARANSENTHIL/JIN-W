"""
JARVIS LinkedIn Agent — creates and publishes LinkedIn posts via browser automation.
"""
import time
from jarvis.browser.browser_controller import BrowserController


class LinkedInAgent:
    def __init__(self, browser: BrowserController, intent_parser):
        self.browser = browser
        self.parser = intent_parser

    def create_post(self, topic: str, additional_context: str = "") -> dict:
        """
        Log into LinkedIn and publish a post about the given topic.
        """
        try:
            # Navigate to LinkedIn
            self.browser.goto("https://www.linkedin.com/feed/")
            time.sleep(3)

            # Check if logged in
            if "login" in self.browser.page.url or "signin" in self.browser.page.url:
                return {
                    "status": "auth_required",
                    "message": "⚠️ Please log in to LinkedIn in the browser window first, then retry."
                }

            # Generate post content using LLaMA
            full_topic = topic
            if additional_context:
                full_topic += f"\n\nAdditional context: {additional_context}"
            post_content = self.parser.generate_linkedin_post(topic=full_topic)
            print(f"[LinkedIn] Generated post ({len(post_content)} chars)")

            # Click "Start a post" button
            start_post_selectors = [
                "button.share-box-feed-entry__trigger",
                "[placeholder='What do you want to talk about?']",
                "span:has-text('Start a post')",
                ".share-box-feed-entry__closed-share-box"
            ]
            clicked = False
            for sel in start_post_selectors:
                if self.browser.click(sel, timeout=3000):
                    clicked = True
                    break

            if not clicked:
                return {"status": "error", "message": "Could not find LinkedIn post button. LinkedIn UI may have changed."}

            time.sleep(2)

            # Type post content
            text_area_selectors = [
                "div.ql-editor",
                "[contenteditable='true']",
                ".editor-content div[contenteditable]"
            ]
            typed = False
            for sel in text_area_selectors:
                try:
                    self.browser.page.wait_for_selector(sel, timeout=4000)
                    self.browser.page.click(sel)
                    time.sleep(0.3)
                    self.browser.page.keyboard.type(post_content, delay=10)
                    typed = True
                    break
                except Exception:
                    continue

            if not typed:
                return {"status": "error", "message": "Could not type into LinkedIn post editor."}

            time.sleep(1)

            # Take screenshot for confirmation
            screenshot = self.browser.screenshot("linkedin_post_preview.png")

            # Click Post button
            post_btn_selectors = [
                "button.share-actions__primary-action",
                "button:has-text('Post')",
                "[data-control-name='share.post']"
            ]
            posted = False
            for sel in post_btn_selectors:
                if self.browser.click(sel, timeout=3000):
                    posted = True
                    break

            if not posted:
                return {
                    "status": "error",
                    "message": "Could not click Post button. Please post manually from the preview.",
                    "post_content": post_content,
                    "screenshot": screenshot
                }

            time.sleep(3)
            print("[LinkedIn] Post published!")

            return {
                "status": "success",
                "message": "✅ LinkedIn post published!",
                "post_content": post_content,
                "screenshot": screenshot,
                "data": f"Post preview:\n{post_content[:300]}..."
            }

        except Exception as e:
            return {"status": "error", "message": f"LinkedIn agent failed: {e}"}

    def post_about_leetcode(self, problem_title: str, solution_summary: str) -> dict:
        """Convenience method: post about a solved LeetCode problem."""
        topic = f"I just solved the LeetCode problem '{problem_title}'!\n\nSolution approach: {solution_summary}"
        return self.create_post(topic)
