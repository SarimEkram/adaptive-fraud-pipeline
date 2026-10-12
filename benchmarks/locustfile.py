"""Load test for POST /v1/score. Results land in benchmarks/results/ (make bench)."""

import random
import uuid
from datetime import UTC, datetime

from locust import HttpUser, constant, task


class Gateway(HttpUser):
    wait_time = constant(0)

    @task
    def score(self) -> None:
        self.client.post(
            "/v1/score",
            json={
                "txn_id": str(uuid.uuid4()),
                "card_id": f"c{random.randint(1, 10_000)}",
                "customer_id": "u1",
                "amount_cents": random.randint(100, 50_000),
                "currency": "CAD",
                "merchant_id": f"m{random.randint(1, 500)}",
                "mcc": "5411",
                "merchant_country": "CA",
                "lat": 43.65,
                "lon": -79.38,
                "channel": "card_present",
                "event_time": datetime.now(UTC).isoformat(),
            },
        )
