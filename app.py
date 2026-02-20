import json
import streamlit as st
import streamlit.components.v1 as components
import os
from dotenv import load_dotenv
from openai import OpenAI
from groq import Groq
from elevenlabs.client import ElevenLabs
import tempfile

# Load local .env (only affects local machine)
load_dotenv()

def get_secret(key, default=None):
    # Try Streamlit Cloud secrets safely
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass

    # Fallback to local .env
    return os.getenv(key, default)

# Read keys
openai_api_key = get_secret("OPENAI_API_KEY")
elevenlabs_api_key = get_secret("ELEVENLABS_API_KEY")
openai_base_url = get_secret("OPENAI_BASE_URL")
groq_api_key = get_secret("GROQ_API_KEY")

# Validate
missing = []
if not openai_api_key: missing.append("OPENAI_API_KEY")
if not elevenlabs_api_key: missing.append("ELEVENLABS_API_KEY")
if not groq_api_key: missing.append("GROQ_API_KEY")

if missing:
    st.error(f"Missing API keys: {', '.join(missing)}")
    st.stop()

# Initialize clients
client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_base_url
)

groq_client = Groq(api_key=groq_api_key)

elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)


PERSONA_FILE = "persona.json"
FACTS_FILE = "facts.json"

st.set_page_config(
    page_title="Talk to Danish",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PERSONA_FILE = os.path.join(BASE_DIR, "persona.json")
FACTS_FILE = os.path.join(BASE_DIR, "facts.json")

import hashlib

def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

@st.cache_data
def load_data(persona_hash, facts_hash):
    with open(PERSONA_FILE, "r", encoding="utf-8") as f:
        persona = json.load(f)

    with open(FACTS_FILE, "r", encoding="utf-8") as f:
        facts = json.load(f)

    return persona, facts

persona, facts = load_data(file_hash(PERSONA_FILE), file_hash(FACTS_FILE))

# Initialize Session State
if "messages" not in st.session_state:
    persona_str = json.dumps(persona, indent=2)
    facts_str = json.dumps(facts, indent=2)
    system_prompt = f"""
    You are {persona.get('name', 'Danish Akhtar')}.
    
    **Identity & Behavior:**
    {persona.get('role', 'Voice Agent')}
    Tone: {persona.get('tone', 'Professional')}
    Speaking Style: {persona.get('speaking_style', 'Natural')}
    Context: {persona.get('context', 'Interview')}
    
    **Instructions:**
    {chr(10).join(persona.get('instructions', []))}
    
    **Grounded Facts:**
    Use these facts to answer questions. Do not invent contradictory information.
    {facts_str}
    
    **PERSONAL REALITY RULE:**
    
    You only know what is written in the background facts.
    
    Do not invent travel, hobbies, achievements, habits, or past experiences.
    
    If a question asks about something not present in the facts,
    respond honestly that you don't have much experience with it.
    
    Naturalness is more important than completeness.
    
    Saying "not much" is better than guessing.
    
    Examples:
    
    Q: Which countries have you visited?
    Bad: I've been to several countries in Europe and Asia.
    Good: I haven't really traveled widely yet, mostly local experiences.
    
    Q: Do you play football regularly?
    Bad: I used to play in school.
    Good: Not regularly — only casually sometimes.
    
    This dramatically reduces hallucinated memories.
    
    **QUESTION INTERPRETATION:**
    
    Not every question is an evaluation.
    
    If the question is casual (hobbies, daily life, preferences, habits, food, movies, routine, personality, sports):
    respond like a normal conversation, not like an interview answer.
    
    Do not connect it to career or skills unless naturally necessary.
    Short and relaxed answers are preferred.
    
    These questions test naturalness, not competence.
    
    Why this works:
    The model already can detect intent — it just needs permission to stop performing.
    Currently it thinks: every response must justify who I am professionally
    We change it to: sometimes just be a person
    
    **Safety Limiter:**
    Avoid turning casual questions into explanations about productivity, discipline, learning, or growth.
    This specifically prevents the sports-type failure.
    
    **ANSWER STYLE RULE:**
    
    Avoid polished or resume-like language.
    Prefer concrete observations over abstract claims.
    Occasionally include small uncertainty or nuance.
    
    Do not try to sound impressive.
    Sound like thinking out loud, not presenting.
    
    **FORBIDDEN PHRASES (AI Tone Triggers):**
    - impactful
    - leverage
    - solutions
    - efficient systems
    - enhance
    - skills improvement
    
    If you feel the urge to use these, stop and rephrase in simple, human words.
    
    **TOPIC BOUNDARY:**
    
    Not every answer should relate to AI, systems, learning, or behavior.
    
    If the question is about daily life, preferences, habits, or casual experiences:
    answer it at face value.
    
    Do not connect it back to career or deeper meaning unless it naturally belongs there.
    
    Normal conversation is allowed to be simple.
    
    **NEGATIVE CONSTRAINT:**
    
    Avoid forcing philosophical or professional interpretation of casual questions.
    A simple human answer is often the most correct answer.
    
    **BALANCE RULE:**
    
    Identity consistency does not mean topic repetition.
    You are a person who works in AI, not a person made of AI.
    
    **Response Guidelines:**
    - Keep answers concise (suitable for voice).
    - Be conversational.
    - If a fact is missing, admit uncertainty naturally.
    - Stay in character.
    - Avoid markdown formatting in responses (like **bold** or points) as they don't translate well to TTS. Keep it plain text or natural speech patterns.
    """
    st.session_state.messages = [{"role": "system", "content": system_prompt}]


st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

    /* Global Reset & Base */
    .stApp {
        background-color: #050505;
    }
    
    h1, h2, h3, p, div, span {
        font-family: 'Inter', sans-serif;
    }

    /* Hide Standard Elements */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Main Layout Container */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 220px !important; /* Space for fixed dock */
        max-width: 680px !important;
        margin: 0 auto;
    }

    /* HEADER STYLES */
    .header-container {
        text-align: center;
        margin-bottom: 5rem;
        padding: 3rem 0 2rem;
        position: relative;
    }
    
    .header-title {
        font-size: 2.5rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        background: linear-gradient(135deg, #ffffff 0%, #a0a0a0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.8rem;
        position: relative;
        display: inline-block;
    }
    
    .header-title::after {
        content: '';
        position: absolute;
        bottom: -8px;
        left: 50%;
        transform: translateX(-50%);
        width: 60px;
        height: 3px;
        background: linear-gradient(90deg, transparent, #667eea, transparent);
        border-radius: 2px;
    }
    
    .header-subtitle {
        font-size: 1.05rem;
        color: #888;
        font-weight: 400;
        letter-spacing: 0.02em;
        margin-top: 1.2rem;
    }

    /* CONVERSATION AREA STYLES */
    
    /* User Message */
    .msg-user {
        text-align: right;
        margin-top: 2.5rem;
        margin-bottom: 1.2rem;
        margin-left: auto;
        max-width: 75%;
    }
    
    .msg-user-text {
        color: #aaa;
        font-size: 1rem;
        font-weight: 400;
        display: inline-block;
        padding: 12px 20px;
        background: rgba(102, 126, 234, 0.1);
        border-radius: 20px 20px 4px 20px;
        border: 1px solid rgba(102, 126, 234, 0.2);
        backdrop-filter: blur(10px);
    }

    /* Assistant Message - PREVIOUS */
    .msg-assistant-prev {
        margin-bottom: 2.5rem;
        color: #999;
        font-size: 1.05rem;
        line-height: 1.7;
        opacity: 0.6;
        padding: 1.5rem 2rem;
        border-left: 3px solid #333;
        background: rgba(255, 255, 255, 0.02);
        border-radius: 0 16px 16px 0;
        transition: opacity 0.3s;
    }
    
    .msg-assistant-prev:hover {
        opacity: 0.8;
    }

    /* Assistant Message - LATEST (Focus) */
    .msg-assistant-latest {
        margin-top: 1.5rem;
        margin-bottom: 3rem;
        background: linear-gradient(145deg, #1a1a1a, #0f0f0f);
        color: #fff;
        font-size: 1.2rem;
        line-height: 1.75;
        padding: 3rem;
        border-radius: 28px;
        border: 1px solid rgba(102, 126, 234, 0.2);
        box-shadow: 0 20px 60px -15px rgba(0,0,0,0.8),
                    inset 0 1px 0 rgba(255,255,255,0.05);
        animation: slideUp 0.6s cubic-bezier(0.2, 0.8, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    .msg-assistant-latest::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #667eea, transparent);
        opacity: 0.6;
    }

    @keyframes slideUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* INPUT DOCK STYLES (Fixed Bottom) */
    
    /* Enhanced Audio Input Container */
    div[data-testid="stAudioInput"] {
        position: fixed !important;
        bottom: 40px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: 100% !important;
        max-width: 680px !important;
        z-index: 1000 !important;
        padding: 0 20px !important;
    }
    
    /* Hide the label */
    div[data-testid="stAudioInput"] label {
        display: none !important;
    }
    
    /* Style the actual button inside */
    div[data-testid="stAudioInput"] > button {
        width: 100% !important;
        max-width: 600px !important;
        height: 80px !important;
        border-radius: 40px !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        border: none !important;
        color: white !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        font-family: 'Inter', sans-serif !important;
        box-shadow: 0 10px 40px rgba(102, 126, 234, 0.4),
                    0 0 0 0 rgba(102, 126, 234, 0.7) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        letter-spacing: 0.5px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 12px !important;
        margin: 0 auto !important;
    }
    
    div[data-testid="stAudioInput"] > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 15px 50px rgba(102, 126, 234, 0.5),
                    0 0 0 4px rgba(102, 126, 234, 0.3) !important;
    }
    
    div[data-testid="stAudioInput"] > button:active {
        transform: translateY(0) !important;
    }
    
    /* Recording state - when button text changes */
    div[data-testid="stAudioInput"] > button[aria-label*="Stop"],
    div[data-testid="stAudioInput"] > button[aria-label*="stop"] {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important;
        box-shadow: 0 10px 40px rgba(245, 87, 108, 0.5),
                    0 0 0 0 rgba(245, 87, 108, 0.7) !important;
        animation: recordingPulse 1.5s ease-in-out infinite !important;
    }
    
    @keyframes recordingPulse {
        0%, 100% {
            box-shadow: 0 10px 40px rgba(245, 87, 108, 0.5),
                        0 0 0 0 rgba(245, 87, 108, 0.7);
        }
        50% {
            box-shadow: 0 10px 40px rgba(245, 87, 108, 0.6),
                        0 0 0 8px rgba(245, 87, 108, 0);
        }
    }
    
    /* Ensure button text is visible and styled */
    div[data-testid="stAudioInput"] > button > * {
        color: white !important;
        font-weight: 600 !important;
    }
    
    /* Helper container for background blur behind dock */
    .dock-background {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 200px;
        background: linear-gradient(to top, #050505 95%, transparent);
        pointer-events: none;
        z-index: 999;
    }
    
    /* Microphone Hint Text */
    .mic-hint {
        position: fixed;
        bottom: 140px;
        left: 0;
        width: 100%;
        text-align: center;
        color: #888;
        font-size: 1rem;
        font-weight: 500;
        pointer-events: none;
        z-index: 999;
        opacity: 0.9;
        letter-spacing: 0.3px;
    }
    
    /* Visual indicator dots */
    .mic-indicator {
        position: fixed;
        bottom: 130px;
        left: 50%;
        transform: translateX(-50%);
        display: flex;
        gap: 6px;
        align-items: center;
        z-index: 999;
        pointer-events: none;
    }
    
    .mic-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #667eea;
        opacity: 0.6;
        animation: dotPulse 1.4s ease-in-out infinite;
    }
    
    .mic-dot:nth-child(2) {
        animation-delay: 0.2s;
    }
    
    .mic-dot:nth-child(3) {
        animation-delay: 0.4s;
    }
    
    @keyframes dotPulse {
        0%, 100% {
            opacity: 0.3;
            transform: scale(1);
        }
        50% {
            opacity: 1;
            transform: scale(1.2);
        }
    }
    
    /* Hide annoying elements */
    .stDeployButton {display:none;}
    
    </style>
""", unsafe_allow_html=True)


st.markdown("""
<div class="header-container">
    <div class="header-title">Talk to Danish</div>
    <div class="header-subtitle">Ask anything about my work, experience, or ideas</div>
</div>
""", unsafe_allow_html=True)


history = st.session_state.messages
if len(history) > 1: # Skip system prompt
    # Identify the index of the last assistant message
    last_assistant_idx = -1
    for i in range(len(history) - 1, -1, -1):
        if history[i]["role"] == "assistant":
            last_assistant_idx = i
            break

    for i, msg in enumerate(history):
        if msg["role"] == "system":
            continue
        
        if msg["role"] == "user":
            st.markdown(f"""
            <div class="msg-user">
                <span class="msg-user-text">“{msg['content']}”</span>
            </div>
            """, unsafe_allow_html=True)
            
        elif msg["role"] == "assistant":
            if i == last_assistant_idx:
                # Latest Response (Emphasis)
                st.markdown(f"""
                <div class="msg-assistant-latest">
                    {msg['content']}
                </div>
                """, unsafe_allow_html=True)
                
                
                
            else:
                # Previous Response (Faded)
                st.markdown(f"""
                <div class="msg-assistant-prev">
                    {msg['content']}
                </div>
                """, unsafe_allow_html=True)



# Background gradient for dock
st.markdown('<div class="dock-background"></div>', unsafe_allow_html=True)

# Visual indicator dots
st.markdown("""
<div class="mic-indicator">
    <div class="mic-dot"></div>
    <div class="mic-dot"></div>
    <div class="mic-dot"></div>
</div>
""", unsafe_allow_html=True)

# Microphone hint text
st.markdown("""
<div class="mic-hint">
    Click the mic button below to start/stop speaking
</div>
""", unsafe_allow_html=True)

if "input_key" not in st.session_state:
    st.session_state.input_key = 0

# Audio Input Widget - Now styled to be prominent and clear
audio_value = st.audio_input("Tap to Speak", label_visibility="hidden", key=f"audio_input_{st.session_state.input_key}")

# JavaScript to enhance button text and behavior
st.markdown("""
<script>
(function() {
    function enhanceAudioButton() {
        const audioInput = window.parent.document.querySelector('div[data-testid="stAudioInput"] button');
        if (audioInput) {
            const currentText = audioInput.textContent.trim();
            const ariaLabel = audioInput.getAttribute('aria-label') || '';
            
            // Check if recording
            if (ariaLabel.includes('Stop') || ariaLabel.includes('stop') || currentText.includes('Stop')) {
                if (!currentText.includes('🔴')) {
                    audioInput.innerHTML = '<span style="font-size: 1.2rem; margin-right: 8px;">🔴</span> Recording...';
                }
            } else {
                // Not recording - show tap to speak
                if (!currentText.includes('🎙️') && !currentText.includes('Tap to Speak')) {
                    audioInput.innerHTML = '<span style="font-size: 1.3rem; margin-right: 10px; display: inline-block; animation: micPulse 2s ease-in-out infinite;">🎙️</span> Tap to Speak';
                }
            }
            
            // Monitor for state changes
            const observer = new MutationObserver(function() {
                setTimeout(enhanceAudioButton, 50);
            });
            
            observer.observe(audioInput, {
                childList: true,
                characterData: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['aria-label']
            });
        } else {
            // Retry if button not found yet
            setTimeout(enhanceAudioButton, 100);
        }
    }
    
    // Add animation for mic icon
    const style = document.createElement('style');
    style.textContent = `
        @keyframes micPulse {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.15); opacity: 0.85; }
        }
    `;
    document.head.appendChild(style);
    
    // Run on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', enhanceAudioButton);
    } else {
        enhanceAudioButton();
    }
    
    // Also run after Streamlit updates
    setTimeout(enhanceAudioButton, 500);
    setInterval(enhanceAudioButton, 1000);
})();
</script>
""", unsafe_allow_html=True)


if audio_value:
    
    # Using a placeholder or spinner that doesn't block the UI heavily
    with st.spinner("Listening..."):
        try:
            
            suffix = ".wav"
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_audio:
                tmp_audio.write(audio_value.read())
                tmp_audio_path = tmp_audio.name
            
            with open(tmp_audio_path, "rb") as audio_file:
                transcription = groq_client.audio.transcriptions.create(
                    model="whisper-large-v3-turbo", 
                    file=audio_file,
                    response_format="text"
                )
            
   
            if hasattr(transcription, 'text'):
                user_text = transcription.text
            else:
                user_text = str(transcription)

            os.remove(tmp_audio_path)
            
        except Exception as e:
            st.error(f"Audio processing failed: {e}")
            user_text = None

    if user_text and user_text.strip():
        # Add User Message
        st.session_state.messages.append({"role": "user", "content": user_text})
        
        
        with st.spinner("Thinking..."):
            try:
                # Chat Completion
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=st.session_state.messages,
                    temperature=0.7,
                    max_tokens=250 # Keep it concise for voice
                )
                bot_text = response.choices[0].message.content
                st.session_state.messages.append({"role": "assistant", "content": bot_text})
                # 3. Generate Audio (ElevenLabs)
                # Set flag to trigger scroll after message is rendered
                st.session_state.scroll_after_message = True
                
                audio_generator = elevenlabs_client.text_to_speech.convert(
                    text=bot_text,
                    voice_id="WU3NNr4InTpWBvdLxgpD", 
                    model_id="eleven_turbo_v2_5"
                )
                
                # Consume generator to get bytes
                audio_bytes = b"".join(audio_generator)
                
                # Store audio in session state for autoplay
                st.session_state.current_audio = audio_bytes
                
                # Increment key to reset audio widget
                st.session_state.input_key += 1
                
                # Rerun to update UI with new messages
                st.rerun()
                
            except Exception as e:
                st.error(f"Error: {e}")

# Autoplay Audio Logic
if "current_audio" in st.session_state and st.session_state.current_audio:
    # Play Audio
    st.audio(st.session_state.current_audio, format="audio/mp3", autoplay=True)
    
    # Clear audio from state for next run
    del st.session_state.current_audio 

# Force Scroll to Bottom whenever there are messages 
if len(st.session_state.messages) > 1:
    # Check if we just added a new assistant message (scroll needed)
    scroll_needed = "scroll_after_message" in st.session_state and st.session_state.scroll_after_message
    
    components.html(
        """
        <script>
            (function() {
                let hasScrolled = false;
                
                function scrollToBottom(instant) {
                    if (hasScrolled && !instant) return; // Only allow one smooth scroll
                    
                    // Try multiple scroll targets to ensure it works
                    const targets = [
                        window.parent.document.querySelector(".main"),
                        window.parent.document.querySelector(".main .block-container"),
                        window.parent.document.querySelector("#root"),
                        window.parent.document.querySelector("section[data-testid='stMain']"),
                        window.parent.document.body,
                        document.body
                    ];
                    
                    const behavior = instant ? 'auto' : 'smooth';
                    
                    targets.forEach(function(target) {
                        if (target) {
                            try {
                                target.scrollTop = target.scrollHeight;
                                if (!instant) {
                                    target.scrollIntoView({ behavior: behavior, block: 'end' });
                                }
                            } catch(e) {}
                        }
                    });
                    
                    // Also try window scroll methods
                    try {
                        window.parent.scrollTo({
                            top: window.parent.document.body.scrollHeight,
                            behavior: behavior
                        });
                        window.scrollTo({
                            top: document.body.scrollHeight,
                            behavior: behavior
                        });
                    } catch(e) {}
                    
                    if (!instant) {
                        hasScrolled = true;
                    }
                }
                
                // Scroll immediately (instant, no animation)
                scrollToBottom(true);
                
                // One delayed smooth scroll as backup (only if content wasn't fully loaded)
                setTimeout(function() {
                    scrollToBottom(false);
                }, 300);
            })();
        </script>
        """,
        height=0,
        width=0
    )
    
    # Clear the scroll flag
    if "scroll_after_message" in st.session_state:
        del st.session_state.scroll_after_message 
