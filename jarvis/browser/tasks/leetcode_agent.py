"""
JARVIS LeetCode Agent — opens LeetCode, reads a problem, solves it, and submits.
"""
import time
import re
from jarvis.browser.browser_controller import BrowserController


class LeetCodeAgent:
    def __init__(self, browser: BrowserController, intent_parser):
        self.browser = browser
        self.parser = intent_parser

    def solve_daily(self) -> dict:
        """Open the LeetCode daily challenge, solve it, and submit."""
        return self._solve_problem(url="https://leetcode.com/problemset/", daily=True)

    def solve_by_name(self, problem_name: str) -> dict:
        """Search and solve a specific problem by name."""
        slug = problem_name.lower().replace(" ", "-").replace("_", "-")
        url = f"https://leetcode.com/problems/{slug}/"
        return self._solve_problem(url=url)

    def _solve_problem(self, url: str, daily: bool = False) -> dict:
        """Core workflow: navigate → read → solve → paste → run → submit."""
        try:
            # Navigate to problem
            if daily:
                self.browser.goto("https://leetcode.com/problemset/")
                time.sleep(3)
                # Click on daily challenge link
                try:
                    self.browser.page.locator("a:has-text('Daily')").first.click()
                    time.sleep(3)
                except Exception:
                    # Fall back to first problem in list
                    self.browser.page.locator("a[href*='/problems/']").first.click()
                    time.sleep(3)
            else:
                self.browser.goto(url)
                time.sleep(3)

            # Get problem title
            try:
                title = self.browser.get_text("div[data-cy='question-title']") or \
                        self.browser.get_text(".text-title-large") or "Unknown Problem"
            except Exception:
                title = "LeetCode Problem"

            # Get problem description
            try:
                description = self.browser.get_text("div.question-content") or \
                              self.browser.get_text("[data-track-load='description_content']") or ""
            except Exception:
                description = ""

            print(f"[LeetCode] Solving: {title}")

            # Select Python3 language
            self._select_language("Python3")
            time.sleep(1)

            # Generate solution
            prompt = f"""
LeetCode Problem: {title}

Description:
{description[:1500]}

Write a complete Python3 solution. Use the Solution class with the appropriate method.
Return ONLY the code.
"""
            solution_code = self.parser.generate_code("Python3", prompt)

            # Clear editor and paste solution
            self._paste_code(solution_code)
            time.sleep(2)

            # Run code first
            run_result = self._run_code()
            time.sleep(4)

            # Check if tests passed
            if self._check_success():
                # Submit
                submit_result = self._submit()
                time.sleep(5)
                accepted = self._check_accepted()

                return {
                    "status": "success",
                    "title": title,
                    "solution": solution_code,
                    "submitted": True,
                    "accepted": accepted,
                    "message": f"✅ Solved and submitted: {title}" + (" — Accepted!" if accepted else " — Check submission status."),
                    "data": solution_code[:300] + "..."
                }
            else:
                return {
                    "status": "partial",
                    "title": title,
                    "solution": solution_code,
                    "submitted": False,
                    "message": f"⚠️ Code written for: {title} but tests didn't all pass. Review manually.",
                    "data": solution_code[:300] + "..."
                }

        except Exception as e:
            return {"status": "error", "message": f"LeetCode agent failed: {e}"}

    def _select_language(self, language: str):
        """Select programming language in the editor dropdown."""
        try:
            self.browser.page.locator("button:has-text('Python')").first.click()
            time.sleep(0.5)
            self.browser.page.locator(f"li:has-text('{language}')").first.click()
        except Exception:
            pass

    def _paste_code(self, code: str):
        """Clear the Monaco editor and paste new code."""
        try:
            editor = self.browser.page.locator(".monaco-editor .view-lines").first
            editor.click()
            time.sleep(0.3)
            # Select all and delete
            self.browser.page.keyboard.press("Control+A")
            time.sleep(0.2)
            self.browser.page.keyboard.press("Delete")
            time.sleep(0.2)
            # Type the code
            self.browser.page.keyboard.type(code, delay=5)
        except Exception as e:
            print(f"[LeetCode] Paste code failed: {e}")

    def _run_code(self) -> bool:
        """Click the Run button."""
        try:
            self.browser.page.locator("button:has-text('Run')").click()
            return True
        except Exception:
            return False

    def _submit(self) -> bool:
        """Click the Submit button."""
        try:
            self.browser.page.locator("button:has-text('Submit')").click()
            return True
        except Exception:
            return False

    def _check_success(self) -> bool:
        """Check if test cases passed."""
        try:
            time.sleep(3)
            result_text = self.browser.page.inner_text("body")
            return "passed" in result_text.lower() or "accepted" in result_text.lower()
        except Exception:
            return False

    def _check_accepted(self) -> bool:
        """Check if submission was accepted."""
        try:
            time.sleep(5)
            result_text = self.browser.page.inner_text("body")
            return "accepted" in result_text.lower()
        except Exception:
            return False
