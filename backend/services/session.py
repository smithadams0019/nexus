"""In-memory session manager for Nexus."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from models.schemas import (
    AlertMessage,
    ConversationEntry,
    InsightCard,
    SessionState,
    SessionStatus,
)

logger = logging.getLogger("nexus.session")


class SessionManager:
    """Manages session state, conversation history, insights, and alerts in memory."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._conversation_history: dict[str, list[ConversationEntry]] = {}
        self._insights: dict[str, list[InsightCard]] = {}
        self._alerts: dict[str, list[AlertMessage]] = {}

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def create_session(self, session_id: str) -> SessionState:
        """Create and store a new session."""
        now = datetime.now(timezone.utc)
        state = SessionState(
            session_id=session_id,
            status=SessionStatus.idle,
            created_at=now,
            last_active=now,
        )
        self._sessions[session_id] = state
        self._conversation_history[session_id] = []
        self._insights[session_id] = []
        self._alerts[session_id] = []
        logger.info("Created session %s", session_id)
        return state

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Return the session state or None if not found."""
        return self._sessions.get(session_id)

    def update_activity(self, session_id: str, status: Optional[SessionStatus] = None) -> Optional[SessionState]:
        """Touch the last_active timestamp and optionally update the status."""
        state = self._sessions.get(session_id)
        if state is None:
            return None
        state.last_active = datetime.now(timezone.utc)
        if status is not None:
            state.status = status
        return state

    def delete_session(self, session_id: str) -> bool:
        """Remove a session and all associated data. Returns True if it existed."""
        existed = session_id in self._sessions
        self._sessions.pop(session_id, None)
        self._conversation_history.pop(session_id, None)
        self._insights.pop(session_id, None)
        self._alerts.pop(session_id, None)
        if existed:
            logger.info("Deleted session %s", session_id)
        return existed

    # ------------------------------------------------------------------
    # Conversation history
    # ------------------------------------------------------------------

    def add_conversation_entry(self, session_id: str, entry: ConversationEntry) -> None:
        """Append a conversation entry to the session history."""
        history = self._conversation_history.get(session_id)
        if history is None:
            logger.warning("add_conversation_entry called for unknown session %s", session_id)
            self._conversation_history[session_id] = []
            history = self._conversation_history[session_id]
        history.append(entry)

    def get_conversation_history(self, session_id: str) -> list[ConversationEntry]:
        """Return the full conversation history for a session."""
        return list(self._conversation_history.get(session_id, []))

    # ------------------------------------------------------------------
    # Insights
    # ------------------------------------------------------------------

    def add_insight(self, session_id: str, insight: InsightCard) -> None:
        """Add an insight card to the session."""
        bucket = self._insights.get(session_id)
        if bucket is None:
            self._insights[session_id] = []
            bucket = self._insights[session_id]
        bucket.append(insight)
        logger.info("Added insight %s to session %s", insight.id, session_id)

    def get_insights(self, session_id: str) -> list[InsightCard]:
        """Return all insight cards for a session."""
        return list(self._insights.get(session_id, []))

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------

    def add_alert(self, session_id: str, alert: AlertMessage) -> None:
        """Add an alert to the session."""
        bucket = self._alerts.get(session_id)
        if bucket is None:
            self._alerts[session_id] = []
            bucket = self._alerts[session_id]
        bucket.append(alert)
        logger.info("Added alert %s (severity=%s) to session %s", alert.id, alert.severity, session_id)

    def get_alerts(self, session_id: str) -> list[AlertMessage]:
        """Return all alerts for a session."""
        return list(self._alerts.get(session_id, []))

    def acknowledge_alert(self, session_id: str, alert_id: str) -> bool:
        """Mark an alert as acknowledged. Returns True if the alert was found."""
        for alert in self._alerts.get(session_id, []):
            if alert.id == alert_id:
                alert.acknowledged = True
                logger.info("Acknowledged alert %s in session %s", alert_id, session_id)
                return True
        return False
