# Talk to Danish - Voice Agent

A conversational voice agent that acts as my digital twin. Speak a question and get a natural voice response — fully free to run, no paid APIs required.

## 🧠 Talk to my AI twin

[Launch Live Demo](https://digital-twin-danish.streamlit.app/)

## ✨ Features

- **🗣️ Natural Voice Interaction**: Seamless "Speak → Audio Response" loop.
- **⚡ Ultra-Low Latency**: Groq `whisper-large-v3-turbo` for near-instant transcription.
- **🧠 Custom Persona**: Grounded in specific facts (`facts.json`) and personality traits (`persona.json`).
- **🎨 Minimalist UI**: Dark-themed interface designed to feel like a native app, not a web page.
- **🔊 Free TTS**: Microsoft neural voices via `edge-tts` — no API key or billing required.

## 🛠️ Tech Stack

| Layer | Service | Notes |
|---|---|---|
| **Frontend** | [Streamlit](https://streamlit.io/) | Custom CSS, fixed mic dock |
| **STT** | [Groq](https://groq.com/) Whisper V3 Turbo | Free tier, falls back to OpenAI Whisper |
| **LLM** | [Groq](https://groq.com/) Llama 3.3 70B | Free tier |
| **TTS** | [edge-tts](https://github.com/rany2/edge-tts) | Microsoft neural voices, completely free |

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- API keys for Groq and OpenAI (free tiers work)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Danish137/Digital-twin.git
   cd Digital-twin
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Copy `.envexample` to `.env` and fill in your keys:
   ```env
   OPENAI_API_KEY=sk-xxxxxx
   GROQ_API_KEY=gsk_xxxxxx
   ```

4. **Run the app**
   ```bash
   streamlit run app.py
   ```

## 📂 Project Structure

```
.
├── app.py                # Main application logic
├── facts.json            # Knowledge base for the digital twin
├── persona.json          # Personality and system prompt config
├── requirements.txt      # Python dependencies
├── .envexample           # Environment variable template
└── README.md
```

## 🎨 Design Philosophy

The interface follows a "Conversation First" design:
- **No distractions**: Header, footer, and sidebar are hidden.
- **Focus**: The latest response is highlighted; older messages fade out.
- **Interactivity**: A custom fixed microphone dock allows single-tap interaction.
- **Multi-turn**: The agent maintains full conversation context.

## 📝 Feel free to contribute or suggest improvements.
