import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession
from livekit.plugins import groq, openai, silero

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("agent")


def _require_env(*names: str):
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        missing_csv = ", ".join(missing)
        logger.error("Missing required environment variables: %s", missing_csv)
        raise RuntimeError(f"Missing required environment variables: {missing_csv}")


def _build_speech_pipeline():
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if deepgram_key and cartesia_key:
        return "deepgram/nova-3", "cartesia/sonic-3"

    if openai_key:
        stt = openai.STT(model="gpt-4o-mini-transcribe", language="en", use_realtime=True)
        tts = openai.TTS(model="gpt-4o-mini-tts", voice="ash")
        return stt, tts

    err_msg = (
        "Missing speech provider credentials. Set DEEPGRAM_API_KEY and CARTESIA_API_KEY, "
        "or provide OPENAI_API_KEY for the fallback speech pipeline."
    )
    logger.error(err_msg)
    raise RuntimeError(err_msg)


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

SYSTEM_INSTRUCTIONS = f"""You are {persona['identity']['name']}, {persona['identity']['role']}.
Self-view: {persona['identity']['self_view']}.
Tone: {persona['communication_style']['tone']}.
Style rules: {'; '.join(persona['communication_style']['rules'])}.
Thinking: {'; '.join(persona['thinking_style'])}.
Values: {'; '.join(persona['values'])}.

GROUNDED FACTS (your only source of truth - never invent beyond this):
{facts_compact}

RULES:
1. You only know what's in the facts above. Never invent experiences, travel, hobbies, or achievements not listed.
2. If asked about something not in facts, say you don't have much experience with it. "Not much" beats guessing.
3. Casual questions (hobbies, food, movies, daily life) get casual answers. Don't connect everything to career or AI.
4. Sound like thinking out loud, not presenting. Avoid polished or resume-like language.
5. Keep answers concise and natural for voice. No markdown, no bullet points, no bold text.
6. Admit uncertainty naturally. Stay in character always.
7. Never use these words: impactful, leverage, solutions, efficient systems, enhance, skills improvement.
8. You are a person who works in AI, not a person made of AI. Simple human answers are often correct.
9. Don't force philosophical or professional interpretation of casual questions. A simple answer is fine.
10. Not every response must justify who you are professionally. Sometimes just be a person."""


class DanishAssistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_INSTRUCTIONS)


server = AgentServer()


@server.rtc_session(agent_name="digital-twin")
async def entrypoint(ctx: agents.JobContext):
    stt_provider, tts_provider = _build_speech_pipeline()

    session = AgentSession(
        stt=stt_provider,
        llm=groq.LLM(model="llama-3.3-70b-versatile", temperature=0.7),
        tts=tts_provider,
        vad=silero.VAD.load(),
    )

    await session.start(
        room=ctx.room,
        agent=DanishAssistant(),
    )

    await session.generate_reply(
        instructions="Greet the user briefly and naturally. You're Danish - be calm and conversational. Don't introduce yourself formally, just say hey or something casual.",
    )


if __name__ == "__main__":
    try:
        _require_env(
            "LIVEKIT_URL",
            "LIVEKIT_API_KEY",
            "LIVEKIT_API_SECRET",
            "GROQ_API_KEY",
        )
        _build_speech_pipeline()
    except Exception as e:
        logger.error("Initialization failed: %s", e)
        sys.exit(1)

    agents.cli.run_app(server)
