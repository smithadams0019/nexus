"""REST endpoints for session data (conversation, insights, alerts)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from models.schemas import AlertMessage, ConversationEntry, InsightCard, SessionState
from services.session import SessionManager

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _get_session_manager(request: Request) -> SessionManager:
    """Dependency that extracts the SessionManager from app state."""
    return request.app.state.session_manager


# ------------------------------------------------------------------
# Session state
# ------------------------------------------------------------------

@router.get("/{session_id}", response_model=SessionState)
async def get_session(
    session_id: str,
    manager: SessionManager = Depends(_get_session_manager),
) -> SessionState:
    """Return the current state of a session."""
    state = manager.get_session(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return state


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    manager: SessionManager = Depends(_get_session_manager),
) -> dict[str, str]:
    """Delete a session and all associated data."""
    if not manager.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": session_id}


# ------------------------------------------------------------------
# Conversation history
# ------------------------------------------------------------------

@router.get("/{session_id}/conversation", response_model=list[ConversationEntry])
async def get_conversation(
    session_id: str,
    manager: SessionManager = Depends(_get_session_manager),
) -> list[ConversationEntry]:
    """Return the full conversation history for a session."""
    if manager.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return manager.get_conversation_history(session_id)


# ------------------------------------------------------------------
# Insights
# ------------------------------------------------------------------

@router.get("/{session_id}/insights", response_model=list[InsightCard])
async def get_insights(
    session_id: str,
    manager: SessionManager = Depends(_get_session_manager),
) -> list[InsightCard]:
    """Return all insight cards for a session."""
    if manager.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return manager.get_insights(session_id)


# ------------------------------------------------------------------
# Alerts
# ------------------------------------------------------------------

@router.get("/{session_id}/alerts", response_model=list[AlertMessage])
async def get_alerts(
    session_id: str,
    manager: SessionManager = Depends(_get_session_manager),
) -> list[AlertMessage]:
    """Return all alerts for a session."""
    if manager.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return manager.get_alerts(session_id)


@router.post("/{session_id}/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    session_id: str,
    alert_id: str,
    manager: SessionManager = Depends(_get_session_manager),
) -> dict[str, str]:
    """Mark an alert as acknowledged."""
    if manager.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not manager.acknowledge_alert(session_id, alert_id):
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "acknowledged", "alert_id": alert_id}
