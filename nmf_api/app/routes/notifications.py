from __future__ import annotations

import os

from fastapi import APIRouter, Depends

from ..data_loader import build_document
from ..deps import get_tagger
from ..nmf_classifier import NmfTagger, OfferRecord
from ..schemas import (
    NotificationAutoOfferRequest,
    NotificationAutoOfferResponse,
    NotificationOffersRequest,
    NotificationOffersResponse,
    NotificationClassOfferRequest,
    NotificationClassOfferResponse,
    NotificationSendRequest,
    NotificationSendResponse,
)
from ..services.interests_service import (
    fetch_class_brief,
    fetch_interest_ids_by_class_id,
    fetch_user_ids_by_interest_ids,
    fetch_user_tag_ids,
    insert_class_interests,
    filter_new_user_ids,
)
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


@router.post(
    "/notifications/offers/class",
    response_model=NotificationClassOfferResponse,
)
def notify_users_by_class(
    payload: NotificationClassOfferRequest,
) -> NotificationClassOfferResponse:
    interest_ids = payload.interest_ids
    if interest_ids is None:
        interest_ids = fetch_interest_ids_by_class_id(payload.class_id)

    if not interest_ids:
        return NotificationClassOfferResponse(
            total_users=0, interest_ids=[], onesignal={}
        )

    user_ids = fetch_user_ids_by_interest_ids(interest_ids)
    if not user_ids:
        return NotificationClassOfferResponse(
            total_users=0, interest_ids=interest_ids, onesignal={}
        )

    heading = payload.heading
    content = payload.content
    if not heading or not content:
        title, description = fetch_class_brief(payload.class_id)
        heading = heading or title or "Nueva oferta"
        if not content:
            content = description or heading

    user_ids = filter_new_user_ids(payload.class_id, user_ids)
    if not user_ids:
        return NotificationClassOfferResponse(
            total_users=0, interest_ids=interest_ids, onesignal={}
        )

    lang = os.getenv("ONESIGNAL_LANG", "es")

    onesignal = send_notification_raw(
        external_user_ids=[str(uid) for uid in user_ids],
        headings={lang: heading},
        contents={lang: content},
        data=payload.data,
        dry_run=payload.dry_run,
    )

    return NotificationClassOfferResponse(
        total_users=len(user_ids),
        interest_ids=interest_ids,
        onesignal=onesignal,
    )


@router.post(
    "/notifications/offers/auto",
    response_model=NotificationAutoOfferResponse,
)
def notify_users_by_offer_auto(
    payload: NotificationAutoOfferRequest,
    tagger: NmfTagger = Depends(get_tagger),
) -> NotificationAutoOfferResponse:
    interest_ids = payload.interest_ids
    tags: list[int] = []

    if interest_ids is None:
        offer_id = str(
            payload.offer.get("id_acao")
            or payload.offer.get("id_anuncio_vaga")
            or payload.offer.get("id_anuncio_acao")
            or payload.offer.get("id")
            or payload.class_id
        )
        title = str(
            payload.offer.get("titulo") or payload.offer.get("titulo_curto") or ""
        )
        text = build_document(payload.offer)
        if not text.strip():
            text = title

        record = OfferRecord(
            offer_id=offer_id,
            title=title,
            text=text,
            raw=payload.offer,
        )
        inferred = tagger.infer([record])
        tags = inferred[0].get("tags", []) if inferred else []
        interest_ids = [int(tag_id) for tag_id in tags]

    if not interest_ids:
        return NotificationAutoOfferResponse(
            total_users=0, interest_ids=[], tags=tags, onesignal={}
        )

    if payload.persist_interests:
        insert_class_interests(payload.class_id, interest_ids)

    user_ids = fetch_user_ids_by_interest_ids(interest_ids)
    if not user_ids:
        return NotificationAutoOfferResponse(
            total_users=0, interest_ids=interest_ids, tags=tags, onesignal={}
        )

    user_ids = filter_new_user_ids(payload.class_id, user_ids)
    if not user_ids:
        return NotificationAutoOfferResponse(
            total_users=0, interest_ids=interest_ids, tags=tags, onesignal={}
        )

    heading = payload.heading
    content = payload.content
    if not heading or not content:
        title, description = fetch_class_brief(payload.class_id)
        heading = heading or title or "Nueva oferta"
        if not content:
            content = description or heading

    lang = os.getenv("ONESIGNAL_LANG", "es")
    onesignal = send_notification_raw(
        external_user_ids=[str(uid) for uid in user_ids],
        headings={lang: heading},
        contents={lang: content},
        data=payload.data,
        dry_run=payload.dry_run,
    )

    return NotificationAutoOfferResponse(
        total_users=len(user_ids),
        interest_ids=interest_ids,
        tags=tags or interest_ids,
        onesignal=onesignal,
    )
