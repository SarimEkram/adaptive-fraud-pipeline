FROM python:3.12-slim
WORKDIR /app
COPY libs/fraudcore /libs/fraudcore
RUN pip install --no-cache-dir /libs/fraudcore
COPY services/analyst-api /app
RUN pip install --no-cache-dir .
EXPOSE 8001
CMD ["uvicorn", "analyst_api.main:app", "--host", "0.0.0.0", "--port", "8001"]
