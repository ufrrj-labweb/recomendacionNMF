from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..data_loader import build_document
from ..deps import get_tagger
from ..nmf_classifier import NmfTagger, OfferRecord, TaggerConfig
from ..schemas import (
    RecommendByUserRequest,
    RecommendRequest,
    RecommendSerendipityRequest,
    RecommendResponse,
    TagOffersRequest,
    TagOffersResponse,
    TagResponse,
    TrainRequest,
)
from ..services.interests_service import fetch_user_tag_ids
from ..services.model_service import build_tagger
from ..state import STATE

router = APIRouter()


@router.get("/tags", response_model=list[TagResponse])
def list_tags(tagger: NmfTagger = Depends(get_tagger)) -> list[dict]:
    return tagger.get_tags()


@router.post("/recommend", response_model=RecommendResponse)
def recommend(
    payload: RecommendRequest,
    tagger: NmfTagger = Depends(get_tagger),
) -> RecommendResponse:
    items = tagger.recommend(
        tag_ids=payload.tag_ids,
        limit=payload.limit,
        min_score=payload.min_score,
        active_only=payload.active_only,
        require_tag_match=payload.require_tag_match,
    )
    return RecommendResponse(total=len(items), items=items)


@router.post("/recommend/serendipity", response_model=RecommendResponse)
def recommend_serendipity(
    payload: RecommendSerendipityRequest,
    tagger: NmfTagger = Depends(get_tagger),
) -> RecommendResponse:
    items = tagger.recommend_serendipity(
        tag_ids=payload.tag_ids,
        limit=payload.limit,
        min_score=payload.min_score,
        active_only=payload.active_only,
        require_tag_match=payload.require_tag_match,
        diversity_lambda=payload.diversity_lambda,
        candidate_multiplier=payload.candidate_multiplier,
    )
    return RecommendResponse(total=len(items), items=items)


@router.post("/recommend/user", response_model=RecommendResponse)
def recommend_by_user(
    payload: RecommendByUserRequest,
    tagger: NmfTagger = Depends(get_tagger),
) -> RecommendResponse:
    tag_ids = fetch_user_tag_ids(payload.user_id)
    if not tag_ids:
        return RecommendResponse(total=0, items=[])

    items = tagger.recommend(
        tag_ids=tag_ids,
        limit=payload.limit,
        min_score=payload.min_score,
        active_only=payload.active_only,
        require_tag_match=payload.require_tag_match,
    )
    return RecommendResponse(total=len(items), items=items)


@router.post("/tag-offers", response_model=TagOffersResponse)
def tag_offers(
    payload: TagOffersRequest,
    tagger: NmfTagger = Depends(get_tagger),
) -> TagOffersResponse:
    offers: list[OfferRecord] = []
    for item in payload.items:
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

    items = tagger.infer(offers)
    return TagOffersResponse(total=len(items), items=items)


@router.post("/train", response_model=list[TagResponse])
def train(payload: TrainRequest) -> list[dict]:
    data_paths = STATE.data_paths
    if not data_paths:
        raise HTTPException(status_code=500, detail="Ruta de datos no configurada")

    config = TaggerConfig(
        n_topics=payload.n_topics,
        max_features=payload.max_features,
        min_df=payload.min_df,
        max_df=payload.max_df,
        top_terms=payload.top_terms,
        topic_threshold=payload.topic_threshold,
        top_k=payload.top_k,
    )

    try:
        tagger = build_tagger(config, list(data_paths), active_only=payload.active_only)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    STATE.tagger = tagger
    return tagger.get_tags()
