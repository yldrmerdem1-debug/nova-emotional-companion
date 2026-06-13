# Nova Emotional Companion

Nova is a Turkish-first AI emotional companion prototype focused on reflective listening, mood journaling, privacy-aware memory, and a calm animated avatar experience.

This project was built as a full-stack AI product prototype: a FastAPI backend orchestrates emotional routing, memory, safety checks, local reasoning services, and response generation, while a React + Vite frontend provides a polished companion chat UI with support modes and a mood journal.

> Nova is not a therapist and is not intended to replace professional mental health care. It is designed as a supportive daily check-in and reflective journaling assistant.

## Why This Project Matters

Many AI chatbots answer questions, but emotional support products need a different interaction model. Nova focuses on:

- Listening before giving advice.
- Asking permission before moving into problem solving.
- Remembering support preferences such as "listen first", "think together", or "keep it brief".
- Avoiding manipulative or over-attached companion behavior.
- Providing crisis-safe language when self-harm or urgent risk appears.
- Keeping local/offline AI optional so the app can run on lower-end machines without heavy model load.

## Key Features

- **Three support modes:** Listen only, think together, and brief response.
- **Mood journal:** Tracks recent mood, intensity, and support preference from conversations.
- **Emotional memory:** Stores emotional patterns and care suggestions in a local JSONL store.
- **Safety guardrails:** Detects crisis/self-harm language and returns safer support guidance.
- **Privacy-aware behavior:** Supports memory-off boundaries and private-context logic.
- **Animated avatar:** Robot face adapts to emotional state, tone, eye contact, and motion.
- **Human feedback loop:** Users can rate responses and provide ideal corrections for future training.
- **Optional local LLM:** Ollama integration exists but is disabled by default to avoid overloading low-end PCs.

## Tech Stack

### Backend

- Python
- FastAPI
- Pydantic / pydantic-settings
- SQLAlchemy
- OpenAI-compatible service layer
- Optional Ollama local LLM integration
- Local JSONL memory stores
- Rule-based emotional routing and safety logic

### Frontend

- React
- TypeScript
- Vite
- CSS animated avatar

## Architecture Overview

```text
User Message
  -> Turkish brain router
  -> Support mode policy
  -> Deep memory + emotional memory
  -> Knowledge / reasoning / reflection services
  -> Response generation
  -> Safety review
  -> Mood journal + avatar state
```

## Product Positioning

Nova is positioned as a **Turkish emotional companion and mood journal**, not a therapy app.

Potential first markets:

- Students and young adults dealing with stress, loneliness, and exam pressure.
- University dorms or student communities as a low-pressure emotional check-in tool.
- Counseling centers as a between-session journaling assistant.
- Individual premium users who want private emotional journaling and memory.

## Repository Structure

```text
ai-companion-brain/
  backend/
    app/
      core/                 # Settings and persona definition
      services/             # Memory, emotion, safety, response generation
      routers/              # API routers
      ml/inference/         # Turkish brain routing helpers
      data/                 # Local knowledge and runtime data
    requirements.txt
  frontend/
    src/
      components/           # Chat panel and animated avatar
      api.ts                # API types and requests
      styles.css
    package.json
  docs/
    EMOTIONAL_COMPANION_MVP.md
  ROBOTU_BASLAT.bat         # Local Windows launcher
```

## Getting Started

### 1. Backend

```bash
cd backend
py -m pip install -r requirements.txt
py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

Open:

```text
http://localhost:5173
```

## Environment Variables

Create `backend/.env` from `backend/.env.example`.

```env
OPENAI_API_KEY=
DATABASE_URL=
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
LOCAL_LLM_PROVIDER=
LOCAL_LLM_BASE_URL=http://localhost:11434
LOCAL_LLM_MODEL=qwen2.5:7b
```

`LOCAL_LLM_PROVIDER` is intentionally empty by default. This keeps Ollama disabled unless the user explicitly turns it on.

## Safety Notes

Nova should be marketed carefully:

- Do not claim it provides therapy.
- Do not claim it can diagnose or treat mental health conditions.
- Do not claim it replaces psychologists, counselors, emergency services, or trusted people.
- Do present it as a daily emotional reflection and mood journaling companion.

## What I Built

This project demonstrates:

- Full-stack product thinking.
- Backend AI orchestration beyond a simple API wrapper.
- Emotional UX design and safe conversational defaults.
- Privacy-aware memory handling.
- Frontend state management and interactive UI design.
- Practical AI engineering tradeoffs, including disabling heavy local LLMs when they hurt user experience.

## Status

Prototype / portfolio project. The current focus is proving the emotional companion experience and product direction before polishing production infrastructure.
