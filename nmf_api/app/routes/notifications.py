from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_tagger
from ..nmf_classifier import NmfTagger
from ..schemas import (
    NotificationOffersRequest,
    NotificationOffersResponse,
    NotificationSendRequest,
    NotificationSendResponse,
)
from ..services.interests_service import fetch_user_tag_ids
from ..services.onesignal_service import send_notification, send_notification_raw

router = APIRouter()


def _get_description(offer: dict) -> str:
    for key in ("descricao", "resumo", "objetivos"):
        value = offer.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _build_content(items: list[dict]) -> str:
    lines = []
    for item in items:
        title = item.get("title", "")
        description = item.get("description", "")
        if description:
            lines.append(f"- {title}: {description}")
        else:
            lines.append(f"- {title}")

    content = "\n".join(lines)
    max_chars = 240
    if len(content) <= max_chars:
        return content
    return content[: max_chars - 3].rstrip() + "..."


@router.post("/notifications/offers/brief", response_model=NotificationOffersResponse)
def notify_offers_brief(
    payload: NotificationOffersRequest,
    tagger: NmfTagger = Depends(get_tagger),
) -> NotificationOffersResponse:
    tag_ids = fetch_user_tag_ids(payload.user_id)
    if not tag_ids:
        return NotificationOffersResponse(total=0, items=[], onesignal={})

    items = tagger.recommend(
        tag_ids=tag_ids,
        limit=payload.limit,
        min_score=payload.min_score,
        active_only=payload.active_only,
        require_tag_match=payload.require_tag_match,
    )

    brief_items = []
    for item in items:
        offer = item.get("offer", {})
        brief_items.append(
            {
                "offer_id": item.get("offer_id"),
                "title": item.get("title"),
                "description": _get_description(offer),
            }
        )

    if not brief_items:
        return NotificationOffersResponse(total=0, items=[], onesignal={})

    heading = payload.heading or "Nuevas ofertas"
    content = _build_content(brief_items)

    onesignal = send_notification(
        external_user_ids=[str(payload.user_id)],
        heading=heading,
        content=content,
        data={"offer_ids": [item["offer_id"] for item in brief_items]},
        dry_run=payload.dry_run,
    )

    return NotificationOffersResponse(
        total=len(brief_items),
        items=brief_items,
        onesignal=onesignal,
    )


@router.post("/notifications/send", response_model=NotificationSendResponse)
def send_notification_general(
    payload: NotificationSendRequest,
) -> NotificationSendResponse:
    if not payload.external_user_ids and not payload.included_segments:
        if not payload.filters:
            return NotificationSendResponse(onesignal={})

    onesignal = send_notification_raw(
        external_user_ids=payload.external_user_ids,
        headings=payload.headings,
        contents=payload.contents,
        included_segments=payload.included_segments,
        filters=payload.filters,
        data=payload.data,
        dry_run=payload.dry_run,
    )
    return NotificationSendResponse(onesignal=onesignal)
