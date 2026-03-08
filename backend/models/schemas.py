"""Pydantic models for the Nexus real-time voice+vision AI copilot."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# WebSocket transport
# ---------------------------------------------------------------------------

class WebSocketMessage(BaseModel):
    """Generic envelope for all WebSocket messages."""

    type: str
    data: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

class SessionStatus(str, Enum):
    idle = "idle"
    listening = "listening"
    thinking = "thinking"
    responding = "responding"


class SessionState(BaseModel):
    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    status: SessionStatus = SessionStatus.idle
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------

class ContentType(str, Enum):
    text = "text"
    audio = "audio"
    image = "image"


class ConversationRole(str, Enum):
    user = "user"
    assistant = "assistant"


class ConversationEntry(BaseModel):
    role: ConversationRole
    content_type: ContentType
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Insight cards
# ---------------------------------------------------------------------------

class InsightCategory(str, Enum):
    anomaly = "anomaly"
    insight = "insight"
    suggestion = "suggestion"
    warning = "warning"


class InsightCard(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    title: str
    content: str
    category: InsightCategory
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_frame: Optional[str] = None


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

class AlertSeverity(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class AlertMessage(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    severity: AlertSeverity
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

class MemoryType(str, Enum):
    episodic = "episodic"
    semantic = "semantic"


class MemoryEntry(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    type: MemoryType
    content: str
    context: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ttl: Optional[int] = None


# ---------------------------------------------------------------------------
# Desktop action control
# ---------------------------------------------------------------------------

class ActionType(str, Enum):
    click = "click"
    double_click = "double_click"
    type_text = "type"
    hotkey = "hotkey"
    scroll = "scroll"
    move = "move"
    screenshot = "screenshot"
    wait = "wait"
    open_url = "open_url"
    open_app = "open_app"


class DesktopAction(BaseModel):
    type: str
    x: int | None = None
    y: int | None = None
    button: str = "left"
    text: str | None = None
    keys: list[str] | None = None
    amount: int | None = None
    seconds: float | None = None
    url: str | None = None
    name: str | None = None
