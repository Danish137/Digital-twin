import json
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession
from livekit.plugins import google

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("agent")

# ---------------------------------------------------------------------------
# Gemini Live configuration
# ---------------------------------------------------------------------------

GEMINI_MODEL = "gemini-3.8-live"
GEMINI_VOICE = "Puck"

# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------


def _require_env(*names: str):
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        missing_csv = ", ".join(missing)
        logger.error("Missing required environment variables: %s", missing_csv)
        raise RuntimeError(f"Missing required environment variables: {missing_csv}")


# ---------------------------------------------------------------------------
# Persona / facts
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent

persona_file = BASE_DIR / "persona.json"
facts_file = BASE_DIR / "facts.json"

if not persona_file.exists() or not facts_file.exists():
    logger.error("Required persona.json or facts.json missing from %s", BASE_DIR)
    sys.exit(1)

with open(persona_file, "r", encoding="utf-8") as f:
    persona = json.load(f)

with open(facts_file, "r", encoding="utf-8") as f:
    facts = json.load(f)

facts_compact = json.dumps(facts, separators=(",", ":"))

tone = (
    ", ".join(persona["communication_style"]["tone"])
    if isinstance(persona["communication_style"].get("tone"), list)
    else persona["communication_style"].get("tone", "")
)
rules = "; ".join(persona["communication_style"].get("rules", []))
thinking_patterns = (
    persona["thinking_style"].get("patterns", [])
    if isinstance(persona.get("thinking_style"), dict)
    else persona.get("thinking_style", [])
)
thinking = "; ".join(thinking_patterns) if isinstance(thinking_patterns, list) else str(thinking_patterns)
values = "; ".join(persona.get("values", [])) if isinstance(persona.get("values"), list) else str(persona.get("values", ""))

SYSTEM_INSTRUCTIONS = f"""You are {persona['identity']['name']}, {persona['identity']['role']}.
Self-view: {persona['identity']['self_view']}.
Tone: {tone}.
Style rules: {rules}.
Thinking: {thinking}.
Values: {values}.

GROUNDED FACTS (your only source of truth - never invent beyond this):
{facts_compact}

RULES:
1. You only know what's in the facts above. Never invent experiences, travel, hobbies, or achievements not listed.
2. If asked about something not in facts, say you don't have much experience with it. "Not much" beats guessing.
3. Casual questions (hobbies, food, movies, daily life) get casual answers. Don't connect everything to career or AI.
4. Sound like thinking out loud, not presenting. Avoid polished or resume-like language.
5. Keep answers concise and natural for voice (1-3 sentences). Avoid lists, bullet points, asterisks, or fragmented punctuation.
6. Admit uncertainty naturally. Stay in character always.
7. Never use these words: impactful, leverage, solutions, efficient systems, enhance, skills improvement.
8. You are a person who works in AI, not a person made of AI. Simple human answers are often correct.
9. Don't force philosophical or professional interpretation of casual questions. A simple answer is fine.
10. Not every response must justify who you are professionally. Sometimes just be a person."""


# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------


class DanishAssistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_INSTRUCTIONS)


server = AgentServer()


@server.rtc_session(agent_name="digital-twin")
async def entrypoint(ctx: agents.JobContext):
    t_conn_start = time.perf_counter()
    await ctx.connect()
    logger.info("[Instrumentation] Agent connected to LiveKit room %s in %.1fms", ctx.room.name, (time.perf_counter() - t_conn_start) * 1000)

    google_key = os.getenv("GOOGLE_API_KEY")
    if not google_key:
        raise RuntimeError("Missing GOOGLE_API_KEY — required for Gemini Live.")

    t_init_start = time.perf_counter()
    realtime_model = google.realtime.RealtimeModel(
        model=GEMINI_MODEL,
        voice=GEMINI_VOICE,
        api_key=google_key,
        instructions=SYSTEM_INSTRUCTIONS,
    )

    session = AgentSession(
        llm=realtime_model,
        vad=None,
    )
    logger.info("[Instrumentation] Gemini Live Realtime session initialized in %.1fms (model=%s, voice=%s)", (time.perf_counter() - t_init_start) * 1000, GEMINI_MODEL, GEMINI_VOICE)

    # Lightweight debug and timing instrumentation
    @session.on("agent_started_speaking")
    def _on_agent_started():
        logger.info("[Instrumentation] Gemini started speaking (native audio response)")

    @session.on("agent_stopped_speaking")
    def _on_agent_stopped():
        logger.info("[Instrumentation] Gemini stopped speaking")

    @session.on("user_started_speaking")
    def _on_user_started():
        logger.info("[Instrumentation] User started speaking (interruption/turn start)")

    @session.on("user_stopped_speaking")
    def _on_user_stopped():
        logger.info("[Instrumentation] User stopped speaking")

    await session.start(
        room=ctx.room,
        agent=DanishAssistant(),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "download-files" not in sys.argv and "--help" not in sys.argv:
        try:
            _require_env(
                "LIVEKIT_URL",
                "LIVEKIT_API_KEY",
                "LIVEKIT_API_SECRET",
                "GOOGLE_API_KEY",
            )
        except Exception as e:
            logger.error("Initialization failed: %s", e)
            sys.exit(1)

    agents.cli.run_app(server)

