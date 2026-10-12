"""Population Stability Index per feature and on the score distribution. PSI > 0.2 means drift."""


def psi(expected, actual, bins: int = 10) -> float:
    """TODO(phase 7): bin on EXPECTED quantiles; add a small epsilon to avoid log(0)."""
    raise NotImplementedError


def run(argv: list[str]) -> None:
    raise NotImplementedError  # TODO(phase 7)
