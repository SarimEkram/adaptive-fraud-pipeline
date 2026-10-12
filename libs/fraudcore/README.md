# fraudcore

The only code shared between the hot path and the training pipeline.

* `schemas.py`: data contracts (see docs/03).
* `features/`: pure feature functions (see ADR-0006). No I/O in here, ever.
* `stores/`: how state is loaded and saved (Redis online). Offline replay keeps state in memory.
* `reasons.py`: maps features to human-readable reason codes.

If you are about to write feature logic anywhere else, stop: it belongs here.
