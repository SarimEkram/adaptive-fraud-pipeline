FROM python:3.12-slim
WORKDIR /app
COPY libs/fraudcore /libs/fraudcore
RUN pip install --no-cache-dir /libs/fraudcore
COPY services/event-sink /app
RUN pip install --no-cache-dir .
CMD ["python", "-m", "event_sink.main"]
