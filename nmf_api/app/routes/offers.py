from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..deps import get_tagger
from ..nmf_classifier import NmfTagger
from ..schemas import (
    OfferOutputResponse,
    OfferTagsResponse,
    OfferTitleDescriptionResponse,
)

router = APIRouter()


@router.get("/offers", response_model=OfferTagsResponse)
def list_offers(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    active_only: bool = Query(False),
    tagger: NmfTagger = Depends(get_tagger),
) -> OfferTagsResponse:
    items = tagger.list_offers(offset=offset, limit=limit, active_only=active_only)
    return OfferTagsResponse(total=tagger.count_offers(active_only), items=items)


@router.get("/offers/active", response_model=OfferTagsResponse)
def list_active_offers(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tagger: NmfTagger = Depends(get_tagger),
) -> OfferTagsResponse:
    items = tagger.list_offers(offset=offset, limit=limit, active_only=True)
    return OfferTagsResponse(total=tagger.count_offers(True), items=items)


@router.get("/offers/normalized", response_model=OfferOutputResponse)
def list_offers_normalized(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    active_only: bool = Query(False),
    tag_ids: list[int] | None = Query(None),
    require_tag_match: bool = Query(True),
    tagger: NmfTagger = Depends(get_tagger),
) -> OfferOutputResponse:
    items = tagger.list_offer_outputs(
        offset=offset,
        limit=limit,
        active_only=active_only,
        tag_ids=tag_ids,
        require_tag_match=require_tag_match,
    )
    total = tagger.count_offers_filtered(
        active_only=active_only,
        tag_ids=tag_ids,
        require_tag_match=require_tag_match,
    )
    return OfferOutputResponse(total=total, items=items)


@router.get("/offers/brief", response_model=OfferTitleDescriptionResponse)
def list_offer_brief(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    active_only: bool = Query(False),
    tag_ids: list[int] | None = Query(None),
    require_tag_match: bool = Query(True),
    tagger: NmfTagger = Depends(get_tagger),
) -> OfferTitleDescriptionResponse:
    items = tagger.list_offer_titles(
        offset=offset,
        limit=limit,
        active_only=active_only,
        tag_ids=tag_ids,
        require_tag_match=require_tag_match,
    )
    total = tagger.count_offers_filtered(
        active_only=active_only,
        tag_ids=tag_ids,
        require_tag_match=require_tag_match,
    )
    return OfferTitleDescriptionResponse(total=total, items=items)
