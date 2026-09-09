FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# If you use the stdio Grafana MCP transport, install the mcp-grafana binary
# into the image here (see HANDOFF.md "Grafana MCP"). Otherwise set
# GRAFANA_MCP_URL to the hosted Grafana Cloud MCP endpoint and skip this.

COPY . .

ENV PORT=8080
CMD ["sh", "-c", "uvicorn kalman.server.app:app --host 0.0.0.0 --port ${PORT}"]
