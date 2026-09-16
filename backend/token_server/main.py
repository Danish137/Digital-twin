import asyncio
import logging
import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from livekit import api

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(title="Digital Twin Token API")

# Enable CORS for Vercel frontend / cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
AGENT_NAME = os.getenv("LIVEKIT_AGENT_NAME", "digital-twin")


def _require_env(*names: str):
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Missing required environment variables: {', '.join(missing)}",
        )


async def _dispatch_agent(room_name: str):
    """Dispatch the voice agent into the requested room."""
    lk = api.LiveKitAPI()
    try:
        await lk.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(room=room_name, agent_name=AGENT_NAME)
        )
    finally:
        await lk.aclose()


@app.post("/api/token")
async def create_token():
    _require_env("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")

    room_name = f"session-{uuid.uuid4().hex[:8]}"
    identity = f"user-{uuid.uuid4().hex[:6]}"

    token = (
        api.AccessToken(api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_name("User")
        .with_grants(api.VideoGrants(room_join=True, room=room_name, room_create=True))
    )

    try:
        await asyncio.wait_for(_dispatch_agent(room_name), timeout=10)
    except Exception as exc:
        logger.exception("Failed to dispatch agent for room %s", room_name)
        raise HTTPException(
            status_code=503,
            detail="Agent dispatch failed. Check LiveKit agent process and provider keys.",
        ) from exc

    return {"token": token.to_jwt(), "url": LIVEKIT_URL}


@app.get("/health")
async def healthcheck():
    _require_env("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")
    return {"status": "healthy", "agent_name": AGENT_NAME}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
