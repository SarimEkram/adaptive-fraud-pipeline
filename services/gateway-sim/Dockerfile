FROM python:3.12-slim
WORKDIR /app
COPY libs/fraudcore /libs/fraudcore
RUN pip install --no-cache-dir /libs/fraudcore
COPY services/gateway-sim /app
RUN pip install --no-cache-dir .
CMD ["python", "-m", "gateway_sim.main"]
