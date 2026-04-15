from __future__ import annotations

from pydantic import BaseModel, Field


class TrainRequest(BaseModel):
    n_topics: int = Field(18, ge=2, le=50)
    max_features: int = Field(5000, ge=100, le=20000)
    min_df: int = Field(3, ge=1, le=20)
    max_df: float = Field(0.9, gt=0.1, le=1.0)
    top_terms: int = Field(8, ge=3, le=20)
    topic_threshold: float = Field(0.1, ge=0.0, le=1.0)
    top_k: int = Field(3, ge=1, le=10)
    active_only: bool = False


class RecommendRequest(BaseModel):
    tag_ids: list[int] = Field(default_factory=list)
    limit: int = Field(10, ge=1, le=50)
    min_score: float = Field(0.0, ge=0.0)
    active_only: bool = False
    require_tag_match: bool = True


class RecommendSerendipityRequest(BaseModel):
    tag_ids: list[int] = Field(default_factory=list)
    limit: int = Field(10, ge=1, le=50)
    min_score: float = Field(0.0, ge=0.0)
    active_only: bool = False
    require_tag_match: bool = True
    diversity_lambda: float = Field(0.7, ge=0.0, le=1.0)
    candidate_multiplier: int = Field(5, ge=1, le=20)


class RecommendByUserRequest(BaseModel):
    user_id: int = Field(..., ge=1)
    limit: int = Field(10, ge=1, le=50)
    min_score: float = Field(0.0, ge=0.0)
    active_only: bool = False
    require_tag_match: bool = True


class TagResponse(BaseModel):
    id: int
    label: str
    terms: list[str]


class RecommendItem(BaseModel):
    score: float
    offer_id: str
    title: str
    tags: list[int]
    matched_tag_ids: list[int]
    tag_labels: list[str]
    is_active: bool
    offer: dict


class RecommendResponse(BaseModel):
    total: int
    items: list[RecommendItem]


class OfferTagItem(BaseModel):
    offer_id: str
    title: str
    tags: list[int]
    is_active: bool
    offer: dict


class OfferTagsResponse(BaseModel):
    total: int
    items: list[OfferTagItem]


class OfferOutputItem(BaseModel):
    offer_id: str
    title: str
    description: str
    modalidade: str | None = None
    area_principal: str | None = None
    area_secundaria: str | None = None
    data_inicio_inscricoes: str | None = None
    data_termino_inscricoes: str | None = None
    is_active: bool
    tags: list[int]


class OfferOutputResponse(BaseModel):
    total: int
    items: list[OfferOutputItem]


class OfferTitleDescriptionItem(BaseModel):
    title: str
    description: str


class OfferTitleDescriptionResponse(BaseModel):
    total: int
    items: list[OfferTitleDescriptionItem]


class TagOffersRequest(BaseModel):
    items: list[dict]


class TaggedOfferItem(BaseModel):
    offer_id: str
    title: str
    tags: list[int]
    tag_labels: list[str]
    is_active: bool
    offer: dict


class TagOffersResponse(BaseModel):
    total: int
    items: list[TaggedOfferItem]


class NotificationOffersRequest(BaseModel):
    user_id: int = Field(..., ge=1)
    limit: int = Field(5, ge=1, le=20)
    min_score: float = Field(0.0, ge=0.0)
    active_only: bool = False
    require_tag_match: bool = True
    heading: str | None = None
    dry_run: bool = False


class NotificationOfferItem(BaseModel):
    offer_id: str | None = None
    title: str | None = None
    description: str | None = None


class NotificationOffersResponse(BaseModel):
    total: int
    items: list[NotificationOfferItem]
    onesignal: dict


class NotificationSendRequest(BaseModel):
    external_user_ids: list[str] | None = None
    included_segments: list[str] | None = None
    filters: list[dict] | None = None
    headings: dict[str, str]
    contents: dict[str, str]
    data: dict | None = None
    dry_run: bool = False


class NotificationSendResponse(BaseModel):
    onesignal: dict
