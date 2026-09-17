import io
import json
import logging
import os
import sys
import time
from pathlib import Path

import av
import edge_tts
from dotenv import load_dotenv
from livekit import agents, rtc
from livekit.agents import Agent, AgentServer, AgentSession
from livekit.agents.tts import tts as tts_base
from livekit.agents.types import APIConnectOptions
from livekit.plugins import groq, silero

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("agent")

# ---------------------------------------------------------------------------
# Edge TTS adapter
# ---------------------------------------------------------------------------

EDGE_TTS_VOICE = "en-IN-PrabhatNeural"
EDGE_TTS_SAMPLE_RATE = 24000
EDGE_TTS_CHANNELS = 1


class EdgeTTSChunkedStream(tts_base.ChunkedStream):
    """ChunkedStream implementation backed by edge-tts + PyAV MP3 decode."""

    def __init__(
        self,
        *,
        tts: "EdgeTTS",
        input_text: str,
        voice: str,
        conn_options: APIConnectOptions,
    ) -> None:
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._voice = voice

    async def _run(self, output_emitter: tts_base.AudioEmitter) -> None:
        request_id = agents.utils.shortuuid()
        output_emitter.initialize(
            request_id=request_id,
            sample_rate=EDGE_TTS_SAMPLE_RATE,
            num_channels=EDGE_TTS_CHANNELS,
            mime_type="audio/pcm",
            stream=False,
        )

        try:
            t0 = time.perf_counter()
            first_chunk_time = None
            first_pcm_time = None
            communicate = edge_tts.Communicate(self._input_text, self._voice)
            codec = av.CodecContext.create("mp3", "r")
            resampler = av.AudioResampler(
                format="s16",
                layout="mono",
                rate=EDGE_TTS_SAMPLE_RATE,
            )
            has_audio = False

            # Incrementally parse MP3 chunks as they stream from edge-tts
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    has_audio = True
                    if first_chunk_time is None:
                        first_chunk_time = time.perf_counter() - t0
                        logger.info("Edge TTS TTFB: %.1fms for text: %r", first_chunk_time * 1000, self._input_text[:50])
                    for packet in codec.parse(chunk["data"]):
                        for frame in codec.decode(packet):
                            for rs_frame in resampler.resample(frame):
                                pcm_bytes = rs_frame.to_ndarray().tobytes()
                                if pcm_bytes:
                                    if first_pcm_time is None:
                                        first_pcm_time = time.perf_counter() - t0
                                        logger.info("Edge TTS first PCM frame: %.1fms", first_pcm_time * 1000)
                                    output_emitter.push(pcm_bytes)

            if not has_audio:
                logger.warning("edge-tts returned no audio for text: %r", self._input_text[:80])
                output_emitter.flush()
                return

            # Flush codec parser
            for packet in codec.parse(b""):
                for frame in codec.decode(packet):
                    for rs_frame in resampler.resample(frame):
                        pcm_bytes = rs_frame.to_ndarray().tobytes()
                        if pcm_bytes:
                            output_emitter.push(pcm_bytes)

            # Flush remaining decoded frames from codec
            for frame in codec.decode(None):
                for rs_frame in resampler.resample(frame):
                    pcm_bytes = rs_frame.to_ndarray().tobytes()
                    if pcm_bytes:
                        output_emitter.push(pcm_bytes)

            # Flush resampler buffer
            for rs_frame in resampler.resample(None):
                pcm_bytes = rs_frame.to_ndarray().tobytes()
                if pcm_bytes:
                    output_emitter.push(pcm_bytes)

            output_emitter.flush()

        except edge_tts.exceptions.NoAudioReceived as exc:
            logger.error("edge-tts: no audio received for voice=%s: %s", self._voice, exc)
            raise
        except Exception as exc:
            logger.error("edge-tts synthesis failed: %s", exc, exc_info=True)
            raise


class EdgeTTS(tts_base.TTS):
    """Minimal LiveKit TTS implementation using Microsoft Edge TTS (edge-tts)."""

    def __init__(self, *, voice: str = EDGE_TTS_VOICE) -> None:
        super().__init__(
            capabilities=tts_base.TTSCapabilities(streaming=False),
            sample_rate=EDGE_TTS_SAMPLE_RATE,
            num_channels=EDGE_TTS_CHANNELS,
        )
        self._voice = voice

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = tts_base.DEFAULT_API_CONNECT_OPTIONS,
    ) -> EdgeTTSChunkedStream:
        return EdgeTTSChunkedStream(
            tts=self,
            input_text=text,
            voice=self._voice,
            conn_options=conn_options,
        )


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------


def _require_env(*names: str):
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        missing_csv = ", ".join(missing)
        logger.error("Missing required environment variables: %s", missing_csv)
        raise RuntimeError(f"Missing required environment variables: {missing_csv}")


def _build_speech_pipeline():
    groq_key = os.getenv("GROQ_API_KEY")

    if groq_key:
        stt = groq.STT(model="whisper-large-v3-turbo", language="en")
        tts = EdgeTTS(voice=EDGE_TTS_VOICE)
        return stt, tts

    raise RuntimeError("Missing GROQ_API_KEY — required for STT.")


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
    await ctx.connect()
    stt_provider, tts_provider = _build_speech_pipeline()

    session = AgentSession(
        stt=stt_provider,
        llm=groq.LLM(model="qwen/qwen3.8-27b", temperature=0.7),
        tts=tts_provider,
        vad=silero.VAD.load(
            min_speech_duration=0.15,
            min_silence_duration=0.3,
        ),
        turn_handling={
            "preemptive_generation": {"enabled": False},
            "endpointing": {
                "min_delay": 0.35,
                "max_delay": 0.8,
            },
            "interruption": {
                "enabled": True,
                "discard_audio_if_uninterruptible": True,
                "resume_false_interruption": False,
                "min_duration": 0.25,
            },
        },
    )

    await session.start(
        room=ctx.room,
        agent=DanishAssistant(),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

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
