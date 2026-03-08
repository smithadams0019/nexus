"""Gemini Live API service for real-time voice + vision streaming."""

from __future__ import annotations

import base64
import logging
import os
from typing import AsyncGenerator

from google import genai
from google.genai import types

logger = logging.getLogger("nexus.gemini_live")

SYSTEM_INSTRUCTION = (
    "You are Nexus, a real-time voice and vision AI copilot. "
    "You can see through the user's camera or screen share and hear their voice in real time.\n\n"
    "Core behaviour:\n"
    "- Be helpful, concise, and conversational. Speak naturally as if you are a knowledgeable colleague sitting next to the user.\n"
    "- Be proactive: if you notice an issue, anomaly, or opportunity in the visual feed, point it out without waiting to be asked.\n"
    "- Adapt your persona to the context of what you see:\n"
    "  - Dashboard / analytics screen -> act as a data analyst. Summarise trends, flag anomalies.\n"
    "  - Source code / IDE -> act as a senior code reviewer. Spot bugs, suggest improvements.\n"
    "  - Document / article -> act as an editor and summariser.\n"
    "  - Real-world object or scene -> be informative and observant.\n"
    "  - Design tool / UI mockup -> act as a UX consultant.\n"
    "- Support multiple languages. If the user speaks in a language other than English, respond in the same language.\n"
    "- Keep responses short (1-3 sentences) unless the user asks for detail.\n"
    "- When you are unsure, say so honestly rather than guessing.\n"
    "- Never repeat the same observation twice in a row."
    "\n\n"
    "DESKTOP CONTROL:\n"
    "You have the ability to control the user's desktop. When the user asks you to perform an action "
    "on their screen (click something, open an app, type text, etc.), a separate action system will "
    "automatically detect and execute the action based on the screen share. "
    "You do NOT need to output any special commands or JSON. Just acknowledge the request naturally, "
    "like 'Sure, doing that now' or 'Opening that for you'. The action will be executed automatically. "
    "Do NOT say 'I will' or 'I can' without it happening — the system handles execution for you."
)


class GeminiLiveService:
    """Manages a single Gemini Live API streaming session."""

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set")

        self._client = genai.Client(api_key=api_key)
        self._session: types.AsyncSession | None = None
        self._ctx_manager = None
        self._closed = False

    async def connect(self) -> None:
        """Open the live streaming session with Gemini."""
        config = types.LiveConnectConfig(
            system_instruction=types.Content(
                parts=[types.Part(text=SYSTEM_INSTRUCTION)]
            ),
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Puck",
                    )
                )
            ),
        )
        self._ctx_manager = self._client.aio.live.connect(
            model="gemini-2.5-flash-native-audio-latest",
            config=config,
        )
        self._session = await self._ctx_manager.__aenter__()
        logger.info("Gemini Live session connected")

    def _ensure_session(self) -> types.AsyncSession:
        if self._session is None:
            raise RuntimeError("Gemini session is not connected. Call connect() first.")
        return self._session

    # ------------------------------------------------------------------
    # Sending data
    # ------------------------------------------------------------------

    async def send_frame(self, frame_data: bytes) -> None:
        """Send a JPEG video frame to Gemini."""
        session = self._ensure_session()
        await session.send_realtime_input(
            video=types.Blob(mime_type="image/jpeg", data=frame_data),
        )
        logger.debug("Sent video frame (%d bytes)", len(frame_data))

    async def send_audio(self, audio_data: bytes) -> None:
        """Send a PCM 16 kHz audio chunk to Gemini."""
        session = self._ensure_session()
        await session.send_realtime_input(
            audio=types.Blob(mime_type="audio/pcm;rate=16000", data=audio_data),
        )
        logger.debug("Sent audio chunk (%d bytes)", len(audio_data))

    async def send_text(self, text: str) -> None:
        """Send a text message to Gemini, signalling end of turn."""
        session = self._ensure_session()
        await session.send_client_content(
            turns=types.Content(
                role="user",
                parts=[types.Part(text=text)],
            ),
            turn_complete=True,
        )
        logger.info("Sent text input: %s", text[:80])

    # ------------------------------------------------------------------
    # Receiving responses
    # ------------------------------------------------------------------

    async def receive_responses(self) -> AsyncGenerator[dict, None]:
        """Async generator that yields parsed response dicts from Gemini.

        Yielded dicts have one of these shapes:
            {"type": "audio", "data": "<base64 pcm>"}
            {"type": "text",  "data": "<text string>"}
            {"type": "turn_complete"}
        """
        session = self._ensure_session()
        try:
            while not self._closed:
                async for response in session.receive():
                    try:
                        server_content = response.server_content
                    except AttributeError:
                        continue

                    if server_content is None:
                        continue

                    # Process model turn parts (audio / text)
                    try:
                        model_turn = server_content.model_turn
                        if model_turn and model_turn.parts:
                            for part in model_turn.parts:
                                # Audio part
                                try:
                                    if part.inline_data and part.inline_data.data:
                                        audio_bytes = part.inline_data.data
                                        if isinstance(audio_bytes, bytes):
                                            audio_b64 = base64.b64encode(audio_bytes).decode()
                                        else:
                                            audio_b64 = audio_bytes
                                        yield {"type": "audio", "data": audio_b64}
                                        continue
                                except AttributeError:
                                    pass

                                # Text part
                                try:
                                    if part.text:
                                        yield {"type": "text", "data": part.text}
                                        continue
                                except AttributeError:
                                    pass
                    except AttributeError:
                        pass

                    # Turn complete signal
                    try:
                        if server_content.turn_complete:
                            yield {"type": "turn_complete"}
                    except AttributeError:
                        pass

        except Exception:
            if not self._closed:
                logger.exception("Error in Gemini response stream")
                raise

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the Gemini Live session."""
        self._closed = True
        if self._ctx_manager is not None:
            try:
                await self._ctx_manager.__aexit__(None, None, None)
                logger.info("Gemini Live session closed")
            except Exception:
                logger.warning("Error closing Gemini session", exc_info=True)
            finally:
                self._session = None
                self._ctx_manager = None
