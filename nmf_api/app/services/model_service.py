from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

from ..data_loader import build_document, load_offers
from ..nmf_classifier import NmfTagger, OfferRecord, TaggerConfig
from ..state import AppState

BASE_DIR = Path(__file__).resolve().parents[3]
DEFAULT_DATA_PATHS = [
    BASE_DIR / "classes.json",
    BASE_DIR / "vacantes.json",
]


def parse_data_paths() -> list[Path]:
    raw = os.getenv("OFFER_DATA_PATHS") or os.getenv("OFFER_DATA_PATH")
    if not raw:
        return DEFAULT_DATA_PATHS

    parts = [item.strip() for item in raw.split(",") if item.strip()]
    return [Path(item) for item in parts]


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    raw = raw[:10]
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


def _is_active(offer: dict) -> bool:
    start = _parse_date(offer.get("data_inicio_inscricoes"))
    end = _parse_date(offer.get("data_termino_inscricoes"))
    today = date.today()

    if start and today < start:
        return False
    if end and today > end:
        return False
    return True


def build_tagger(
    config: TaggerConfig, data_paths: list[Path], active_only: bool = False
) -> NmfTagger:
    raw_offers = load_offers(data_paths)
    if not raw_offers:
        raise ValueError("El archivo de datos no tiene ofertas.")

    if active_only:
        raw_offers = [item for item in raw_offers if _is_active(item)]
        if not raw_offers:
            raise ValueError("No hay ofertas activas para entrenar el modelo.")

    offers: list[OfferRecord] = []
    for item in raw_offers:
        offer_id = str(
            item.get("id_acao")
            or item.get("id_anuncio_vaga")
            or item.get("id_anuncio_acao")
            or item.get("id")
            or ""
        )
        title = str(item.get("titulo") or item.get("titulo_curto") or "")
        text = build_document(item)
        if not text.strip():
            text = title
        offers.append(OfferRecord(offer_id=offer_id, title=title, text=text, raw=item))

    tagger = NmfTagger(config)
    tagger.fit(offers)
    return tagger


def startup_model(state: AppState) -> None:
    data_paths = parse_data_paths()
    config = TaggerConfig()
    tagger = build_tagger(config, data_paths)

    state.tagger = tagger
    state.data_paths = data_paths
