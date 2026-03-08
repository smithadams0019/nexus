# Building Nexus: A Real-Time Voice + Vision AI Copilot with Google's Gemini Live API

*How we built an AI assistant that can see your screen, hear your voice, and control your desktop — all in real time.*

---

What if your AI assistant could actually *see* what you're looking at?

Not "paste a screenshot and wait 30 seconds." Not "describe what's on your screen." But genuinely watch your screen in real time, listen to your voice, and respond instantly with spoken words — like a knowledgeable colleague sitting next to you.

That's what we built with **Nexus**.

Nexus is a real-time voice and vision AI copilot powered by Google's Gemini Live API. You open it in your browser, share your camera or screen, and start talking. The AI sees everything, hears everything, and responds with natural speech. No typing. No waiting. Just point and talk.

In this post, I'll walk through how we built it, the technical challenges we faced, and what we learned about working with one of the newest and most powerful APIs in AI.

---

## The Problem with Current AI Assistants

Most AI tools today work like this:

1. You type a prompt
2. You wait
3. You read a wall of text
4. You copy-paste the relevant part

Even the "multimodal" ones usually mean: upload an image, wait for processing, get text back.

This is fine for many tasks. But it completely breaks down for anything that requires *context* — reviewing code on your screen, analyzing a dashboard, understanding what's happening in front of your camera. You end up spending more time explaining what you're looking at than actually getting help.

The Gemini Live API changes this. It supports **bidirectional audio and video streaming** in a single persistent session. Audio in, audio out, video in — all at the same time, all in real time. This is the foundation that made Nexus possible.

---

## What Nexus Does

When you open Nexus and start a session, here's what happens:

**You share your camera or screen.** Nexus captures JPEG frames every 2 seconds and streams them to the backend.

**You talk naturally.** Your microphone captures audio at 16kHz PCM and streams it continuously. No push-to-talk button. Just speak.

**Nexus responds with voice.** Gemini processes your audio and video input together and responds with natural speech, streamed back and played through your browser's Web Audio API.

**Nexus adapts to what it sees.** The system instruction tells Gemini to adapt its persona based on the visual context:
- See a dashboard? It becomes a data analyst.
- See source code? It becomes a code reviewer.
- See a document? It becomes an editor.
- See a real-world scene? It becomes an informative observer.

**Background agents work silently.** While you're talking to Nexus, background agents analyze your screen every 10 seconds:
- The **Alert Agent** flags errors, warnings, and anomalies
- The **Analyst Agent** generates contextual insight cards
- The **Memory Agent** stores conversation context in Google Cloud Firestore

**Desktop control.** When you share your screen and type a command like "click on the search bar and type Ghana," the **Action Planner** agent analyzes your screenshot with Gemini 2.5 Flash, determines the exact pixel coordinates, and executes the action on your desktop via PyAutoGUI.

---

## The Architecture

Here's how everything connects:

```
User (Camera/Mic/Screen)
    ↓ WebSocket (wss://)
React Frontend (Vite + Zustand)
    ↓ WebSocket (wss://)
FastAPI Backend (Python)
    ├── Task 1: Gemini Receiver (streams responses back)
    ├── Task 2: Agent Processor (insights + alerts every 10s)
    └── Task 3: Input Router (forwards frames/audio/text)
            ↓
    Gemini Live API (bidirectional audio + video)
    Agent System (Analyst, Alert, Memory, Action Planner)
    Google Cloud (Cloud Run, Firestore)
    Desktop Executor (PyAutoGUI)
```

The key insight: **three concurrent async tasks** run per WebSocket connection. This means the AI can receive your input, process agent insights, and stream responses back — all simultaneously without blocking.

---

## Deep Dive: Connecting to the Gemini Live API

This was the most challenging part of the build. The Gemini Live API is relatively new, and we hit several surprises.

### Establishing the Connection

The `google-genai` SDK provides `client.aio.live.connect()`, which returns an async context manager — not an awaitable. This tripped us up initially:

```python
# This is WRONG
self._session = await self._client.aio.live.connect(model=model, config=config)

# This is RIGHT
self._ctx_manager = self._client.aio.live.connect(model=model, config=config)
self._session = await self._ctx_manager.__aenter__()
```

### Streaming Input

Video frames and audio are sent using `send_realtime_input()`:

```python
# Send a JPEG frame
await session.send_realtime_input(
    video=types.Blob(mime_type="image/jpeg", data=frame_bytes),
)

# Send PCM audio
await session.send_realtime_input(
    audio=types.Blob(mime_type="audio/pcm;rate=16000", data=audio_bytes),
)
```

Text messages use a different method:

```python
await session.send_client_content(
    turns=types.Content(role="user", parts=[types.Part(text=text)]),
    turn_complete=True,
)
```

### The Multi-Turn Problem

This one cost us hours. `session.receive()` is an async iterator that yields responses — but it **exits after each turn completes**. Our first implementation only worked for one exchange:

```python
# BROKEN: Only handles one turn
async for response in session.receive():
    # process response...
    # After turn_complete, the iterator ends. Silence forever.
```

The fix: wrap it in a loop:

```python
# FIXED: Handles multiple turns
while not self._closed:
    async for response in session.receive():
        # process audio, text, turn_complete...
```

### Audio-Only Modality

The model `gemini-2.5-flash-native-audio-latest` only supports `response_modalities=["AUDIO"]`. You cannot combine `["AUDIO", "TEXT"]`. This has a major implication: **the model can speak but cannot output structured text.**

This meant our original plan — having Gemini output action commands as JSON in its response — was impossible. The model would *say* "Sure, I'll click that for you" but couldn't output a structured `{"type": "click", "x": 500, "y": 300}`.

Our solution: a separate **Action Planner** agent.

---

## The Action Planner: Making Desktop Control Work

Since the Live API can only respond with audio, we needed a different approach for desktop control. The Action Planner is a separate Gemini 2.5 Flash call (non-live, standard API) that:

1. Takes the latest screenshot (base64-encoded JPEG)
2. Takes the user's text request
3. Returns a JSON array of precise desktop actions

```python
class ActionPlanner:
    async def plan_actions(self, screenshot_b64: str, user_request: str):
        screenshot_bytes = base64.b64decode(screenshot_b64)

        response = await self._client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(role="user", parts=[
                    types.Part(inline_data=types.Blob(
                        mime_type="image/jpeg",
                        data=screenshot_bytes,
                    )),
                    types.Part(text=ACTION_PROMPT.format(request=user_request)),
                ])
            ],
        )
        # Parse JSON array of actions
        return json.loads(response.text.strip())
```

These actions are then executed by the Desktop Executor using PyAutoGUI:

```python
async def execute_action(action):
    pag = _get_pyautogui()

    if action["type"] == "click":
        pag.moveTo(action["x"], action["y"], duration=0.15)
        pag.click(action["x"], action["y"])

    elif action["type"] == "type":
        pag.typewrite(action["text"], interval=0.03)

    elif action["type"] == "hotkey":
        pag.hotkey(*action["keys"])
    # ... scroll, open_url, open_app, etc.
```

The flow in the WebSocket handler:

```python
elif msg_type == "text":
    await gemini.send_text(data)  # Send to Gemini for voice response

    if last_frame[0] is not None:  # Screen is being shared
        actions = await action_planner.plan_actions(last_frame[0], data)
        for action in actions:
            result = await execute_action(action)
            await ws.send_json({
                "type": "action_result",
                "action": action["type"],
                "success": result["success"],
                "message": result["message"],
            })
```

Gemini voices the response. The Action Planner executes it. Both happen simultaneously.

---

## Real-Time Audio in the Browser

Getting smooth audio playback from streaming PCM chunks was trickier than expected.

Gemini sends audio as raw PCM bytes (24kHz). Each chunk arrives independently. If you just play them immediately, you get gaps and clicks between chunks. If you buffer too much, you get noticeable latency.

The solution: **sequential scheduling** with Web Audio API.

```typescript
let nextPlayTime = 0;

export function playAudioChunk(audioContext: AudioContext, base64Data: string) {
  const pcmBytes = atob(base64Data);
  const samples = new Float32Array(pcmBytes.length / 2);

  // Convert PCM16 to Float32
  for (let i = 0; i < samples.length; i++) {
    const sample = (pcmBytes.charCodeAt(i * 2) | (pcmBytes.charCodeAt(i * 2 + 1) << 8));
    samples[i] = (sample > 32767 ? sample - 65536 : sample) / 32768;
  }

  const buffer = audioContext.createBuffer(1, samples.length, 24000);
  buffer.copyToChannel(samples, 0);

  const source = audioContext.createBufferSource();
  source.buffer = buffer;
  source.connect(audioContext.destination);

  // Schedule this chunk right after the previous one
  const now = audioContext.currentTime;
  const startTime = Math.max(now, nextPlayTime);
  source.start(startTime);
  nextPlayTime = startTime + buffer.duration;
}
```

Each chunk is scheduled to start exactly when the previous one ends. No gaps, no overlap, no clicks.

---

## Background Agents: Intelligence Without Asking

One of the most compelling features of Nexus is that it doesn't wait for you to ask questions. The Agent Processor runs as a background task every 10 seconds, analyzing the latest frame with two specialized agents:

**Alert Agent** — monitors for anything that looks wrong:
- Error messages on screen
- Security warnings
- Metric spikes in dashboards
- Build failures
- Low disk space warnings

When it detects something, it sends an alert to the browser with a severity level (info, warning, critical). Critical alerts pulse red in the UI. You didn't ask — Nexus just noticed.

**Analyst Agent** — generates contextual insight cards:
- Summarizes what's on screen
- Identifies trends in data
- Suggests actions
- Categorizes as anomaly, insight, suggestion, or warning

Both agents use `gemini-2.5-flash` for fast inference and are designed to fail silently — a background agent crashing should never kill the main conversation.

---

## Deployment: One Container, Everything Included

We wanted the simplest possible deployment. The solution: a **multi-stage Docker build** that packages both the React dashboard and Python backend into a single container.

```dockerfile
# Stage 1: Build React dashboard
FROM node:20-slim AS dashboard-build
WORKDIR /dashboard
COPY dashboard/ .
RUN npm install && npm run build

# Stage 2: Python backend + static files
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY --from=dashboard-build /dashboard/dist /app/static
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

FastAPI serves the built dashboard as static files, with a catch-all route for SPA routing. One image, one Cloud Run service, everything works.

Deployment is automated:

```bash
export GOOGLE_CLOUD_PROJECT=your-project
export GEMINI_API_KEY=your-key
bash deploy/cloud-run.sh
```

Cloud Run gives us auto-scaling (0 to 3 instances), session affinity for WebSocket connections, and HTTPS out of the box — which is required for browser camera and microphone access.

---

## Lessons Learned

**1. The Gemini Live API is powerful but young.** Model names, API versions, and SDK methods may change. We went through multiple model names and API versions before finding the right combination. Build with flexibility.

**2. Audio-only modality requires creative workarounds.** If you need structured output alongside voice responses, use a separate non-live API call. The pattern of "Live API for conversation + Flash API for structured tasks" works well.

**3. WebSocket lifecycle management matters.** Every connection spawns multiple async tasks and a Gemini session. Proper cleanup in `finally` blocks is essential, or you'll leak connections.

**4. Background agents add massive value with minimal complexity.** Running a frame analysis every 10 seconds is cheap (one API call) but makes the product feel genuinely intelligent. The AI notices things before you do.

**5. Browser audio APIs are finicky.** Sequential scheduling with `AudioBufferSourceNode` is the way to go for streaming PCM playback. Don't try to use `AudioWorklet` for simple playback — it's overkill.

---

## What's Next

- **Voice-triggered desktop actions** — transcribe spoken commands and route them to the Action Planner
- **Multi-session collaboration** — share a Nexus session with teammates
- **Plugin system** — custom agents for Slack, Jira, email, and more
- **Mobile-native app** — deeper camera and microphone integration

---

## Try It

**Live demo:** [nexus-backend-cxotjai2ta-uc.a.run.app](https://nexus-backend-cxotjai2ta-uc.a.run.app)

**Source code:** [github.com/smithadams0019/nexus](https://github.com/smithadams0019/nexus)

Nexus was built for the [Gemini Live Agent Challenge](https://geminiliveagentchallenge.devpost.com/) in the **Live Agents** category. If you're interested in building with the Gemini Live API, the source code is fully open — clone it, run it, break it, improve it.

---

*Built with Google Gemini Live API, FastAPI, React, and deployed on Google Cloud Run.*
