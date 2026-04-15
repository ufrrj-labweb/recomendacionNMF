from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import HTTPException

DEFAULT_ONESIGNAL_URL = "https://onesignal.com/api/v1/notifications"


def _get_env(name: str, required: bool = True) -> str | None:
    value = os.getenv(name)
    if required and not value:
        raise HTTPException(status_code=400, detail=f"Falta {name}")
    return value


def send_notification_raw(
    *,
    external_user_ids: list[str] | None,
    headings: dict[str, str],
    contents: dict[str, str],
    included_segments: list[str] | None = None,
    filters: list[dict[str, Any]] | None = None,
    data: dict[str, Any] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    app_id = _get_env("ONESIGNAL_APP_ID")
    api_key = _get_env("ONESIGNAL_API_KEY")
    api_url = os.getenv("ONESIGNAL_API_URL", DEFAULT_ONESIGNAL_URL)

    payload: dict[str, Any] = {
        "app_id": app_id,
        "headings": headings,
        "contents": contents,
    }
    if external_user_ids:
        payload["include_external_user_ids"] = external_user_ids
    if included_segments:
        payload["included_segments"] = included_segments
    if filters:
        payload["filters"] = filters
    if data:
        payload["data"] = data
    if dry_run:
        payload["test_type"] = "email"

    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(api_url, json=payload, headers=headers, timeout=20.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Error al enviar notificacion: {exc}",
        ) from exc

    return response.json()


def send_notification(
    *,
    external_user_ids: list[str],
    heading: str,
    content: str,
    data: dict[str, Any] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    lang = os.getenv("ONESIGNAL_LANG", "es")
    return send_notification_raw(
        external_user_ids=external_user_ids,
        headings={lang: heading},
        contents={lang: content},
        data=data,
        dry_run=dry_run,
    )
