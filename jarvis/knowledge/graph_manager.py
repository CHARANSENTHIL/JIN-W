"""
JARVIS Knowledge Graph — Neo4j graph database for entity relationship reasoning.
Stores contacts, projects, preferences, and their relationships.
"""
import os
from dotenv import load_dotenv, find_dotenv
from pathlib import Path

# Explicitly find the .env at project root regardless of working directory
_env_path = find_dotenv(usecwd=True) or str(Path(__file__).resolve().parents[2] / ".env")
load_dotenv(_env_path, override=True)
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable



class GraphManager:
    def __init__(self):
        self.driver = None
        self._connected = False
        self._connect()

    def _connect(self):
        """Connect to Neo4j database."""
        uri      = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user     = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        self.db  = os.getenv("DATABASE", "neo4j")
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            self._connected = True
            self._init_schema()
            print(f"[KnowledgeGraph] ✅ Connected to Neo4j (db: {self.db})")
        except ServiceUnavailable:
            print("[KnowledgeGraph] ⚠️ Neo4j not available — knowledge graph disabled")
            self._connected = False
        except Exception as e:
            print(f"[KnowledgeGraph] Connection failed: {e}")
            self._connected = False

    def _init_schema(self):
        """Create indexes for common node types."""
        with self.driver.session(database=self.db) as session:
            session.run("CREATE CONSTRAINT person_name IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE")
            session.run("CREATE CONSTRAINT project_name IF NOT EXISTS FOR (p:Project) REQUIRE p.name IS UNIQUE")
            session.run("CREATE INDEX app_name IF NOT EXISTS FOR (a:App) ON (a.name)")

    def _run(self, query: str, params: dict = None):
        """Execute a Cypher query."""
        if not self._connected:
            return []
        with self.driver.session(database=self.db) as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]

    # ─── Entity Management ─────────────────────────────────────

    def add_person(self, name: str, platform: str = None, contact_id: str = None, notes: str = None):
        """Add or update a person node."""
        self._run(
            """
            MERGE (p:Person {name: $name})
            SET p.platform = $platform,
                p.contact_id = $contact_id,
                p.notes = $notes
            RETURN p
            """,
            {"name": name, "platform": platform, "contact_id": contact_id, "notes": notes}
        )

    def add_project(self, name: str, language: str = None, path: str = None, description: str = None):
        """Add or update a project node."""
        self._run(
            """
            MERGE (p:Project {name: $name})
            SET p.language = $language,
                p.path = $path,
                p.description = $description
            RETURN p
            """,
            {"name": name, "language": language, "path": path, "description": description}
        )

    def add_app(self, name: str, exe_path: str = None):
        """Add or update an application node."""
        self._run(
            """
            MERGE (a:App {name: $name})
            SET a.exe_path = $exe_path
            RETURN a
            """,
            {"name": name, "exe_path": exe_path}
        )

    def add_preference(self, key: str, value: str):
        """Add or update a user preference node."""
        self._run(
            """
            MERGE (u:User {name: 'JARVIS_User'})
            MERGE (p:Preference {key: $key})
            SET p.value = $value
            MERGE (u)-[:PREFERS]->(p)
            """,
            {"key": key, "value": value}
        )

    # ─── Relationship Management ────────────────────────────────

    def add_relationship(self, from_label: str, from_name: str,
                          rel_type: str,
                          to_label: str, to_name: str,
                          properties: dict = None):
        """
        Add a relationship between two nodes.
        Example: add_relationship('Person','Mom','CONTACTS_VIA','Platform','WhatsApp')
        """
        props = properties or {}
        self._run(
            f"""
            MERGE (a:{from_label} {{name: $from_name}})
            MERGE (b:{to_label} {{name: $to_name}})
            MERGE (a)-[r:{rel_type}]->(b)
            SET r += $props
            """,
            {"from_name": from_name, "to_name": to_name, "props": props}
        )

    def link_user_to_person(self, person_name: str, relationship: str = "KNOWS"):
        """Link the main user to a person (e.g., User KNOWS Mom)."""
        self._run(
            f"""
            MERGE (u:User {{name: 'JARVIS_User'}})
            MERGE (p:Person {{name: $name}})
            MERGE (u)-[:{relationship}]->(p)
            """,
            {"name": person_name}
        )

    def link_person_to_project(self, person_name: str, project_name: str):
        """Record that a person is associated with a project."""
        self._run(
            """
            MERGE (p:Person {name: $person})
            MERGE (pr:Project {name: $project})
            MERGE (p)-[:WORKS_ON]->(pr)
            """,
            {"person": person_name, "project": project_name}
        )

    def record_task(self, task_description: str, intent: str, outcome: str):
        """Record a completed task as a Task node linked to User."""
        self._run(
            """
            MERGE (u:User {name: 'JARVIS_User'})
            CREATE (t:Task {description: $desc, intent: $intent, outcome: $outcome, timestamp: datetime()})
            CREATE (u)-[:PERFORMED]->(t)
            """,
            {"desc": task_description, "intent": intent, "outcome": outcome}
        )

    # ─── Query Methods ──────────────────────────────────────────

    def get_contact(self, name: str) -> dict | None:
        """Look up a contact by name."""
        results = self._run(
            """
            MATCH (p:Person {name: $name})
            RETURN p.name as name, p.platform as platform, p.contact_id as contact_id, p.notes as notes
            """,
            {"name": name}
        )
        return results[0] if results else None

    def get_preference(self, key: str) -> str | None:
        """Look up a user preference."""
        results = self._run(
            "MATCH (p:Preference {key: $key}) RETURN p.value as value",
            {"key": key}
        )
        return results[0]["value"] if results else None

    def get_all_contacts(self) -> list[dict]:
        """Return all stored contacts."""
        return self._run(
            "MATCH (p:Person) RETURN p.name as name, p.platform as platform, p.contact_id as contact_id"
        )

    def get_all_projects(self) -> list[dict]:
        """Return all stored projects."""
        return self._run(
            "MATCH (p:Project) RETURN p.name as name, p.language as language, p.path as path"
        )

    def get_recent_tasks(self, n: int = 5) -> list[dict]:
        """Return the n most recent tasks."""
        return self._run(
            """
            MATCH (u:User {name: 'JARVIS_User'})-[:PERFORMED]->(t:Task)
            RETURN t.description as description, t.intent as intent, t.outcome as outcome, t.timestamp as time
            ORDER BY t.timestamp DESC
            LIMIT $n
            """,
            {"n": n}
        )

    def find_related(self, name: str) -> list[dict]:
        """
        Find all nodes related to a given entity.
        Useful for context queries like 'send message to my project team'.
        """
        return self._run(
            """
            MATCH (n {name: $name})-[r]-(related)
            RETURN type(r) as relationship, labels(related)[0] as type, related.name as name
            """,
            {"name": name}
        )

    def query_cypher(self, cypher: str, params: dict = None) -> list[dict]:
        """Run a raw Cypher query (for advanced use)."""
        return self._run(cypher, params)

    def close(self):
        if self.driver:
            self.driver.close()
