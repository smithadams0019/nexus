"""AlertAgent — proactive anomaly and alert detection from screen frames."""

import json
import logging
import os

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

ALERT_PROMPT = """Look at this screen capture carefully. Is there anything alarming, concerning, or that needs immediate attention?

Examples of things to flag:
- Error messages or exceptions
- Security warnings or certificate issues
- Critical system alerts or failures
- Unusual spikes in metrics or graphs
- Low disk space, high CPU/memory usage
- Failed builds, deployment errors
- Payment failures or account warnings
- Data loss warnings

{context_section}

If there is NOTHING concerning, respond with exactly: NONE

If there IS something concerning, respond ONLY with valid JSON:
{{
  "severity": "info" | "warning" | "critical",
  "message": "clear description of what was detected"
}}

Use these severity levels:
- "info": minor issue, good to know but not urgent
- "warning": should be addressed soon
- "critical": needs immediate attention"""


class AlertAgent:
    """Monitors screen frames for anomalies and alerts using Gemini 2.0 Flash.

    Includes rate limiting to avoid excessive API calls — only every Nth frame
    is actually analyzed.
    """

    def __init__(self, check_interval: int = 10) -> None:
        """Initialize the AlertAgent.

        Args:
            check_interval: Only analyze every Nth frame (default 10).
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        self._client = genai.Client(api_key=api_key)
        self._model = "gemini-2.0-flash"
        self._check_interval = max(1, check_interval)
        self._frame_counter: int = 0

    async def check_frame(
        self, frame_b64: str, session_context: str = ""
    ) -> dict | None:
        """Check a frame for anomalies or alerts.

        Rate-limited: only every Nth frame (configured via check_interval) is
        actually sent to Gemini. All other frames return None immediately.

        Args:
            frame_b64: Base64-encoded image data (JPEG/PNG).
            session_context: Optional context about the current session.

        Returns:
            None if nothing concerning (or frame was skipped due to rate limit).
            Dict with keys: severity ("info"|"warning"|"critical"), message (str).
        """
        self._frame_counter += 1

        if self._frame_counter % self._check_interval != 0:
            return None

        context_section = ""
        if session_context:
            context_section = (
                f"Additional context about the user's session:\n{session_context}"
            )

        prompt = ALERT_PROMPT.format(context_section=context_section)

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=[
                    types.Content(
                        parts=[
                            types.Part(
                                inline_data=types.Blob(
                                    mime_type="image/jpeg",
                                    data=frame_b64,
                                )
                            ),
                            types.Part(text=prompt),
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=256,
                ),
            )

            text = response.text.strip() if response.text else ""

            if not text or text.upper() == "NONE":
                return None

            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            result = json.loads(text)

            severity = result.get("severity", "info")
            if severity not in ("info", "warning", "critical"):
                severity = "info"

            message = result.get("message", "")
            if not message:
                return None

            logger.info(
                "AlertAgent: detected alert (severity=%s): %s",
                severity,
                message[:100],
            )

            return {"severity": severity, "message": message}

        except json.JSONDecodeError:
            logger.debug("Alert check response was not JSON — treating as no alert.")
            return None
        except Exception as exc:
            logger.error("AlertAgent.check_frame failed: %s", exc, exc_info=True)
            return None

    def reset_counter(self) -> None:
        """Reset the internal frame counter."""
        self._frame_counter = 0
