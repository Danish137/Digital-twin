FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Download ONNX models (Silero VAD) at build time
RUN python agent.py download-files

EXPOSE 3000

# Run agent (background, connects outbound to LiveKit Cloud) + token server (foreground, serves UI)
CMD sh -c "python agent.py start & python token_server.py"
