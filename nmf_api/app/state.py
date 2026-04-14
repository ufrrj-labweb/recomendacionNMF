from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .nmf_classifier import NmfTagger


@dataclass
class AppState:
    tagger: NmfTagger | None = None
    data_paths: list[Path] | None = None


STATE = AppState()
