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

from agents.analyst import AnalystAgent
from agents.alert import AlertAgent
from agents.memory import MemoryAgent
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
    app.state.analyst = AnalystAgent()
    app.state.alert_agent = AlertAgent()
    app.state.memory = MemoryAgent()
    logger.info("Nexus backend started (agents initialized)")
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
    memory: MemoryAgent,
) -> None:
    """Read from the Gemini stream and forward messages to the browser WebSocket."""
    text_buffer: list[str] = []
    try:
        logger.info("Session %s: receiver started, waiting for Gemini responses", session_id)
        async for msg in gemini.receive_responses():
            msg_type = msg["type"]
            logger.info("Session %s: received %s from Gemini", session_id, msg_type)

            if msg_type == "audio":
                manager.update_activity(session_id, SessionStatus.responding)
                await ws.send_json({"type": "audio", "data": msg["data"]})

            elif msg_type == "text":
                manager.update_activity(session_id, SessionStatus.responding)
                text_buffer.append(msg["data"])
                await ws.send_json({"type": "text", "data": msg["data"]})

            elif msg_type == "turn_complete":
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
                    # Store assistant response in memory
                    try:
                        await memory.store(
                            session_id,
                            full_text,
                            memory_type="episodic",
                            context="assistant_response",
                        )
                    except Exception:
                        logger.exception("Session %s: failed to store assistant response in memory", session_id)
                    text_buffer.clear()

                manager.update_activity(session_id, SessionStatus.idle)
                await ws.send_json({"type": "turn_complete"})

        logger.warning("Session %s: Gemini receive loop ended naturally (session closed?)", session_id)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected during response receive for session %s", session_id)
    except Exception:
        logger.exception("Error in Gemini response receiver for session %s", session_id)


# ---------------------------------------------------------------------------
# Agent background processor (runs alongside the Gemini receiver)
# ---------------------------------------------------------------------------

async def _agent_processor(
    ws: WebSocket,
    session_id: str,
    last_frame: list[str | None],
    analyst: AnalystAgent,
    alert_agent: AlertAgent,
    memory: MemoryAgent,
) -> None:
    """Periodically run agents on the latest frame. Never crashes the session."""
    try:
        while True:
            await asyncio.sleep(10)

            frame_b64 = last_frame[0]
            if frame_b64 is None:
                continue

            # --- Alert check ---
            try:
                alert_result = await alert_agent.check_frame(frame_b64)
                if alert_result is not None:
                    await ws.send_json({
                        "type": "alert",
                        "severity": alert_result["severity"],
                        "message": alert_result["message"],
                    })
                    logger.info("Session %s: alert sent (%s)", session_id, alert_result["severity"])
            except Exception:
                logger.exception("Session %s: agent_processor alert check failed", session_id)

            # --- Insight card ---
            try:
                conversation_ctx = await memory.get_session_context(session_id)
                insight = await analyst.generate_insight_card(frame_b64, conversation_ctx)
                if insight is not None:
                    await ws.send_json({
                        "type": "insight",
                        "title": insight["title"],
                        "content": insight["content"],
                        "category": insight["category"],
                    })
                    logger.info("Session %s: insight sent (%s)", session_id, insight["category"])
            except Exception:
                logger.exception("Session %s: agent_processor insight generation failed", session_id)

    except asyncio.CancelledError:
        logger.info("Session %s: agent_processor cancelled", session_id)
    except Exception:
        logger.exception("Session %s: agent_processor unexpected error (non-fatal)", session_id)


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(ws: WebSocket, session_id: str) -> None:
    """Main WebSocket handler: bridges the browser and Gemini Live API."""
    await ws.accept()
    manager: SessionManager = app.state.session_manager
    memory: MemoryAgent = app.state.memory
    analyst: AnalystAgent = app.state.analyst
    alert_agent: AlertAgent = app.state.alert_agent
    manager.create_session(session_id)

    gemini = GeminiLiveService()
    receiver_task: asyncio.Task | None = None
    agent_task: asyncio.Task | None = None

    # Shared mutable container for the latest frame (base64 string)
    last_frame: list[str | None] = [None]

    try:
        # Open Gemini Live session
        await gemini.connect()
        logger.info("Session %s: Gemini connected", session_id)

        # Start background receiver
        receiver_task = asyncio.create_task(
            _gemini_response_receiver(ws, gemini, session_id, manager, memory)
        )

        # Start background agent processor
        agent_task = asyncio.create_task(
            _agent_processor(ws, session_id, last_frame, analyst, alert_agent, memory)
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

            try:
                if msg_type == "frame":
                    manager.update_activity(session_id, SessionStatus.listening)
                    # Store latest frame for agent processor
                    last_frame[0] = data
                    frame_bytes = base64.b64decode(data)
                    await gemini.send_frame(frame_bytes)

                elif msg_type == "audio":
                    audio_bytes = base64.b64decode(data)
                    logger.debug("Session %s: got audio chunk %d bytes", session_id, len(audio_bytes))
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
                    # Store user message in memory
                    try:
                        await memory.store(
                            session_id,
                            data,
                            memory_type="episodic",
                            context="user_message",
                        )
                    except Exception:
                        logger.exception("Session %s: failed to store user message in memory", session_id)
                    await gemini.send_text(data)

                elif msg_type == "end_of_turn":
                    manager.update_activity(session_id, SessionStatus.thinking)

                else:
                    logger.warning("Session %s: unknown message type '%s'", session_id, msg_type)
            except Exception:
                logger.exception("Session %s: error sending %s to Gemini", session_id, msg_type)
                break

    except WebSocketDisconnect:
        logger.info("Session %s: browser disconnected", session_id)
    except Exception:
        logger.exception("Session %s: unhandled error", session_id)
    finally:
        # Cleanup
        for task in (receiver_task, agent_task):
            if task is not None:
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

        await gemini.close()
        manager.update_activity(session_id, SessionStatus.idle)
        logger.info("Session %s: cleaned up", session_id)
