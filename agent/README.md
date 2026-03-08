# Nexus Desktop Control Agent

A lightweight agent that runs on the user's machine, connects to the Nexus backend via WebSocket, and executes desktop control commands (click, type, scroll, screenshot, etc.) using PyAutoGUI.

## Install

```bash
cd agent
pip install -r requirements.txt
```

On Linux you may also need:

```bash
sudo apt-get install python3-tk python3-dev scrot
```

## Run

```bash
python agent.py SESSION_ID
```

Optionally specify a custom backend URL:

```bash
python agent.py SESSION_ID --url ws://192.168.1.10:8000
```

The agent will auto-reconnect if the connection drops.

## Supported Actions

| Action         | Description                          |
|----------------|--------------------------------------|
| `click`        | Move mouse and click                 |
| `double_click` | Double-click at position             |
| `type`         | Type text with realistic delay       |
| `hotkey`       | Press a key combination (e.g. Ctrl+C)|
| `scroll`       | Scroll at a given position           |
| `move`         | Move mouse without clicking          |
| `screenshot`   | Capture screen, return as base64 JPEG|
| `wait`         | Pause before next action             |
| `open_url`     | Open URL in default browser          |
| `open_app`     | Launch an application by name        |

## Safety

- **Failsafe**: move the mouse to the upper-left corner of the screen to immediately abort any running action.
- **Security warning**: this agent grants AI control of your desktop. Only run it in trusted environments and with sessions you initiated yourself.
