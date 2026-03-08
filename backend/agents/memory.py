"""MemoryAgent — remembers context across conversations with optional Firestore persistence."""

import logging
import os
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A single memory record."""

    content: str
    memory_type: str
    context: str
    timestamp: float
    ttl: int | None = None  # seconds until expiry, None = never expires


@dataclass
class _SessionStore:
    """In-memory storage for a single session."""

    memories: list[MemoryEntry] = field(default_factory=list)


class MemoryAgent:
    """Stores and retrieves conversational memory per session.

    Uses in-memory storage by default. If the ``GOOGLE_CLOUD_PROJECT``
    environment variable is set, memories are also persisted to a Firestore
    collection named ``nexus_memories``.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, _SessionStore] = {}
        self._firestore_client = None
        self._firestore_collection = "nexus_memories"

        gcp_project = os.getenv("GOOGLE_CLOUD_PROJECT")
        if gcp_project:
            try:
                from google.cloud import firestore  # type: ignore[import-untyped]

                self._firestore_client = firestore.AsyncClient(project=gcp_project)
                logger.info(
                    "MemoryAgent: Firestore persistence enabled (project=%s)",
                    gcp_project,
                )
            except Exception as exc:
                logger.warning(
                    "MemoryAgent: Firestore import/init failed, using in-memory only: %s",
                    exc,
                )

    def _get_session(self, session_id: str) -> _SessionStore:
        if session_id not in self._sessions:
            self._sessions[session_id] = _SessionStore()
        return self._sessions[session_id]

    def _prune_expired(self, store: _SessionStore) -> None:
        """Remove expired memories from the store."""
        now = time.time()
        store.memories = [
            m
            for m in store.memories
            if m.ttl is None or (m.timestamp + m.ttl) > now
        ]

    async def store(
        self,
        session_id: str,
        content: str,
        memory_type: str = "episodic",
        context: str = "",
        ttl: int | None = None,
    ) -> None:
        """Store a memory entry.

        Args:
            session_id: Unique session identifier.
            content: The text content to remember.
            memory_type: Category of memory (e.g. "episodic", "semantic", "procedural").
            context: Optional context or tags for retrieval.
            ttl: Time-to-live in seconds. None means the memory never expires.
        """
        entry = MemoryEntry(
            content=content,
            memory_type=memory_type,
            context=context,
            timestamp=time.time(),
            ttl=ttl,
        )

        store = self._get_session(session_id)
        store.memories.append(entry)
        logger.debug(
            "MemoryAgent: stored memory for session %s (type=%s, ttl=%s)",
            session_id,
            memory_type,
            ttl,
        )

        # Persist to Firestore if available
        if self._firestore_client is not None:
            try:
                doc_data = {
                    "session_id": session_id,
                    "content": content,
                    "memory_type": memory_type,
                    "context": context,
                    "timestamp": entry.timestamp,
                    "ttl": ttl,
                }
                await self._firestore_client.collection(
                    self._firestore_collection
                ).add(doc_data)
            except Exception as exc:
                logger.error(
                    "MemoryAgent: Firestore write failed: %s", exc, exc_info=True
                )

    async def recall(
        self, session_id: str, query: str, limit: int = 5
    ) -> list[dict]:
        """Recall memories matching a keyword query.

        Uses simple keyword matching — each word in the query is checked against
        stored memory content and context. Results are scored by keyword overlap
        and sorted by recency among matches.

        Args:
            session_id: Unique session identifier.
            query: Search query string.
            limit: Maximum number of results to return.

        Returns:
            List of dicts with keys: content, memory_type, context, timestamp.
        """
        store = self._get_session(session_id)
        self._prune_expired(store)

        query_terms = set(query.lower().split())
        if not query_terms:
            return []

        scored: list[tuple[float, MemoryEntry]] = []
        for entry in store.memories:
            searchable = f"{entry.content} {entry.context}".lower()
            matches = sum(1 for term in query_terms if term in searchable)
            if matches > 0:
                # Score: keyword overlap ratio + recency bonus (normalized timestamp)
                score = matches / len(query_terms)
                scored.append((score, entry))

        # Sort by score descending, then by timestamp descending (most recent first)
        scored.sort(key=lambda x: (x[0], x[1].timestamp), reverse=True)

        results: list[dict] = []
        for _, entry in scored[:limit]:
            results.append({
                "content": entry.content,
                "memory_type": entry.memory_type,
                "context": entry.context,
                "timestamp": entry.timestamp,
            })

        return results

    async def get_session_context(self, session_id: str) -> str:
        """Return a formatted string of recent memories for prompt injection.

        Args:
            session_id: Unique session identifier.

        Returns:
            A formatted string summarizing recent session memories, or empty string.
        """
        store = self._get_session(session_id)
        self._prune_expired(store)

        if not store.memories:
            return ""

        # Take the 10 most recent memories
        recent = sorted(store.memories, key=lambda m: m.timestamp, reverse=True)[:10]

        lines: list[str] = ["[Session Memory Context]"]
        for entry in reversed(recent):  # chronological order
            type_tag = f"[{entry.memory_type}]" if entry.memory_type else ""
            lines.append(f"- {type_tag} {entry.content}")

        return "\n".join(lines)

    async def clear_session(self, session_id: str) -> None:
        """Clear all memories for a session.

        Args:
            session_id: Unique session identifier.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("MemoryAgent: cleared session %s", session_id)

        # Clear from Firestore if available
        if self._firestore_client is not None:
            try:
                collection_ref = self._firestore_client.collection(
                    self._firestore_collection
                )
                query = collection_ref.where("session_id", "==", session_id)
                docs = query.stream()
                async for doc in docs:
                    await doc.reference.delete()
                logger.info(
                    "MemoryAgent: cleared Firestore entries for session %s",
                    session_id,
                )
            except Exception as exc:
                logger.error(
                    "MemoryAgent: Firestore clear failed: %s", exc, exc_info=True
                )
