"""Load champion and challenger models from the registry folder.

Layout written by ml-platform:
    {model_dir}/champion -> symlink or file pointing to a version folder
    {model_dir}/challenger -> optional
    {model_dir}/versions/{version}/model.txt + metadata.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import lightgbm as lgb


@dataclass
class LoadedModel:
    version: str
    booster: lgb.Booster
    feature_names: list[str]


class ModelRegistry:
    def __init__(self, model_dir: str) -> None:
        self.root = Path(model_dir)
        self.champion: LoadedModel | None = self._load("champion")
        self.challenger: LoadedModel | None = self._load("challenger")

    def _load(self, alias: str) -> LoadedModel | None:
        path = self.root / alias
        if not path.exists():
            return None  # failure mode F4: caller decides fallback
        meta = json.loads((path / "metadata.json").read_text())
        booster = lgb.Booster(model_file=str(path / "model.txt"))
        return LoadedModel(meta["version"], booster, meta["feature_names"])

    def reload(self) -> None:
        """TODO(phase 7): reload atomically; keep old models if the new load fails."""
        raise NotImplementedError
