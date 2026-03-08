# Nexus

**Point. Ask. Know.**

Real-time voice + vision AI copilot powered by Google's Gemini Live API. Nexus lets you point your camera or share your screen, speak naturally, and get intelligent answers grounded in what you see — all in real time.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                       Browser                           │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────────┐ │
│  │  Camera   │  │   Mic    │  │    Screen Share       │ │
│  └────┬─────┘  └────┬─────┘  └──────────┬────────────┘ │
│       └──────────────┼───────────────────┘              │
│                      │  WebSocket                       │
└──────────────────────┼──────────────────────────────────┘
                       │
              ┌────────▼────────┐
              │   FastAPI        │
              │   Backend        │
              │                  │
              │  ┌────────────┐  │      ┌────────────────┐
              │  │  Session    │  │      │                │
              │  │  Manager    │◄─┼──────│   Redis        │
              │  └────────────┘  │      │                │
              │                  │      └────────────────┘
              │  ┌────────────┐  │
              │  │  Agent      │  │
              │  │  Router     │  │
              │  └──┬───┬──┬──┘  │
              │     │   │  │     │
              └─────┼───┼──┼─────┘
                    │   │  │
         ┌──────────┘   │  └──────────┐
         ▼              ▼             ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐
   │ Analyst  │  │ Research │  │  Memory  │
   │  Agent   │  │  Agent   │  │  Agent   │
   └────┬─────┘  └────┬─────┘  └────┬─────┘
        │              │             │
        └──────────────┼─────────────┘
                       │
              ┌────────▼────────┐
              │  Gemini Live    │
              │  API            │
              │  (2.0 Flash)    │
              └─────────────────┘
```

## Features

- **Camera Access** — Point your device camera at anything and ask questions about it
- **Real-Time Voice Streaming** — Speak naturally; responses stream back as audio
- **Screen Share** — Share your screen for code review, document analysis, and more
- **Mobile Support** — Responsive UI works on phones and tablets
- **Proactive Alerts** — The Alert agent monitors your stream and flags issues
- **Persistent Memory** — Memory agent retains context across sessions via Firestore
- **Research Grounding** — Research agent augments answers with web-grounded data
- **Multi-Agent Routing** — Requests are routed to specialized agents based on intent

## Use Cases

- **Data Analysis** — Point at charts, dashboards, or spreadsheets and ask for insights
- **Code Review** — Share your screen and get real-time feedback on code
- **Document Understanding** — Hold up a document and ask questions about its contents
- **Real-World Scanning** — Identify objects, read labels, translate text from your camera
- **Learning & Tutoring** — Point at a textbook problem and get step-by-step explanations
- **Accessibility** — Describe surroundings for visually impaired users

## Prerequisites

| Requirement       | Version   |
| ----------------- | --------- |
| Python            | 3.11+     |
| Node.js           | 18+       |
| Gemini API Key    | —         |
| GCP Project       | —         |
| Docker (optional) | 24+       |

## Environment Variables

| Variable               | Required | Description                          | Default          |
| ---------------------- | -------- | ------------------------------------ | ---------------- |
| `GEMINI_API_KEY`       | Yes      | Google Gemini API key                | —                |
| `GOOGLE_CLOUD_PROJECT` | Yes      | GCP project ID                       | —                |
| `REDIS_URL`            | No       | Redis connection URL                 | `redis://localhost:6379/0` |
| `HOST`                 | No       | Backend bind host                    | `0.0.0.0`        |
| `PORT`                 | No       | Backend bind port                    | `8080`           |
| `LOG_LEVEL`            | No       | Logging level                        | `info`           |
| `ALLOWED_ORIGINS`      | No       | CORS origins (comma-separated)       | `*`              |

## Quick Start

### Option A: Docker Compose

```bash
# 1. Clone the repo
git clone <repo-url> nexus && cd nexus

# 2. Configure backend environment
cp backend/.env.example backend/.env
# Edit backend/.env and set GEMINI_API_KEY and GOOGLE_CLOUD_PROJECT

# 3. Start backend + Redis
docker compose up -d

# 4. Start the dashboard (in a separate terminal)
cd dashboard
npm install
npm run dev
```

The backend runs at `http://localhost:8000` and the dashboard at `http://localhost:5173`.

### Option B: Manual Setup

```bash
# 1. Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set GEMINI_API_KEY and GOOGLE_CLOUD_PROJECT
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# 2. Redis (separate terminal)
docker run -d -p 6379:6379 redis:7-alpine

# 3. Dashboard (separate terminal)
cd dashboard
npm install
npm run dev
```

## GCP Deployment

Deploy the backend to Google Cloud Run:

```bash
export GEMINI_API_KEY="your-key"
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Optional overrides
export REGION="us-central1"
export SERVICE_NAME="nexus-backend"
export REDIS_URL="redis://your-redis-host:6379/0"

./deploy/cloud-run.sh
```

The script enables required APIs, builds the container image via Cloud Build, and deploys to Cloud Run with WebSocket support, session affinity, and auto-scaling (0-3 instances).

For the dashboard, deploy the built static files to Firebase Hosting, Vercel, or any static hosting provider:

```bash
cd dashboard
npm run build
# Upload dist/ to your hosting provider
```

## Tech Stack

| Layer     | Technology                        |
| --------- | --------------------------------- |
| Frontend  | React 18, Vite, Tailwind CSS      |
| Backend   | FastAPI, Python 3.11, WebSockets  |
| AI        | Gemini Live API (2.0 Flash)       |
| Cache     | Redis 7                           |
| Database  | Google Firestore                  |
| Hosting   | Google Cloud Run                  |
| Build     | Docker, Cloud Build               |

## Agent Architecture

| Agent    | Role                                                              | Trigger                                      |
| -------- | ----------------------------------------------------------------- | -------------------------------------------- |
| Analyst  | Interprets visual input (camera/screen) and answers questions     | Default for all vision + voice queries        |
| Research | Augments answers with web-grounded data via Gemini search tools   | Queries requiring external knowledge          |
| Memory   | Stores and retrieves context from Firestore across sessions       | References to past conversations or follow-ups|
| Alert    | Monitors the video stream and proactively flags anomalies/issues  | Continuous background monitoring              |

## Demo Scenarios

1. **Chart Analysis** — Open a financial dashboard, share your screen, and ask: "What trend do you see in Q3 revenue?"
2. **Code Review** — Share your IDE and ask: "Are there any bugs in this function?"
3. **Document Scan** — Hold a receipt up to your camera and ask: "Summarize the line items and total."
4. **Object Identification** — Point your phone camera at a plant and ask: "What species is this?"
5. **Proactive Alert** — Share a server monitoring dashboard; Nexus alerts you when a metric spikes.

---

Built for the **Gemini Live Agent Challenge**.
