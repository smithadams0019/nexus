"""Nexus Desktop Control Agent — receives commands from the backend and controls the desktop."""

from __future__ import annotations

import asyncio
import base64
import io
import json
import subprocess
import sys
import time
import webbrowser

import pyautogui
from PIL import Image

try:
    import websockets
    from websockets.asyncio.client import connect as ws_connect
except ImportError:
    print("\033[91mError: websockets library not found. Run: pip install -r requirements.txt\033[0m")
    sys.exit(1)

# ---------------------------------------------------------------------------
# PyAutoGUI safety settings
# ---------------------------------------------------------------------------

pyautogui.FAILSAFE = True  # move mouse to upper-left corner to abort
pyautogui.PAUSE = 0.1  # small pause between actions for human-like feel

# ---------------------------------------------------------------------------
# Terminal colours
# ---------------------------------------------------------------------------

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
DIM = "\033[2m"


def _log(colour: str, label: str, message: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"{DIM}{ts}{RESET} {colour}{BOLD}[{label}]{RESET} {message}")


def log_info(msg: str) -> None:
    _log(CYAN, "INFO", msg)


def log_action(msg: str) -> None:
    _log(GREEN, "ACTION", msg)


def log_warn(msg: str) -> None:
    _log(YELLOW, "WARN", msg)


def log_error(msg: str) -> None:
    _log(RED, "ERROR", msg)


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------

def handle_click(action: dict) -> dict:
    x = int(action["x"])
    y = int(action["y"])
    button = action.get("button", "left")
    pyautogui.moveTo(x, y, duration=0.25)
    pyautogui.click(x, y, button=button)
    log_action(f"click ({button}) at ({x}, {y})")
    return {"type": "action_result", "success": True, "message": f"Clicked {button} at ({x}, {y})"}


def handle_double_click(action: dict) -> dict:
    x = int(action["x"])
    y = int(action["y"])
    pyautogui.moveTo(x, y, duration=0.25)
    pyautogui.doubleClick(x, y)
    log_action(f"double_click at ({x}, {y})")
    return {"type": "action_result", "success": True, "message": f"Double-clicked at ({x}, {y})"}


def handle_type(action: dict) -> dict:
    text = str(action["text"])
    pyautogui.typewrite(text, interval=0.03) if text.isascii() else pyautogui.write(text)
    log_action(f"type: {text[:60]}{'...' if len(text) > 60 else ''}")
    return {"type": "action_result", "success": True, "message": f"Typed {len(text)} characters"}


def handle_hotkey(action: dict) -> dict:
    keys = action["keys"]
    pyautogui.hotkey(*keys)
    combo = "+".join(keys)
    log_action(f"hotkey: {combo}")
    return {"type": "action_result", "success": True, "message": f"Pressed {combo}"}


def handle_scroll(action: dict) -> dict:
    x = int(action["x"])
    y = int(action["y"])
    amount = int(action["amount"])
    pyautogui.moveTo(x, y, duration=0.15)
    pyautogui.scroll(amount, x, y)
    direction = "up" if amount > 0 else "down"
    log_action(f"scroll {direction} ({amount}) at ({x}, {y})")
    return {"type": "action_result", "success": True, "message": f"Scrolled {amount} at ({x}, {y})"}


def handle_move(action: dict) -> dict:
    x = int(action["x"])
    y = int(action["y"])
    pyautogui.moveTo(x, y, duration=0.3)
    log_action(f"move to ({x}, {y})")
    return {"type": "action_result", "success": True, "message": f"Moved mouse to ({x}, {y})"}


def handle_screenshot(_action: dict) -> dict:
    screenshot = pyautogui.screenshot()
    buffer = io.BytesIO()
    screenshot.save(buffer, format="JPEG", quality=75)
    b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
    log_action(f"screenshot taken ({len(b64_data)} bytes base64)")
    return {"type": "screenshot_result", "data": b64_data}


def handle_wait(action: dict) -> dict:
    seconds = float(action.get("seconds", 1.0))
    log_action(f"waiting {seconds}s")
    time.sleep(seconds)
    return {"type": "action_result", "success": True, "message": f"Waited {seconds}s"}


def handle_open_url(action: dict) -> dict:
    url = str(action["url"])
    webbrowser.open(url)
    log_action(f"open_url: {url}")
    return {"type": "action_result", "success": True, "message": f"Opened URL: {url}"}


def handle_open_app(action: dict) -> dict:
    name = str(action["name"])
    try:
        if sys.platform == "linux":
            subprocess.Popen(
                ["xdg-open", name] if "." in name else [name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-a", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif sys.platform == "win32":
            subprocess.Popen(["start", name], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            return {"type": "action_result", "success": False, "message": f"Unsupported platform: {sys.platform}"}
    except FileNotFoundError:
        return {"type": "action_result", "success": False, "message": f"Application not found: {name}"}
    log_action(f"open_app: {name}")
    return {"type": "action_result", "success": True, "message": f"Opened application: {name}"}


# Dispatch table
ACTION_HANDLERS: dict[str, callable] = {
    "click": handle_click,
    "double_click": handle_double_click,
    "type": handle_type,
    "hotkey": handle_hotkey,
    "scroll": handle_scroll,
    "move": handle_move,
    "screenshot": handle_screenshot,
    "wait": handle_wait,
    "open_url": handle_open_url,
    "open_app": handle_open_app,
}


def execute_action(action: dict) -> dict:
    """Execute a single action and return a result dict."""
    action_type = action.get("type", "")
    handler = ACTION_HANDLERS.get(action_type)
    if handler is None:
        log_warn(f"unknown action type: {action_type}")
        return {"type": "action_result", "success": False, "message": f"Unknown action type: {action_type}"}
    try:
        return handler(action)
    except pyautogui.FailSafeException:
        log_error("FAILSAFE triggered — mouse moved to corner. Aborting action.")
        return {"type": "action_result", "success": False, "message": "Failsafe triggered (mouse at corner)"}
    except Exception as exc:
        log_error(f"action {action_type} failed: {exc}")
        return {"type": "action_result", "success": False, "message": f"Action failed: {exc}"}


# ---------------------------------------------------------------------------
# WebSocket client with auto-reconnect
# ---------------------------------------------------------------------------

async def agent_loop(session_id: str, backend_url: str) -> None:
    """Connect to the backend and process action commands in a loop."""
    base_delay = 1.0
    max_delay = 30.0
    attempt = 0

    while True:
        ws_url = f"{backend_url}/ws/agent/{session_id}"
        try:
            log_info(f"connecting to {ws_url} ...")
            async with ws_connect(ws_url) as ws:
                log_info(f"connected to backend (session: {session_id})")
                attempt = 0  # reset backoff on successful connection

                async for raw_message in ws:
                    try:
                        action = json.loads(raw_message)
                    except json.JSONDecodeError:
                        log_warn(f"received non-JSON message: {raw_message[:100]}")
                        continue

                    action_type = action.get("type", "unknown")
                    log_info(f"received action: {action_type}")

                    # Execute the action (blocking — actions are sequential)
                    result = execute_action(action)

                    # Send result back
                    await ws.send(json.dumps(result))
                    log_info(f"sent result: success={result.get('success', 'n/a')}")

            # Connection closed cleanly
            log_warn("connection closed by server")

        except (ConnectionRefusedError, OSError) as exc:
            log_warn(f"connection failed: {exc}")
        except websockets.exceptions.ConnectionClosed as exc:
            log_warn(f"connection lost: {exc}")
        except Exception as exc:
            log_error(f"unexpected error: {exc}")

        # Exponential backoff for reconnection
        attempt += 1
        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
        log_info(f"reconnecting in {delay:.1f}s (attempt {attempt}) ...")
        await asyncio.sleep(delay)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    session_id: str | None = None
    backend_url = "ws://localhost:8000"

    # Parse CLI arguments
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg in ("--url", "-u") and i + 1 < len(args):
            backend_url = args[i + 1]
        elif not arg.startswith("-") and session_id is None:
            session_id = arg

    if session_id is None:
        try:
            session_id = input(f"{CYAN}Enter session ID: {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

    if not session_id:
        log_error("session ID is required")
        print(f"\nUsage: python {sys.argv[0]} SESSION_ID [--url ws://host:port]")
        sys.exit(1)

    print(f"\n{BOLD}{'=' * 50}{RESET}")
    print(f"{BOLD}  Nexus Desktop Control Agent{RESET}")
    print(f"{BOLD}{'=' * 50}{RESET}")
    print(f"  Session:  {CYAN}{session_id}{RESET}")
    print(f"  Backend:  {CYAN}{backend_url}{RESET}")
    print(f"  Failsafe: move mouse to upper-left corner to abort")
    print(f"{BOLD}{'=' * 50}{RESET}\n")

    try:
        asyncio.run(agent_loop(session_id, backend_url))
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Shutting down gracefully...{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
