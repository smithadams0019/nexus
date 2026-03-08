"""Desktop action executor — runs actions directly via PyAutoGUI (lazy import)."""

from __future__ import annotations

import base64
import io
import logging
import subprocess
import webbrowser
from typing import Any

logger = logging.getLogger("nexus.desktop")

_pyautogui = None


def _get_pyautogui():
    """Lazy import pyautogui to avoid X display errors at module load time."""
    global _pyautogui
    if _pyautogui is None:
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05
        _pyautogui = pyautogui
    return _pyautogui


async def execute_action(action: dict[str, Any]) -> dict[str, Any]:
    """Execute a single desktop action. Returns {success, message}."""
    action_type = action.get("type", "")

    try:
        pag = _get_pyautogui()

        if action_type == "click":
            x, y = action["x"], action["y"]
            button = action.get("button", "left")
            pag.moveTo(x, y, duration=0.15)
            pag.click(x, y, button=button)
            return {"success": True, "message": f"Clicked ({x}, {y}) {button}"}

        elif action_type == "double_click":
            x, y = action["x"], action["y"]
            pag.moveTo(x, y, duration=0.15)
            pag.doubleClick(x, y)
            return {"success": True, "message": f"Double-clicked ({x}, {y})"}

        elif action_type == "type":
            text = action["text"]
            if text.isascii():
                pag.typewrite(text, interval=0.03)
            else:
                pag.write(text)
            return {"success": True, "message": f"Typed: {text[:50]}"}

        elif action_type == "hotkey":
            keys = action["keys"]
            pag.hotkey(*keys)
            return {"success": True, "message": f"Hotkey: {'+'.join(keys)}"}

        elif action_type == "scroll":
            x = action.get("x")
            y = action.get("y")
            amount = action.get("amount", 3)
            if x is not None and y is not None:
                pag.moveTo(x, y, duration=0.1)
            pag.scroll(amount)
            return {"success": True, "message": f"Scrolled {amount}"}

        elif action_type == "move":
            x, y = action["x"], action["y"]
            pag.moveTo(x, y, duration=0.2)
            return {"success": True, "message": f"Moved to ({x}, {y})"}

        elif action_type == "screenshot":
            screenshot = pag.screenshot()
            buf = io.BytesIO()
            screenshot.save(buf, format="JPEG", quality=70)
            b64 = base64.b64encode(buf.getvalue()).decode()
            return {"success": True, "message": "Screenshot taken", "data": b64}

        elif action_type == "open_url":
            url = action["url"]
            webbrowser.open(url)
            return {"success": True, "message": f"Opened URL: {url}"}

        elif action_type == "open_app":
            name = action["name"]
            subprocess.Popen(
                ["xdg-open", name] if not name.endswith(".app") else ["open", "-a", name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return {"success": True, "message": f"Opened app: {name}"}

        elif action_type == "wait":
            seconds = action.get("seconds", 1.0)
            return {"success": True, "message": f"Wait {seconds}s"}

        else:
            return {"success": False, "message": f"Unknown action type: {action_type}"}

    except Exception as e:
        logger.exception("Action execution failed: %s", action_type)
        return {"success": False, "message": f"Error: {str(e)}"}
