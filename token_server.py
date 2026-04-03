import asyncio
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from livekit import api

load_dotenv()

app = FastAPI()

LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")


async def _dispatch_agent(room_name: str):
    """Fire-and-forget: dispatch the agent after the token is already returned."""
    lk = api.LiveKitAPI()
    try:
        await lk.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(room=room_name, agent_name="digital-twin")
        )
    finally:
        await lk.aclose()


@app.post("/api/token")
async def create_token():
    room_name = f"session-{uuid.uuid4().hex[:8]}"
    identity = f"user-{uuid.uuid4().hex[:6]}"

    token = (
        api.AccessToken(api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_name("User")
        .with_grants(api.VideoGrants(room_join=True, room=room_name, room_create=True))
    )

    # Dispatch agent in background — don't block the token response
    asyncio.create_task(_dispatch_agent(room_name))

    return {"token": token.to_jwt(), "url": LIVEKIT_URL}


@app.get("/")
async def serve_frontend():
    return FileResponse(Path(__file__).parent / "frontend" / "index.html")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port)
