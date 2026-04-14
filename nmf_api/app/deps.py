from __future__ import annotations

from fastapi import HTTPException

from .nmf_classifier import NmfTagger
from .state import STATE


def get_tagger() -> NmfTagger:
    tagger = STATE.tagger
    if not tagger:
        raise HTTPException(status_code=500, detail="Modelo no inicializado")
    return tagger
