# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create runtime directories for externalized config, logs, and state
RUN mkdir -p /config

ENV CONFIG_PATH=/config/config.json \
    STATE_FILE_PATH=/config/last_state.json \
    LOG_PATH=/config/monitor.log

VOLUME ["/config"]

CMD ["python", "main.py"]
