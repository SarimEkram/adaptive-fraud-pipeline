"""A tiny model registry: one folder per version under models/versions/.

models/versions/v0001/
    model.txt            LightGBM booster (what the scoring service loads)
    logreg.joblib        logistic regression baseline
    amount_only.joblib   amount-only sanity baseline
    metadata.json        version, feature names, windows, generator version, metrics, thresholds
"""

from __future__ import annotations

import json
import re
from pathlib import Path

DEFAULT_ROOT = Path("models/versions")
_VERSION = re.compile(r"^v(\d{4})$")


def _versions(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir() and _VERSION.match(p.name))


def new_version_dir(root: str | Path = DEFAULT_ROOT) -> tuple[str, Path]:
    """Create the next folder (v0001, v0002, ...) and return its name and path."""
    root = Path(root)
    existing = _versions(root)
    number = int(_VERSION.match(existing[-1].name).group(1)) + 1 if existing else 1  # type: ignore[union-attr]
    version = f"v{number:04d}"
    path = root / version
    path.mkdir(parents=True)
    return version, path


def latest_version_dir(root: str | Path = DEFAULT_ROOT) -> Path:
    versions = _versions(Path(root))
    if not versions:
        raise FileNotFoundError(f"no model versions under {root}; run `mlp train` first")
    return versions[-1]


def read_metadata(version_dir: str | Path) -> dict:
    return json.loads((Path(version_dir) / "metadata.json").read_text())


def write_metadata(version_dir: str | Path, metadata: dict) -> None:
    (Path(version_dir) / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True))
