"""Backend for the dashboard: review queue, labels, live feed, metrics, attack controls."""

from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI, WebSocket

app = FastAPI(title="Analyst API", version="0.1.0")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/review-queue")
async def review_queue(limit: int = 50) -> list[dict]:
    """TODO(phase 6): oldest unreviewed REVIEW decisions with features and reasons."""
    raise NotImplementedError


@app.post("/v1/transactions/{txn_id}/label")
async def label(txn_id: UUID, is_fraud: bool) -> dict:
    """TODO(phase 6): publish Label(source=analyst) to labels.analyst; mark queue item reviewed."""
    raise NotImplementedError


@app.post("/v1/attacks/{pattern}")
async def launch_attack(pattern: str, victims: int = 5) -> dict:
    """TODO(phase 6): forward to gateway-sim control API."""
    raise NotImplementedError


@app.websocket("/v1/live")
async def live(ws: WebSocket) -> None:
    """TODO(phase 6): consume transactions.scored, push to clients.

    Use its own consumer group and start from the latest offset.
    """
    await ws.accept()
    raise NotImplementedError
