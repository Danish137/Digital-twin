import asyncio
import logging
import os
import time
import uuid
import jwt

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx2 as httpx

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

@app.middleware("http")
async def sync_env_middleware(request, call_next):
    env_bindings = request.scope.get("env")
    if env_bindings:
        for k in ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "LIVEKIT_AGENT_NAME"]:
            try:
                val = None
                if hasattr(env_bindings, k):
                    val = getattr(env_bindings, k)
                elif hasattr(env_bindings, "get"):
                    val = env_bindings.get(k)
                if val and isinstance(val, str):
                    os.environ[k] = val
            except Exception:
                pass
    return await call_next(request)


def _get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _require_env(*names: str):
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Missing required environment variables: {', '.join(missing)}",
        )

def _generate_livekit_token(api_key: str, api_secret: str, room_name: str, identity: str) -> str:
    """Generate a standard LiveKit JWT without using the livekit-api package."""
    now = int(time.time())
    payload = {
        "exp": now + 3600,
        "iss": api_key,
        "sub": identity,
        "name": "User",
        "video": {
            "roomJoin": True,
            "room": room_name,
            "roomCreate": True
        }
    }
    return jwt.encode(payload, api_secret, algorithm="HS256")

async def _dispatch_agent(room_name: str, api_key: str, api_secret: str, livekit_url: str, agent_name: str):
    """Dispatch the voice agent into the requested room via LiveKit Twirp API."""
    http_url = livekit_url.replace("wss://", "https://").replace("ws://", "http://").rstrip("/")
    url = f"{http_url}/twirp/livekit.AgentDispatchService/CreateDispatch"

    # For admin token, we need roomAdmin=True
    now = int(time.time())
    admin_payload = {
        "exp": now + 3600,
        "iss": api_key,
        "sub": "admin",
        "video": {
            "roomAdmin": True,
            "room": room_name
        }
    }
    admin_token = jwt.encode(admin_payload, api_secret, algorithm="HS256")

    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "room": room_name,
        "agent_name": agent_name,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            logger.error("LiveKit dispatch returned status %d: %s", resp.status_code, resp.text)
            resp.raise_for_status()


@app.post("/api/token")
async def create_token():
    _require_env("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")
    
    livekit_url = os.environ["LIVEKIT_URL"]
    api_key = os.environ["LIVEKIT_API_KEY"]
    api_secret = os.environ["LIVEKIT_API_SECRET"]
    agent_name = _get_env("LIVEKIT_AGENT_NAME", "digital-twin-agent")

    room_name = f"session-{uuid.uuid4().hex[:8]}"
    identity = f"user-{uuid.uuid4().hex[:6]}"

    token = _generate_livekit_token(api_key, api_secret, room_name, identity)

    try:
        await asyncio.wait_for(_dispatch_agent(room_name, api_key, api_secret, livekit_url, agent_name), timeout=10)
    except Exception as exc:
        logger.exception("Failed to dispatch agent for room %s", room_name)
        raise HTTPException(
            status_code=503,
            detail="Agent dispatch failed. Check LiveKit agent process and provider keys.",
        ) from exc

    return {"token": token, "url": livekit_url}


@app.get("/health")
async def healthcheck():
    _require_env("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")
    return {"status": "healthy", "agent_name": _get_env("LIVEKIT_AGENT_NAME", "digital-twin-agent")}


# Cloudflare Python Worker entrypoint
try:
    from workers import asgi
    Default = asgi.entrypoint(app)
except (ImportError, ModuleNotFoundError):
    Default = None


if __name__ == "__main__":
    import uvicorn
    # Make sure we import dotenv here for local Uvicorn runs only
    try:
        from dotenv import load_dotenv
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
        load_dotenv(env_path)
    except ImportError:
        pass

    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
