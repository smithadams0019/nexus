"""Action planner — uses Gemini Flash to convert user requests into desktop actions."""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from typing import Any

from google import genai
from google.genai import types

logger = logging.getLogger("nexus.action_planner")

ACTION_PROMPT = """You are a desktop automation agent. You can see the user's screen and must convert their request into precise desktop actions.

Analyze the screenshot carefully and output a JSON array of actions to perform. Each action is an object with a "type" field.

Available actions:
- {{"type": "click", "x": <int>, "y": <int>, "button": "left"}} — click at pixel coordinates
- {{"type": "double_click", "x": <int>, "y": <int>}} — double click
- {{"type": "type", "text": "<string>"}} — type text
- {{"type": "hotkey", "keys": ["ctrl", "c"]}} — keyboard shortcut
- {{"type": "scroll", "x": <int>, "y": <int>, "amount": <int>}} — scroll (positive=up, negative=down)
- {{"type": "open_url", "url": "https://..."}} — open URL in browser
- {{"type": "open_app", "name": "<app>"}} — open application
- {{"type": "wait", "seconds": <float>}} — wait between actions

RULES:
- x,y coordinates must be absolute pixel positions matching what you see in the screenshot
- Be precise — click on the exact center of buttons, links, text fields
- For typing into a field, first click on the field, then type
- Output ONLY a JSON array, no explanation, no markdown fences
- If you cannot determine the action (e.g., can't find the element), output: []

User request: {request}"""


class ActionPlanner:
    """Plans desktop actions from screenshots + user requests."""

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        self._client = genai.Client(api_key=api_key)

    async def plan_actions(self, screenshot_b64: str, user_request: str) -> list[dict[str, Any]]:
        """Given a screenshot (base64) and user request, return a list of actions to execute."""
        try:
            # Decode base64 to raw bytes for the Blob
            screenshot_bytes = base64.b64decode(screenshot_b64)

            response = await self._client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                inline_data=types.Blob(
                                    mime_type="image/jpeg",
                                    data=screenshot_bytes,
                                )
                            ),
                            types.Part(text=ACTION_PROMPT.format(request=user_request)),
                        ],
                    )
                ],
            )

            raw = response.text.strip()
            logger.info("ActionPlanner raw response: %s", raw[:300])
            # Strip markdown fences if present
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)

            actions = json.loads(raw)
            if not isinstance(actions, list):
                actions = [actions]

            logger.info("Planned %d actions for request: %s", len(actions), user_request[:60])
            return actions

        except json.JSONDecodeError:
            logger.warning("Failed to parse action plan JSON: %s", raw[:200] if 'raw' in dir() else "no response")
            return []
        except Exception:
            logger.exception("Action planning failed")
            return []
