"""
JARVIS Memory Manager — ChromaDB vector database for persistent memory.
Stores user preferences, task history, and code solutions.
"""
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings

load_dotenv()

CHROMA_PATH = os.path.abspath(os.getenv("CHROMA_DB_PATH", "./jarvis/.chromadb"))


class MemoryManager:
    """
    Three collections:
    - user_memory:  contacts, preferences, personal facts
    - task_memory:  executed tasks and their outcomes
    - code_memory:  code snippets and solutions
    """

    def __init__(self):
        os.makedirs(CHROMA_PATH, exist_ok=True)
        self.client = chromadb.PersistentClient(path=CHROMA_PATH)
        self._collections = {}

    def _get_collection(self, name: str):
        """Get or create a ChromaDB collection."""
        if name not in self._collections:
            self._collections[name] = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collections[name]

    def remember(self, key: str, value: str | dict, collection: str = "user_memory", metadata: dict = None) -> bool:
        """
        Store a memory entry. Uses the key as the document ID (upserts).
        """
        try:
            col = self._get_collection(collection)
            if isinstance(value, dict):
                doc = json.dumps(value)
            else:
                doc = str(value)

            meta = {
                "key": key,
                "timestamp": datetime.now().isoformat(),
                "collection": collection,
            }
            if metadata:
                meta.update(metadata)

            col.upsert(
                ids=[key],
                documents=[doc],
                metadatas=[meta]
            )
            return True
        except Exception as e:
            print(f"[Memory] Failed to store '{key}': {e}")
            return False

    def recall(self, query: str, collection: str = "user_memory", n: int = 3) -> list[dict]:
        """
        Semantic search — return top-n most relevant memories.
        """
        try:
            col = self._get_collection(collection)
            results = col.query(
                query_texts=[query],
                n_results=min(n, col.count() or 1)
            )
            memories = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results.get("distances") else None
                    memories.append({
                        "key": meta.get("key", ""),
                        "value": doc,
                        "timestamp": meta.get("timestamp", ""),
                        "relevance": round(1 - (distance or 0), 3)
                    })
            return memories
        except Exception as e:
            print(f"[Memory] Recall failed for '{query}': {e}")
            return []

    def recall_exact(self, key: str, collection: str = "user_memory") -> str | None:
        """Retrieve a memory by exact key."""
        try:
            col = self._get_collection(collection)
            result = col.get(ids=[key])
            if result["documents"]:
                return result["documents"][0]
        except Exception:
            pass
        return None

    def forget(self, key: str, collection: str = "user_memory") -> bool:
        """Delete a specific memory by key."""
        try:
            col = self._get_collection(collection)
            col.delete(ids=[key])
            return True
        except Exception as e:
            print(f"[Memory] Failed to forget '{key}': {e}")
            return False

    def log_task(self, command: str, intent: dict, result: dict):
        """
        Automatically log every executed task for future learning.
        """
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.remember(
            key=task_id,
            value={
                "command": command,
                "intent": intent.get("intent"),
                "status": result.get("status"),
                "summary": result.get("message", "")[:200]
            },
            collection="task_memory",
            metadata={"intent": intent.get("intent", "unknown")}
        )

    def log_code(self, description: str, language: str, code: str, path: str = ""):
        """Store a code solution in code memory."""
        code_id = f"code_{description[:30].replace(' ', '_').lower()}"
        self.remember(
            key=code_id,
            value={"description": description, "language": language, "code": code[:2000], "path": path},
            collection="code_memory",
            metadata={"language": language}
        )

    def remember_contact(self, name: str, platform: str, contact_id: str):
        """Store contact information."""
        self.remember(
            key=f"contact_{name.lower()}",
            value={"name": name, "platform": platform, "id": contact_id},
            collection="user_memory",
            metadata={"type": "contact"}
        )

    def remember_preference(self, key: str, value: str):
        """Store a user preference."""
        self.remember(
            key=f"pref_{key.lower()}",
            value=value,
            collection="user_memory",
            metadata={"type": "preference"}
        )

    def get_recent_tasks(self, n: int = 5) -> list[dict]:
        """Return the most recently logged tasks."""
        try:
            col = self._get_collection("task_memory")
            results = col.get()
            items = []
            for i, doc in enumerate(results.get("documents", [])):
                meta = results["metadatas"][i] if results.get("metadatas") else {}
                try:
                    data = json.loads(doc)
                except Exception:
                    data = {"raw": doc}
                items.append({**data, "timestamp": meta.get("timestamp", "")})
            # Sort by timestamp descending
            items = sorted(items, key=lambda x: x.get("timestamp", ""), reverse=True)
            return items[:n]
        except Exception as e:
            print(f"[Memory] Failed to get recent tasks: {e}")
            return []
