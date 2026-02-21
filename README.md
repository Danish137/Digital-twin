# Talk to Danish - Voice Agent

A high-fidelity conversational voice agent that acts as my digital twin. This project uses a hybrid architecture leveraging **Groq** for ultra-fast Whisper transcription, **GPT-4o-mini** for intelligence, and **ElevenLabs** for realistic voice synthesis.
## 🧠 Talk to my AI twin
Click below and speak:

[Launch Live Demo](https://digital-twin-danish.streamlit.app/)


## ✨ Features

- **🗣️ Natural Voice Interaction**: Seamless "Speak → Audio Response" loop.
- **⚡ Ultra-Low Latency**: Uses Groq `whisper-large-v3-turbo` for near-instant transcription.
- **🧠 Custom Persona**: Grounded in specific facts (`facts.json`) and personality traits (`persona.json`).
- **🎨 "Disappearing UI"**: A minimalist, dark-themed interface designed to feel like a native app, not a web page.
- **🔊 ElevenLabs Integration**: for text to speech.

## 🛠️ Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/) (Custom CSS)
- **STT (Speech-to-Text)**: [Groq](https://groq.com/) (Whisper V3 Turbo)
- **LLM (Intelligence)**: [OpenAI](https://openai.com/) (GPT-4o-mini)
- **TTS (Text-to-Speech)**: [ElevenLabs](https://elevenlabs.io/)

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- API Keys for:
  - Groq
  - ElevenLabs
  - OpenAI

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Digital-twin.git
   cd Digital-twin
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Environment Variables**
   Rename `.envexample` to `.env` in the root directory and add your API keys:
   ```env
   OPENAI_API_KEY=sk-xxxxxx
   OPENAI_BASE_URL=
   GROQ_API_KEY=gsk_xxxxxx
   ELEVENLABS_API_KEY=xxxxxx
   ```

4. **Run the App**
   ```bash
   streamlit run app.py
   ```

## 📂 Project Structure

```
.
├── app.py                # Main application logic
├── facts.json            # Knowledge base for the digital twin
├── persona.json          # Personality definition and system prompts
├── requirements.txt      # Python dependencies
├── .env                  # API keys
└── README.md             
```

## 🎨 Design Philosophy

The interface follows a "Conversation First" design:

- **No distractions**: Header, footer, and sidebar are hidden.
- **Focus**: The latest response is highlighted; older messages fade out.
- **Interactivity**: A custom fixed microphone dock allows for single-tap interaction.
- **Multi-turn conversation**: The agent can remember the context of the conversation and respond accordingly.

## 📝 NOTE: This is not a completed project , I am working on it.
