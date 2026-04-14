from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TEXT_FIELDS = [
    "titulo",
    "titulo_curto",
    "resumo",
    "descricao",
    "objetivos",
    "area_principal",
    "area_secundaria",
    "modalidade",
    "publico",
    "requisitos",
    "atribuicoes",
    "funcao_extensionista",
    "centro",
    "unidade",
    "coordenador",
    "observacoes",
]


def _as_paths(json_path: str | Path | list[str | Path]) -> list[Path]:
    if isinstance(json_path, (str, Path)):
        return [Path(json_path)]
    return [Path(item) for item in json_path]


def _offer_key(offer: dict[str, Any]) -> str:
    key = (
        offer.get("id_acao")
        or offer.get("id_anuncio_acao")
        or offer.get("id_anuncio_vaga")
        or offer.get("id")
        or ""
    )
    return str(key)


def _merge_offers(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def _is_empty(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        if isinstance(value, (list, tuple, dict, set)):
            return len(value) == 0
        return False

    merged: dict[str, dict[str, Any]] = {}
    counter = 0
    for item in items:
        key = _offer_key(item)
        if not key:
            counter += 1
            key = f"__anon__{counter}"

        if key not in merged:
            merged[key] = dict(item)
        else:
            target = merged[key]
            for field, value in item.items():
                if field not in target or _is_empty(target.get(field)):
                    if not _is_empty(value):
                        target[field] = value

    return list(merged.values())


def load_offers(json_path: str | Path | list[str | Path]) -> list[dict[str, Any]]:
    paths = _as_paths(json_path)
    all_items: list[dict[str, Any]] = []

    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"No se encontro el archivo: {path}")

        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            continue

        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("El JSON debe ser una lista de ofertas.")
        all_items.extend(data)

    return _merge_offers(all_items)


def build_document(offer: dict[str, Any]) -> str:
    parts: list[str] = []
    for field in TEXT_FIELDS:
        value = offer.get(field)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    return "\n".join(parts)
