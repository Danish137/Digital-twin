FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY persona.json facts.json agent.py ./

# Pre-download ONNX / VAD model files during build
RUN python agent.py download-files

CMD ["python", "agent.py", "start"]
