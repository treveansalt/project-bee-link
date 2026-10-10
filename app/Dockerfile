FROM python:3.12-slim
WORKDIR /app
COPY server.py protocol.json ./
COPY dist ./dist
RUN useradd --uid 10001 --create-home beelink && mkdir /app/data && chown beelink /app/data
USER beelink
EXPOSE 8765
CMD ["python", "server.py", "--host", "0.0.0.0", "--db", "/app/data/bee-link.sqlite"]
