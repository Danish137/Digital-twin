# Digital Twin

Digital Twin is a real-time voice assistant that acts like a conversational version of me(Danish). Built around a LiveKit-based voice pipeline and a custom browser UI, it is designed to feel like a natural live call.

## Architecture

The application is architected into decoupled microservices:

```
Vercel Frontend (frontend/index.html)
       │
       │ HTTPS POST /api/token
       ▼
Google Cloud Run — FastAPI Token API (backend/token_server)
       │
       │ LiveKit Room + Agent Dispatch
       ▼
LiveKit Cloud
       ▲
       │ WebRTC / Streaming Audio
       ▼
Dedicated LiveKit Agent Worker — Persistent VM (backend/agent)
 ├── Deepgram STT (Nova-3)
 ├── Groq LLM (Llama 3.3 70B)
 ├── Cartesia TTS (Sonic-3)
 └── Silero VAD
```

### Components

| Layer | Path | Responsibility | Deployment |
|---|---|---|---|
| **Frontend** | [`frontend/index.html`](frontend/index.html) | Browser UI, WebRTC audio, orb visuals, dynamic transcripts | Vercel |
| **Token API** | [`backend/token_server`](backend/token_server) | FastAPI HTTP service issuing LiveKit JWTs & agent dispatch | Google Cloud Run |
| **Agent Worker** | [`backend/agent`](backend/agent) | Long-running LiveKit worker handling STT → LLM → TTS pipeline | Persistent VM / Server |

---

## Repository Layout

```text
.
├── backend/
│   ├── token_server/
│   │   ├── main.py            # FastAPI token server & dispatch endpoint
│   │   ├── requirements.txt   # Minimal HTTP service dependencies
│   │   └── Dockerfile         # Stateless container for Cloud Run
│   └── agent/
│       ├── agent.py           # LiveKit voice worker runtime
│       ├── persona.json       # Agent personality schema
│       ├── facts.json         # Ground truth facts knowledge base
│       ├── requirements.txt   # LiveKit + ML/Audio pipeline dependencies
│       └── Dockerfile         # Persistent container for worker VM
├── frontend/
│   └── index.html             # Vanilla WebRTC frontend
├── .env.example               # Template for environment configuration
├── .gitignore
└── README.md
```
