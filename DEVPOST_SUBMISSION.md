# Nexus — Real-Time Voice + Vision AI Copilot

**Category: Live Agents**

**Live Demo:** https://nexus-backend-cxotjai2ta-uc.a.run.app

**Repository:** *(add your GitHub URL here)*

---

## Inspiration

We live in an era of powerful AI, yet most interactions are still trapped in a text box. You type a prompt, wait, read a wall of text. Meanwhile, the most natural form of communication — voice — goes unused. And the richest source of context — what you're looking at — gets ignored entirely.

We asked: **What if AI could see what you see and talk to you like a colleague sitting next to you?**

That's Nexus. A real-time voice and vision AI copilot that watches your screen (or camera) and has a live, intelligent conversation with you about whatever you're working on. No typing. No copying and pasting screenshots. Just point and talk.

The Gemini Live API made this possible — bidirectional audio and video streaming in a single persistent session. We saw the chance to build something that truly breaks the "text box" paradigm.

---

## What it does

**Nexus is a real-time AI copilot you can talk to while sharing your camera or screen.** Open it on any device, start a session, and Nexus instantly:

- **Sees** your camera feed or shared screen in real time (JPEG frames streamed every 2 seconds)
- **Listens** to your voice and responds conversationally with natural speech (via Gemini's native audio)
- **Adapts its persona** based on what it sees:
  - Dashboard or spreadsheet → acts as a **data analyst**, summarizing trends and flagging anomalies
  - Source code or IDE → acts as a **senior code reviewer**, spotting bugs and suggesting improvements
  - Document or article → acts as an **editor and summarizer**
  - Real-world scene → becomes an **informative observer**
  - UI mockup → becomes a **UX consultant**

### Background Intelligence (runs automatically)
- **Alert Agent** — continuously monitors your screen for errors, warnings, security issues, and metric spikes. Sends real-time alerts without you asking.
- **Analyst Agent** — generates contextual insight cards every 10 seconds with anomalies, suggestions, and observations.
- **Memory Agent** — stores conversation context in Google Cloud Firestore so Nexus remembers what you've discussed.

### Desktop Control
- **Action Planner** — when you share your screen and type a command like "open Chrome" or "click on the search bar and type Ghana", Nexus analyzes the screenshot with Gemini 2.5 Flash, plans precise pixel-coordinate actions, and executes them on your desktop via PyAutoGUI.
- Supports: click, double-click, type, keyboard shortcuts, scroll, open URLs, open apps.

### Works Everywhere
- Responsive design works on desktop, tablet, and mobile
- Camera and screen share both supported
- Voice and text input both work
- HTTPS on Cloud Run enables microphone and camera access on all devices

---

## How we built it

### Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Browser (React)                     │
│  Camera/Screen → JPEG frames                          │
│  Microphone → PCM 16kHz audio                         │
│  ← Audio playback (PCM 24kHz)                         │
│  ← Insight cards, Alerts, Action results              │
└─────────────────────┬────────────────────────────────┘
                      │ WebSocket (wss://)
┌─────────────────────▼────────────────────────────────┐
│              FastAPI Backend (Python)                  │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │           WebSocket Handler (main.py)            │ │
│  │  ┌──────────┐ ┌──────────┐ ┌────────────────┐  │ │
│  │  │ Gemini   │ │ Agent    │ │ Main Input     │  │ │
│  │  │ Receiver │ │ Processor│ │ Loop           │  │ │
│  │  │ Task     │ │ Task     │ │ (frame/audio/  │  │ │
│  │  │          │ │ (10s)    │ │  text routing) │  │ │
│  │  └────┬─────┘ └────┬─────┘ └───────┬────────┘  │ │
│  └───────┼────────────┼───────────────┼────────────┘ │
│          │            │               │               │
│  ┌───────▼──┐  ┌──────▼──────┐  ┌────▼─────────┐    │
│  │ Gemini   │  │  Analyst    │  │ Action       │    │
│  │ Live API │  │  Alert      │  │ Planner      │    │
│  │ Service  │  │  Memory     │  │ + Desktop    │    │
│  │          │  │  Research   │  │ Executor     │    │
│  └──────────┘  └─────────────┘  └──────────────┘    │
│                       │                               │
│              ┌────────▼────────┐                      │
│              │ Google Cloud    │                      │
│              │ Firestore       │                      │
│              └─────────────────┘                      │
└──────────────────────────────────────────────────────┘
```

### The Gemini Live API Connection

The core of Nexus is a persistent bidirectional session with Gemini via `google-genai` SDK:

1. **Browser** captures camera frames (JPEG) and microphone audio (PCM 16kHz) and streams them over WebSocket
2. **Backend** receives these and forwards to Gemini Live API using `send_realtime_input()` for audio/video and `send_client_content()` for text
3. **Gemini** processes multimodal input in real time and streams audio responses back
4. **Backend** relays audio to browser where it's played sequentially using Web Audio API
5. **Three async tasks** run concurrently per session: Gemini receiver, agent processor, and input router

### Multi-Agent System

We built 5 specialized agents that run alongside the Gemini conversation:

| Agent | Model | Role |
|-------|-------|------|
| **Gemini Live** | gemini-2.5-flash-native-audio | Primary voice + vision conversation |
| **Analyst** | gemini-2.5-flash | Background insight generation from frames |
| **Alert** | gemini-2.5-flash | Proactive anomaly detection (rate-limited) |
| **Memory** | — | Context storage in Firestore + in-memory |
| **Action Planner** | gemini-2.5-flash | Screenshot → action planning for desktop control |
| **Research** | gemini-2.5-flash + Google Search | Grounded web research with source attribution |

### Frontend

Built with React 18 + Zustand for state management. The UI is split into:
- **Camera/Screen view** with live status indicators and vignette overlay
- **Floating controls** for mute, camera flip, screen share, and disconnect
- **Conversation log** with real-time streaming and typing indicator
- **Insight cards** color-coded by category (anomaly, insight, suggestion, warning)
- **Alert panel** with slide-in notifications and auto-dismiss
- **Status bar** with connection state, session timer, and live indicator

### Deployment

Single Docker container (multi-stage build) deployed to Google Cloud Run:
- Stage 1: Node.js builds the React dashboard
- Stage 2: Python serves both the API and static files
- Auto-scales 0→3 instances, session affinity for WebSocket persistence
- Automated via `deploy/cloud-run.sh` script

---

## Challenges we ran into

**1. Gemini Live API is bleeding-edge.**
The model name, API version, and SDK methods changed during development. We went through `gemini-2.0-flash-live-001` → `gemini-2.5-flash-native-audio-latest`, discovered `v1alpha` was wrong (needed `v1beta`), and found that `client.aio.live.connect()` returns a context manager, not an awaitable. Each discovery required reworking the connection logic.

**2. Audio-only response modality.**
Gemini's native audio model can't combine `["AUDIO", "TEXT"]` response modalities. This meant the model could say "Sure, I'll click that for you" but couldn't output structured JSON action commands. We solved this by creating a separate Action Planner agent that uses Gemini 2.5 Flash's vision API to analyze screenshots and produce structured action plans independently.

**3. Multi-turn conversations kept dying.**
`session.receive()` exits after a single turn completes. Our first implementation only worked for one exchange. The fix was wrapping the receive iterator in a `while not closed` loop that re-enters the iterator after each turn.

**4. Real-time audio playback quality.**
Raw PCM chunks arriving out of order or with gaps caused clicking and popping. We implemented sequential playback scheduling using Web Audio API's `AudioBufferSourceNode` with precise `startTime` tracking to ensure smooth continuous audio.

**5. Desktop control on Wayland.**
PyAutoGUI relies on X11, but modern Linux uses Wayland. We implemented lazy importing to avoid crashes and used `xhost +local:` for X authorization, though full Wayland support remains a challenge.

---

## Accomplishments that we're proud of

- **True multimodal real-time interaction** — voice in, voice out, video in, all streaming simultaneously through a single WebSocket. No turn-taking, no upload-and-wait.
- **Background intelligence that works** — the Alert and Analyst agents run silently in the background and surface relevant information without being asked. It feels like having a vigilant assistant watching over your shoulder.
- **Desktop control through natural language** — telling your AI copilot "search for Ghana on Google" and watching it actually click the search bar, type the query, and press Enter is genuinely magical.
- **Single-container deployment** — one Docker image, one Cloud Run service, serves everything. Dashboard, API, WebSocket, all in one.
- **Zero to deployed in days** — from concept to a working, deployed, real-time multimodal AI agent on Google Cloud.

---

## What we learned

- The Gemini Live API is incredibly powerful for building real-time AI agents. Bidirectional audio + video streaming in a single persistent session is a game-changer.
- **Audio-only modality** means you need creative workarounds for structured output. Separate "planner" agents that work alongside the live session are an effective pattern.
- WebSocket lifecycle management is critical — every connection needs proper cleanup of async tasks, Gemini sessions, and state.
- Sequential audio scheduling with Web Audio API is the key to smooth playback of streaming PCM chunks.
- Google Cloud Run with session affinity handles WebSocket connections well, making serverless deployment viable for real-time applications.

---

## What's next for Nexus

- **Full Wayland/native desktop control** — using `ydotool` or platform-native APIs for reliable cross-platform desktop automation
- **Voice-triggered actions** — speech-to-intent pipeline so spoken commands (not just typed) can trigger desktop actions
- **Multi-session collaboration** — share a Nexus session with teammates for collaborative screen analysis
- **Plugin system** — let users add custom agents (Slack integration, Jira ticket creation, email drafting)
- **Mobile-native app** — React Native version with deeper camera and microphone integration
- **Persistent user profiles** — remember preferences, frequently used workflows, and learned patterns across sessions

---

## Built with

- Google Gemini Live API (gemini-2.5-flash-native-audio-latest)
- Google Gemini 2.5 Flash
- Google GenAI SDK (google-genai)
- Google Cloud Run
- Google Cloud Build
- Google Cloud Firestore
- FastAPI
- Python 3.11
- React 18
- TypeScript
- Vite
- Tailwind CSS
- Zustand
- WebSockets
- Web Audio API
- PyAutoGUI
- Docker

---

## Try it

**Live:** https://nexus-backend-cxotjai2ta-uc.a.run.app

**Run locally:**
```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add your GEMINI_API_KEY
uvicorn main:app --host 0.0.0.0 --port 8000

# Dashboard (separate terminal)
cd dashboard
npm install && npm run dev
```

**Deploy to Cloud Run:**
```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
export GEMINI_API_KEY=your-key
bash deploy/cloud-run.sh
```

---

## TODO before submission

- [ ] Record demo video (max 4 minutes) showing:
  - Starting a session from mobile/desktop
  - Voice conversation with camera pointed at something
  - Screen share + AI analysis
  - Desktop control via typed command
  - Background alerts and insights appearing
  - Cloud deployment proof (show Cloud Run console)
- [ ] Create architecture diagram (clean version of the ASCII one above)
- [ ] Push code to public GitHub repository
- [ ] Add screenshots to Devpost gallery
- [ ] Optional: Write a blog post about the build (+0.6 bonus points)
- [ ] Optional: Join Google Developer Group and link profile (+0.2 bonus points)
