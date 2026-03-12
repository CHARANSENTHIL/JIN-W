"""
JARVIS Intent Parser — uses LLaMA via Ollama to parse natural language commands.
"""
import json
import re
import os
import time
import requests
from dotenv import load_dotenv
from jarvis.ai_engine.prompt_templates import (
    SYSTEM_PROMPT,
    MULTILINE_AGGREGATOR_PROMPT,
    SELF_HEAL_PROMPT,
    CODE_GENERATION_PROMPT,
    TOOL_CREATION_PROMPT,
    LINKEDIN_POST_PROMPT,
)

load_dotenv()


class IntentParser:
    def __init__(self):
        self.model = os.getenv("OLLAMA_MODEL", "llama3")
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.multiline_timeout = float(os.getenv("MULTILINE_TIMEOUT", "2.5"))
        self._pending_lines = []
        self._last_input_time = None

    def _call_llama(self, prompt: str, system: str = None, temperature: float = 0.1) -> str:
        """Call Ollama LLaMA model and return raw response text."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 1024,
            }
        }
        if system:
            payload["system"] = system

        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                "Cannot connect to Ollama. Make sure it's running: 'ollama serve'"
            )
        except Exception as e:
            raise RuntimeError(f"LLaMA call failed: {e}")

    def _extract_json(self, text: str) -> dict:
        """Robustly extract JSON from LLaMA output."""
        # Try direct parse first
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON block from markdown code fences
        patterns = [
            r"```json\s*([\s\S]*?)\s*```",
            r"```\s*([\s\S]*?)\s*```",
            r"(\{[\s\S]*\})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue

        # Return error intent if parsing fails
        return {
            "raw_input": text,
            "intent": "unknown",
            "subtype": None,
            "parameters": {},
            "steps": [],
            "use_browser": False,
            "agent_needed": "none",
            "confidence": 0.0,
            "parse_error": "Could not extract JSON from LLaMA response"
        }

    def parse(self, user_input: str) -> dict:
        """
        Parse a natural language command into a structured intent dict.
        Handles single-line, multiline, typos, and slang.
        """
        # Normalize input — replace literal \n with real newlines
        user_input = user_input.replace("\\n", "\n").strip()
        lines = [l.strip() for l in user_input.splitlines() if l.strip()]

        # Build the prompt
        if len(lines) > 1:
            # Multiline batch
            formatted = MULTILINE_AGGREGATOR_PROMPT.format(
                command_block="\n".join(f"{i+1}. {l}" for i, l in enumerate(lines))
            )
            prompt = formatted
        else:
            prompt = f'User command: "{user_input}"'

        raw = self._call_llama(prompt, system=SYSTEM_PROMPT)
        result = self._extract_json(raw)
        result["raw_input"] = user_input
        return result

    def add_line(self, line: str) -> dict | None:
        """
        Add a line to the pending buffer.
        Returns parsed intent when multiline_timeout elapses, else None.
        Used by WhatsApp Web interface for multiline message collection.
        """
        self._pending_lines.append(line.strip())
        self._last_input_time = time.time()
        return None  # Caller polls flush()

    def flush(self) -> dict | None:
        """
        If multiline_timeout has elapsed since last input, parse and clear buffer.
        """
        if not self._pending_lines:
            return None
        if self._last_input_time is None:
            return None
        elapsed = time.time() - self._last_input_time
        if elapsed >= self.multiline_timeout:
            combined = "\n".join(self._pending_lines)
            self._pending_lines = []
            self._last_input_time = None
            return self.parse(combined)
        return None

    def generate_code(self, language: str, description: str) -> str:
        """Generate code using LLaMA."""
        prompt = CODE_GENERATION_PROMPT.format(
            language=language,
            description=description
        )
        return self._call_llama(prompt, temperature=0.3)

    def generate_tool(self, tool_name: str, description: str) -> str:
        """Generate a Python tool script using LLaMA."""
        prompt = TOOL_CREATION_PROMPT.format(
            tool_name=tool_name,
            description=description
        )
        return self._call_llama(prompt, temperature=0.3)

    def generate_linkedin_post(self, topic: str) -> str:
        """Generate a LinkedIn post using LLaMA."""
        prompt = LINKEDIN_POST_PROMPT.format(topic=topic)
        return self._call_llama(prompt, temperature=0.7)

    def suggest_fix(self, task_description: str, error_message: str) -> dict:
        """Ask LLaMA to suggest a fix for a failed task."""
        prompt = SELF_HEAL_PROMPT.format(
            task_description=task_description,
            error_message=error_message
        )
        raw = self._call_llama(prompt, temperature=0.2)
        return self._extract_json(raw)
