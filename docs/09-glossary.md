# 09 Glossary

* **Authorization**: the real-time approve/decline request for a card payment.
* **Chargeback**: a customer disputes a charge; arrives days or weeks later; our delayed fraud label.
* **Hot path / cold path**: work needed for the decision (fast, synchronous) vs everything else (async).
* **Idempotency**: doing the same request twice has the same effect as once.
* **At-least-once delivery**: every message arrives, possibly more than once.
* **Point-in-time correctness**: features only use data available at the moment of the event.
* **Training-serving skew**: features computed differently in training and production, so the model silently degrades.
* **PR-AUC**: area under the precision-recall curve; the main metric under class imbalance.
* **Precision / recall**: of what we flagged, how much was fraud / of all fraud, how much we flagged.
* **TreeSHAP**: exact per-feature contribution to a tree model's prediction.
* **PSI**: Population Stability Index; measures how much a distribution has shifted.
* **Champion / challenger / shadow**: live model / candidate model / scoring traffic without acting on it.
* **MCC**: merchant category code, a 4-digit merchant type.
* **DLQ**: dead-letter queue for messages that cannot be processed.
* **Velocity feature**: count or sum of activity in a recent time window.
