# Build context = REPO ROOT (railway up uploads the root; compose sets context: .)
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY services/ivrit-transcriber/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# The wire contract is shared verbatim with the API and the gateway — never fork it.
COPY backend/app/services/calls/contract.py ./calls_contract.py
COPY services/ivrit-transcriber/worker.py ./
# The ~1.6GB ivrit.ai model is downloaded ONCE into this volume on first boot, not baked in.
ENV MODEL_DIR=/models HF_HOME=/models/hf PYTHONUNBUFFERED=1
CMD ["python", "worker.py"]
