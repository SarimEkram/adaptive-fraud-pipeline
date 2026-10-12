FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY libs/fraudcore /libs/fraudcore
RUN pip install --no-cache-dir /libs/fraudcore
COPY services/ml-platform /app
RUN pip install --no-cache-dir .
ENTRYPOINT ["mlp"]
