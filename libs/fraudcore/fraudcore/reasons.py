"""Map model features to reason codes analysts understand."""

REASON_CODES: dict[str, str] = {
    "implied_speed_kmh": "IMPOSSIBLE_TRAVEL",
    "km_from_last_txn": "UNUSUAL_LOCATION",
    "txn_count_1m": "HIGH_VELOCITY",
    "txn_count_1h": "HIGH_VELOCITY",
    "small_txn_count_10m": "CARD_TESTING",
    "amount_zscore": "UNUSUAL_AMOUNT",
    "is_new_device": "NEW_DEVICE",
    "is_new_merchant": "NEW_MERCHANT",
    "is_foreign": "FOREIGN_MERCHANT",
    "mcc_risk_bucket": "HIGH_RISK_CATEGORY",
    "hour_of_day": "UNUSUAL_TIME",
}


def reason_code(feature: str) -> str:
    return REASON_CODES.get(feature, "OTHER")
