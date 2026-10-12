"""FastAPI entrypoint for the scoring service."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fraudcore.config import Settings
from fraudcore.schemas import Decision, Transaction
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from scoring.model import ModelRegistry
from scoring.pipeline import ScoringPipeline

SCORE_LATENCY = Histogram(
    "score_latency_seconds",
    "End-to-end scoring latency inside the service",
    buckets=(0.002, 0.005, 0.01, 0.02, 0.03, 0.05, 0.075, 0.1, 0.25),
)
DECISIONS = Counter("decisions_total", "Decisions by action", ["action"])

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO(phase 3/4): create Redis client, Kafka publisher, load models, build pipeline.
    app.state.registry = ModelRegistry(settings.model_dir)
    app.state.pipeline = ScoringPipeline(settings=settings, registry=app.state.registry)
    yield
    # TODO(phase 4): flush publisher, close clients


app = FastAPI(title="Fraud scoring service", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness: the process is up."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz(response: Response) -> dict[str, object]:
    """Readiness: a champion model is loaded and dependencies are reachable."""
    ready = app.state.registry.champion is not None  # TODO(phase 4): also check Redis
    response.status_code = 200 if ready else 503
    return {"ready": ready}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/v1/score", response_model=Decision)
async def score(txn: Transaction) -> Decision:
    with SCORE_LATENCY.time():
        decision = await app.state.pipeline.score(txn)
    DECISIONS.labels(decision.action.value).inc()
    return decision
