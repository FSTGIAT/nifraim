# Build context = REPO ROOT (railway up uploads the root; compose sets context: .)
FROM python:3.11-slim
WORKDIR /app
COPY services/calls-gateway/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# The wire contract is shared verbatim with the API and the transcriber — never fork it.
COPY backend/app/services/calls/contract.py ./calls_contract.py
COPY services/calls-gateway/main.py ./
ENV CALLS_DATA_DIR=/data/calls
# HOST "::" — Railway private networking may resolve over IPv6 only; 0.0.0.0 would fail silently.
# (uvicorn's "::" is IPv6-ONLY, so docker-compose sets HOST=0.0.0.0 for the local IPv4 port map.)
ENV HOST=::
CMD sh -c "uvicorn main:app --host ${HOST} --port ${PORT:-8080}"
