FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY libs/fraudcore /libs/fraudcore
RUN pip install --no-cache-dir /libs/fraudcore
COPY services/scoring /app
RUN pip install --no-cache-dir .
EXPOSE 8000
CMD ["uvicorn", "scoring.main:app", "--host", "0.0.0.0", "--port", "8000"]
