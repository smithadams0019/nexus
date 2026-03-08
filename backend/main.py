"""Nexus backend — real-time voice + vision AI copilot powered by Gemini Live API."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from api.health import router as health_router
from api.sessions import router as sessions_router
from models.schemas import ContentType, ConversationEntry, ConversationRole, SessionStatus
from services.gemini_live import GeminiLiveService
from services.session import SessionManager

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nexus")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: setup and teardown."""
    app.state.session_manager = SessionManager()
    logger.info("Nexus backend started")
    yield
    logger.info("Nexus backend shutting down")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Nexus",
    description="Real-time voice + vision AI copilot",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(sessions_router)


# ---------------------------------------------------------------------------
# Gemini response receiver (background task per connection)
# ---------------------------------------------------------------------------

async def _gemini_response_receiver(
    ws: WebSocket,
    gemini: GeminiLiveService,
    session_id: str,
    manager: SessionManager,
) -> None:
    """Read from the Gemini stream and forward messages to the browser WebSocket."""
    text_buffer: list[str] = []
    try:
        async for msg in gemini.receive_responses():
            msg_type = msg["type"]

            if msg_type == "audio":
                manager.update_activity(session_id, SessionStatus.responding)
                await ws.send_json({"type": "audio", "data": msg["data"]})

            elif msg_type == "text":
                manager.update_activity(session_id, SessionStatus.responding)
                text_buffer.append(msg["data"])
                await ws.send_json({"type": "text", "data": msg["data"]})

            elif msg_type == "turn_complete":
                # Flush accumulated text as a conversation entry
                if text_buffer:
                    full_text = "".join(text_buffer)
                    manager.add_conversation_entry(
                        session_id,
                        ConversationEntry(
                            role=ConversationRole.assistant,
                            content_type=ContentType.text,
                            content=full_text,
                        ),
                    )
                    text_buffer.clear()

                manager.update_activity(session_id, SessionStatus.idle)
                await ws.send_json({"type": "turn_complete"})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected during response receive for session %s", session_id)
    except Exception:
        logger.exception("Error in Gemini response receiver for session %s", session_id)


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(ws: WebSocket, session_id: str) -> None:
    """Main WebSocket handler: bridges the browser and Gemini Live API."""
    await ws.accept()
    manager: SessionManager = app.state.session_manager
    manager.create_session(session_id)

    gemini = GeminiLiveService()
    receiver_task: asyncio.Task | None = None

    try:
        # Open Gemini Live session
        await gemini.connect()
        logger.info("Session %s: Gemini connected", session_id)

        # Start background receiver
        receiver_task = asyncio.create_task(
            _gemini_response_receiver(ws, gemini, session_id, manager)
        )

        # Main loop: browser -> Gemini
        while True:
            raw = await ws.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Session %s: received non-JSON message", session_id)
                continue

            msg_type = message.get("type", "")
            data = message.get("data", "")

            if msg_type == "frame":
                manager.update_activity(session_id, SessionStatus.listening)
                frame_bytes = base64.b64decode(data)
                await gemini.send_frame(frame_bytes)

            elif msg_type == "audio":
                manager.update_activity(session_id, SessionStatus.listening)
                audio_bytes = base64.b64decode(data)
                await gemini.send_audio(audio_bytes)

            elif msg_type == "text":
                manager.update_activity(session_id, SessionStatus.thinking)
                manager.add_conversation_entry(
                    session_id,
                    ConversationEntry(
                        role=ConversationRole.user,
                        content_type=ContentType.text,
                        content=data,
                    ),
                )
                await gemini.send_text(data)

            elif msg_type == "end_of_turn":
                manager.update_activity(session_id, SessionStatus.thinking)

            else:
                logger.warning("Session %s: unknown message type '%s'", session_id, msg_type)

    except WebSocketDisconnect:
        logger.info("Session %s: browser disconnected", session_id)
    except Exception:
        logger.exception("Session %s: unhandled error", session_id)
    finally:
        # Cleanup
        if receiver_task is not None:
            receiver_task.cancel()
            try:
                await receiver_task
            except (asyncio.CancelledError, Exception):
                pass

        await gemini.close()
        manager.update_activity(session_id, SessionStatus.idle)
        logger.info("Session %s: cleaned up", session_id)
