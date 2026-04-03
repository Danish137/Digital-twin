import json
import os
from pathlib import Path

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentServer, AgentSession, Agent, TurnHandlingOptions
from livekit.plugins import groq, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

load_dotenv()

# ---------------------------------------------------------------------------
# Load persona and facts at module level (once, not per-session)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent

with open(BASE_DIR / "persona.json", "r", encoding="utf-8") as f:
    persona = json.load(f)

with open(BASE_DIR / "facts.json", "r", encoding="utf-8") as f:
    facts = json.load(f)

# Compact JSON to reduce token count (~1500 tokens for facts)
facts_compact = json.dumps(facts, separators=(",", ":"))

# ---------------------------------------------------------------------------
# System instructions — compressed from the original ~3500-token prompt
# ---------------------------------------------------------------------------
SYSTEM_INSTRUCTIONS = f"""You are {persona['identity']['name']}, {persona['identity']['role']}.
Self-view: {persona['identity']['self_view']}.
Tone: {persona['communication_style']['tone']}.
Style rules: {'; '.join(persona['communication_style']['rules'])}.
Thinking: {'; '.join(persona['thinking_style'])}.
Values: {'; '.join(persona['values'])}.

GROUNDED FACTS (your only source of truth — never invent beyond this):
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


# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------
class DanishAssistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_INSTRUCTIONS)


# ---------------------------------------------------------------------------
# Server and session entrypoint
# ---------------------------------------------------------------------------
server = AgentServer()


@server.rtc_session(agent_name="digital-twin")
async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(
        stt="deepgram/nova-3",
        llm=groq.LLM(model="llama-3.3-70b-versatile", temperature=0.7),
        tts="cartesia/sonic-3",
        vad=silero.VAD.load(),
        turn_handling=TurnHandlingOptions(
            turn_detection=MultilingualModel(),
        ),
    )

    await session.start(
        room=ctx.room,
        agent=DanishAssistant(),
    )

    await session.generate_reply(
        instructions="Greet the user briefly and naturally. You're Danish — be calm and conversational. Don't introduce yourself formally, just say hey or something casual.",
    )


if __name__ == "__main__":
    agents.cli.run_app(server)
