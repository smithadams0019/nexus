"""AnalystAgent — core intelligence that enhances Gemini responses with deep frame analysis."""

import json
import logging
import os

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """Analyze this screen capture in detail. Identify:
1. **Screen type**: What is being shown? (code editor, terminal, dashboard, web page, document, video call, real-world object via camera, etc.)
2. **Key insights**: What are the most important pieces of information visible?
3. **Anomalies**: Is there anything unusual, unexpected, or potentially problematic?
4. **Suggestions**: Based on what you see, what actionable suggestions can you offer?

Respond ONLY with valid JSON in this exact format:
{
  "screen_type": "string describing the type of screen/content",
  "insights": ["insight 1", "insight 2"],
  "anomalies": ["anomaly 1"],
  "suggestions": ["suggestion 1", "suggestion 2"]
}

If a category has no entries, use an empty list."""

INSIGHT_CARD_PROMPT = """You are an AI copilot observing a user's screen and listening to their conversation.

**Recent conversation context:**
{conversation_context}

**Task:** Look at this screen capture and the conversation context. Is there something noteworthy that the user might benefit from knowing? This could be:
- An anomaly or error they haven't noticed
- A useful insight about what's on screen
- A proactive suggestion based on what they're doing
- A warning about something that looks problematic

If there is nothing particularly noteworthy, respond with exactly: NONE

If there IS something noteworthy, respond ONLY with valid JSON:
{{
  "title": "short title for the insight card",
  "content": "detailed explanation (2-3 sentences max)",
  "category": "anomaly" | "insight" | "suggestion" | "warning"
}}"""


class AnalystAgent:
    """Performs deep visual analysis of screen frames using Gemini 2.0 Flash."""

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        self._client = genai.Client(api_key=api_key)
        self._model = "gemini-2.5-flash"

    async def analyze_frame(self, frame_b64: str, context: str = "") -> dict:
        """Send a base64-encoded frame to Gemini for deep analysis.

        Args:
            frame_b64: Base64-encoded image data (JPEG/PNG).
            context: Optional additional context to include in the prompt.

        Returns:
            Dict with keys: screen_type, insights, anomalies, suggestions.
        """
        prompt = ANALYSIS_PROMPT
        if context:
            prompt = f"Additional context: {context}\n\n{prompt}"

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
                    temperature=0.3,
                    max_output_tokens=1024,
                ),
            )

            text = response.text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            result = json.loads(text)

            return {
                "screen_type": result.get("screen_type", "unknown"),
                "insights": result.get("insights", []),
                "anomalies": result.get("anomalies", []),
                "suggestions": result.get("suggestions", []),
            }

        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Gemini analysis response as JSON: %s", exc)
            return {
                "screen_type": "unknown",
                "insights": [],
                "anomalies": [],
                "suggestions": [],
            }
        except Exception as exc:
            logger.error("AnalystAgent.analyze_frame failed: %s", exc, exc_info=True)
            return {
                "screen_type": "error",
                "insights": [],
                "anomalies": [],
                "suggestions": [],
            }

    async def generate_insight_card(
        self, frame_b64: str, conversation_context: str
    ) -> dict | None:
        """Analyze a frame plus conversation context to produce an InsightCard.

        Args:
            frame_b64: Base64-encoded image data.
            conversation_context: Recent conversation text for added context.

        Returns:
            A dict with title, content, category — or None if nothing noteworthy.
        """
        prompt = INSIGHT_CARD_PROMPT.format(
            conversation_context=conversation_context or "(no conversation yet)"
        )

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
                    temperature=0.4,
                    max_output_tokens=512,
                ),
            )

            text = response.text.strip()

            if text.upper() == "NONE":
                return None

            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            result = json.loads(text)

            category = result.get("category", "insight")
            if category not in ("anomaly", "insight", "suggestion", "warning"):
                category = "insight"

            return {
                "title": result.get("title", "Observation"),
                "content": result.get("content", ""),
                "category": category,
            }

        except json.JSONDecodeError:
            logger.debug("Insight card response was not JSON — treating as no insight.")
            return None
        except Exception as exc:
            logger.error(
                "AnalystAgent.generate_insight_card failed: %s", exc, exc_info=True
            )
            return None
