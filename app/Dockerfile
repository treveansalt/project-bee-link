FROM python:3.12-slim
WORKDIR /app
ARG WITH_MESHCORE=false
COPY requirements-meshcore.txt ./
RUN if [ "$WITH_MESHCORE" = "true" ]; then pip install --no-cache-dir -r requirements-meshcore.txt; fi
COPY server.py capture_summary.py meshcore_bridge.py meshcore_policy.py protocol.json ./
COPY dist ./dist
RUN useradd --uid 10001 --create-home beelink && mkdir /app/data && chown beelink /app/data
USER beelink
EXPOSE 8765
CMD ["python", "server.py", "--host", "0.0.0.0", "--db", "/app/data/bee-link.sqlite"]
