"""
JARVIS Crew Manager — assembles and runs CrewAI agents based on task intent.
The central routing hub that connects intents to execution.
"""
import os
from dotenv import load_dotenv

load_dotenv()

from jarvis.execution.app_controller import AppController
from jarvis.execution.file_manager import FileManager
from jarvis.execution.system_monitor import SystemMonitor
from jarvis.execution.code_runner import CodeRunner
from jarvis.memory.memory_manager import MemoryManager
from jarvis.knowledge.graph_manager import GraphManager
from jarvis.vision.screen_reader import ScreenReader
from jarvis.self_heal.error_handler import ErrorHandler

# Browser agents (lazy-loaded to avoid startup cost)
_browser_ctrl = None
_leetcode_agent = None
_linkedin_agent = None
_movie_agent = None


def _get_browser():
    """Lazy-load the shared browser controller."""
    global _browser_ctrl
    if _browser_ctrl is None:
        from jarvis.browser.browser_controller import BrowserController
        _browser_ctrl = BrowserController(headless=False)
        _browser_ctrl.start()
    return _browser_ctrl


class CrewManager:
    """
    Routes parsed intents to the appropriate execution layer.
    Acts as the Planner + Executor combined for straightforward tasks,
    and assembles multi-step crews for complex tasks.
    """

    def __init__(self, intent_parser=None, whatsapp_sender=None):
        self.parser = intent_parser
        self.whatsapp_sender = whatsapp_sender  # Callback for sending WhatsApp replies

        # Initialize core components
        self.app_ctrl = AppController()
        self.file_mgr = FileManager(intent_parser=intent_parser)
        self.monitor = SystemMonitor()
        self.memory = MemoryManager()
        self.graph = GraphManager()
        self.vision = ScreenReader()
        self.self_healer = ErrorHandler(intent_parser=intent_parser)
        self.runner = CodeRunner(self_healer=self.self_healer)

        # Set self_healer on runner
        self.runner.self_healer = self.self_healer

    def set_parser(self, parser):
        self.parser = parser
        self.file_mgr.parser = parser
        self.self_healer.parser = parser

    def execute(self, intent: dict) -> dict:
        """
        Main dispatch method: route intent to appropriate handler.
        Automatically logs task to memory after execution.
        """
        intent_type = intent.get("intent", "unknown")
        params = intent.get("parameters", {})
        raw_input = intent.get("raw_input", "")

        # Dispatch table
        handlers = {
            "open_application": self._handle_open_app,
            "close_application": self._handle_close_app,
            "create_file": self._handle_create_file,
            "delete_file": self._handle_delete_file,
            "read_file": self._handle_read_file,
            "write_code": self._handle_write_code,
            "run_code": self._handle_run_code,
            "run_command": self._handle_run_command,
            "system_monitor": self._handle_system_monitor,
            "take_screenshot": self._handle_screenshot,
            "browser_task": self._handle_browser_task,
            "memory_recall": self._handle_memory_recall,
            "knowledge_query": self._handle_knowledge_query,
            "create_tool": self._handle_create_tool,
            "chitchat": self._handle_chitchat,
            "unknown": self._handle_unknown,
        }

        handler = handlers.get(intent_type, self._handle_unknown)
        try:
            result = handler(params, intent)
        except Exception as e:
            result = {"status": "error", "message": f"Execution error: {e}"}

        # Log task to memory
        try:
            self.memory.log_task(command=raw_input, intent=intent, result=result)
        except Exception:
            pass

        return result

    # ─── Handlers ──────────────────────────────────────────────

    def _handle_open_app(self, params: dict, intent: dict) -> dict:
        app = params.get("app", "")
        if not app:
            return {"status": "error", "message": "No app specified."}
        return self.app_ctrl.open_app(app)

    def _handle_close_app(self, params: dict, intent: dict) -> dict:
        app = params.get("app", "")
        return self.app_ctrl.close_app(app)

    def _handle_create_file(self, params: dict, intent: dict) -> dict:
        path = params.get("path", "")
        content = params.get("content", "")
        if not path:
            return {"status": "error", "message": "No file path specified."}
        return self.file_mgr.create_file(path, content)

    def _handle_delete_file(self, params: dict, intent: dict) -> dict:
        path = params.get("path", "")
        return self.file_mgr.delete_file(path)

    def _handle_read_file(self, params: dict, intent: dict) -> dict:
        path = params.get("path", "")
        result = self.file_mgr.read_file(path)
        if result["status"] == "success":
            content = result["content"]
            # Truncate for WhatsApp
            result["data"] = content[:2000] + ("..." if len(content) > 2000 else "")
            result["message"] = f"📄 {path} ({result['lines']} lines)"
        return result

    def _handle_write_code(self, params: dict, intent: dict) -> dict:
        path = params.get("path", "")
        language = params.get("language", "python")
        description = params.get("content", params.get("description", ""))
        if not self.parser:
            return {"status": "error", "message": "AI engine not connected."}
        return self.file_mgr.write_code(path, language, description)

    def _handle_run_code(self, params: dict, intent: dict) -> dict:
        path = params.get("path", "")
        if path.endswith(".py"):
            return self.runner.run_python(path)
        return self.runner.run_command(f'python "{path}"')

    def _handle_run_command(self, params: dict, intent: dict) -> dict:
        command = params.get("command", "")
        return self.runner.run_command(command)

    def _handle_system_monitor(self, params: dict, intent: dict) -> dict:
        metric = params.get("metric", "all").lower()
        if metric in ("cpu",):
            data = self.monitor.cpu_usage()
            return {"status": "success", "message": data["formatted"], "data": ""}
        elif metric in ("ram", "memory"):
            data = self.monitor.ram_usage()
            return {"status": "success", "message": data["formatted"], "data": ""}
        elif metric in ("gpu", "gpu_temp", "temperature"):
            data = self.monitor.gpu_temp()
            return {"status": "success", "message": data.get("formatted", str(data)), "data": ""}
        elif metric in ("disk", "storage"):
            data = self.monitor.disk_usage()
            return {"status": "success", "message": data["formatted"], "data": ""}
        else:
            data = self.monitor.all_stats()
            return {"status": "success", "message": data["summary"], "data": ""}

    def _handle_screenshot(self, params: dict, intent: dict) -> dict:
        path = self.vision.take_screenshot()
        if path:
            # Send file via WhatsApp if sender is available
            if self.whatsapp_sender:
                self.whatsapp_sender(file_path=path)
            return {"status": "success", "message": f"📸 Screenshot saved: {path}", "data": path}
        return {"status": "error", "message": "Screenshot failed."}

    def _handle_browser_task(self, params: dict, intent: dict) -> dict:
        subtype = intent.get("subtype", "")
        steps = intent.get("steps", [])

        if subtype == "leetcode":
            return self._run_leetcode(params, intent)
        elif subtype == "linkedin":
            return self._run_linkedin(params, intent)
        elif subtype == "movie_booking":
            return self._run_movie_booking(params, intent)
        else:
            # Generic browser navigation
            url = params.get("url", "")
            query = params.get("search_query", "")
            if url:
                browser = _get_browser()
                browser.goto(url)
                return {"status": "success", "message": f"✅ Opened: {url}"}
            elif query:
                browser = _get_browser()
                browser.goto(f"https://www.google.com/search?q={query}")
                return {"status": "success", "message": f"✅ Searched: {query}"}
            return {"status": "error", "message": "Browser task: no URL or subtype specified"}

    def _run_leetcode(self, params: dict, intent: dict) -> dict:
        global _leetcode_agent
        browser = _get_browser()
        if not _leetcode_agent:
            from jarvis.browser.tasks.leetcode_agent import LeetCodeAgent
            _leetcode_agent = LeetCodeAgent(browser=browser, intent_parser=self.parser)

        steps_text = " ".join(s.get("action", "") for s in intent.get("steps", []))
        if "daily" in steps_text.lower() or "today" in steps_text.lower():
            result = _leetcode_agent.solve_daily()
        else:
            problem = params.get("search_query", params.get("content", ""))
            result = _leetcode_agent.solve_by_name(problem) if problem else _leetcode_agent.solve_daily()

        # Auto-post to LinkedIn if steps include it
        steps_lower = steps_text.lower()
        if result.get("status") == "success" and ("linkedin" in steps_lower or "post" in steps_lower):
            linkedin_result = self._run_linkedin(
                params={"content": f"Solved LeetCode: {result.get('title', 'a problem')}. {result.get('data', '')}"},
                intent=intent
            )
            result["linkedin"] = linkedin_result.get("message", "")

        return result

    def _run_linkedin(self, params: dict, intent: dict) -> dict:
        global _linkedin_agent
        browser = _get_browser()
        if not _linkedin_agent:
            from jarvis.browser.tasks.linkedin_agent import LinkedInAgent
            _linkedin_agent = LinkedInAgent(browser=browser, intent_parser=self.parser)

        topic = params.get("content", params.get("search_query", "my latest work and learnings today"))
        return _linkedin_agent.create_post(topic=topic)

    def _run_movie_booking(self, params: dict, intent: dict) -> dict:
        global _movie_agent
        browser = _get_browser()
        if not _movie_agent:
            from jarvis.browser.tasks.movie_booking_agent import MovieBookingAgent
            _movie_agent = MovieBookingAgent(
                browser=browser,
                whatsapp_sender=self.whatsapp_sender
            )

        return _movie_agent.book_ticket(
            movie=params.get("movie", ""),
            date=params.get("date"),
            show_time=params.get("time"),
            city=params.get("city")
        )

    def _handle_memory_recall(self, params: dict, intent: dict) -> dict:
        query = params.get("content", params.get("search_query", intent.get("raw_input", "")))
        results = self.memory.recall(query)
        if results:
            items = "\n".join(f"• {r['key']}: {r['value']}" for r in results)
            return {"status": "success", "message": f"🧠 Memory recall:\n{items}"}
        return {"status": "success", "message": "No matching memories found."}

    def _handle_knowledge_query(self, params: dict, intent: dict) -> dict:
        name = params.get("content", params.get("contact", ""))
        if name:
            contact = self.graph.get_contact(name)
            if contact:
                return {"status": "success", "message": f"📊 {name}: {contact}"}
            related = self.graph.find_related(name)
            if related:
                items = "\n".join(f"• {r['relationship']} → {r['name']}" for r in related)
                return {"status": "success", "message": f"📊 Related to {name}:\n{items}"}
        return {"status": "success", "message": "No knowledge graph entries found."}

    def _handle_create_tool(self, params: dict, intent: dict) -> dict:
        tool_name = params.get("app", params.get("content", "new_tool"))
        description = params.get("content", intent.get("raw_input", ""))
        if not self.parser:
            return {"status": "error", "message": "AI engine not connected."}
        code = self.parser.generate_tool(tool_name, description)
        tools_dir = os.getenv("TOOLS_DIR", "./jarvis/tools/generated")
        os.makedirs(tools_dir, exist_ok=True)
        path = os.path.join(tools_dir, f"{tool_name.replace(' ', '_')}.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        return {"status": "success", "message": f"🔧 Tool created: {path}", "data": code[:300]}

    def _handle_chitchat(self, params: dict, intent: dict) -> dict:
        user_input = intent.get("raw_input", "")
        if self.parser:
            try:
                response = self.parser._call_llama(
                    f"User says: {user_input}\nRespond helpfully as JARVIS, an AI assistant. Keep it brief.",
                    temperature=0.7
                )
                return {"status": "success", "message": response.strip()}
            except Exception:
                pass
        return {"status": "success", "message": "I'm JARVIS. How can I help you?"}

    def _handle_unknown(self, params: dict, intent: dict) -> dict:
        raw = intent.get("raw_input", "")
        return {
            "status": "unknown",
            "message": f"⚠️ I couldn't understand: '{raw}'\n\nTry being more specific, e.g.:\n• 'open vscode'\n• 'what is my cpu usage'\n• 'create file test.py with hello world'"
        }
