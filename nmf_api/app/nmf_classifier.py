from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import numpy as np
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer


DEFAULT_STOPWORDS = [
    "a",
    "o",
    "e",
    "e",
    "do",
    "da",
    "de",
    "os",
    "as",
    "em",
    "um",
    "uma",
    "para",
    "com",
    "que",
    "no",
    "na",
    "dos",
    "das",
    "nos",
    "nas",
    "se",
    "por",
    "como",
    "mais",
    "ao",
    "aos",
    "ou",
    "sua",
    "seu",
    "sao",
    "pelo",
    "pela",
    "sobre",
    "isso",
    "este",
    "esta",
    "ser",
    "sendo",
    "projetos",
    "projeto",
    "acao",
    "acoes",
    "curso",
    "cursos",
    "alunos",
    "aluno",
    "estudantes",
    "atraves",
    "tambem",
    "bem",
    "seus",
    "suas",
    "entre",
    "nesta",
    "neste",
]


@dataclass
class OfferRecord:
    offer_id: str
    title: str
    text: str
    raw: dict[str, Any]


@dataclass
class TaggerConfig:
    n_topics: int = 18
    max_features: int = 5000
    min_df: int = 3
    max_df: float = 0.9
    ngram_range: tuple[int, int] = (1, 2)
    random_state: int = 42
    top_terms: int = 8
    topic_threshold: float = 0.1
    top_k: int = 3
    stopwords: list[str] | None = None


class NmfTagger:
    def __init__(self, config: TaggerConfig) -> None:
        self.config = config
        self.vectorizer: TfidfVectorizer | None = None
        self.model: NMF | None = None
        self.topic_terms: list[list[str]] = []
        self.topic_labels: list[str] = []
        self.offer_tags: list[list[int]] = []
        self.offer_scores: np.ndarray | None = None
        self.offers: list[OfferRecord] = []

    def fit(self, offers: list[OfferRecord]) -> None:
        if not offers:
            raise ValueError("No hay ofertas para entrenar el modelo.")

        self.offers = offers
        stopwords = self.config.stopwords or DEFAULT_STOPWORDS
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            max_features=self.config.max_features,
            min_df=self.config.min_df,
            max_df=self.config.max_df,
            ngram_range=self.config.ngram_range,
            stop_words=stopwords,
        )
        tfidf = self.vectorizer.fit_transform([o.text for o in offers])

        self.model = NMF(
            n_components=self.config.n_topics,
            init="nndsvda",
            random_state=self.config.random_state,
            max_iter=400,
        )
        W = self.model.fit_transform(tfidf)
        self.offer_scores = W

        self._build_topics()
        self._assign_offer_tags()

    def _build_topics(self) -> None:
        if not self.model or not self.vectorizer:
            return

        feature_names = np.array(self.vectorizer.get_feature_names_out())
        topic_terms: list[list[str]] = []
        topic_labels: list[str] = []

        for topic_idx, topic_weights in enumerate(self.model.components_):
            top_indices = topic_weights.argsort()[::-1][: self.config.top_terms]
            terms = feature_names[top_indices].tolist()
            topic_terms.append(terms)

            label_terms = terms[:3] if terms else [f"tema_{topic_idx}"]
            topic_labels.append(" / ".join(label_terms))

        self.topic_terms = topic_terms
        self.topic_labels = topic_labels

    def _assign_offer_tags(self) -> None:
        if self.offer_scores is None:
            return

        tags: list[list[int]] = []
        for row in self.offer_scores:
            tags.append(self._select_tags(row))
        self.offer_tags = tags

    def _select_tags(self, row: np.ndarray) -> list[int]:
        scores = list(enumerate(row))
        scores.sort(key=lambda item: item[1], reverse=True)

        selected = [
            idx for idx, score in scores if score >= self.config.topic_threshold
        ]
        if not selected:
            selected = [idx for idx, _ in scores[: self.config.top_k]]
        return selected

    def get_tags(self) -> list[dict[str, Any]]:
        return [
            {"id": idx, "label": label, "terms": terms}
            for idx, (label, terms) in enumerate(
                zip(self.topic_labels, self.topic_terms)
            )
        ]

    def recommend(
        self,
        tag_ids: list[int],
        limit: int,
        min_score: float,
        active_only: bool = False,
        require_tag_match: bool = True,
    ) -> list[dict[str, Any]]:
        if self.offer_scores is None:
            return []

        selected = [tid for tid in tag_ids if 0 <= tid < self.offer_scores.shape[1]]
        if not selected:
            return []

        scored = self._score_candidates(
            selected,
            min_score=min_score,
            active_only=active_only,
            require_tag_match=require_tag_match,
        )

        scored.sort(key=lambda item: item[0], reverse=True)
        top = scored[:limit]

        results: list[dict[str, Any]] = []
        for score, idx in top:
            offer = self.offers[idx]
            matched_tag_ids = [
                tag_id for tag_id in self.offer_tags[idx] if tag_id in selected
            ]
            tag_labels = [
                self.topic_labels[tag_id]
                for tag_id in self.offer_tags[idx]
                if tag_id < len(self.topic_labels)
            ]
            results.append(
                {
                    "score": score,
                    "offer_id": offer.offer_id,
                    "title": offer.title,
                    "tags": self.offer_tags[idx],
                    "matched_tag_ids": matched_tag_ids,
                    "tag_labels": tag_labels,
                    "is_active": self._is_active(offer.raw),
                    "offer": offer.raw,
                }
            )
        return results

    def recommend_serendipity(
        self,
        tag_ids: list[int],
        limit: int,
        min_score: float,
        active_only: bool = False,
        require_tag_match: bool = True,
        diversity_lambda: float = 0.7,
        candidate_multiplier: int = 5,
    ) -> list[dict[str, Any]]:
        if self.offer_scores is None:
            return []

        selected = [tid for tid in tag_ids if 0 <= tid < self.offer_scores.shape[1]]
        if not selected:
            return []

        candidates = self._score_candidates(
            selected,
            min_score=min_score,
            active_only=active_only,
            require_tag_match=require_tag_match,
        )
        if not candidates:
            return []

        candidate_limit = max(limit * candidate_multiplier, limit)
        candidates = candidates[:candidate_limit]
        max_score = max(score for score, _ in candidates) or 1.0

        chosen: list[tuple[float, int]] = []
        remaining = list(candidates)
        while remaining and len(chosen) < limit:
            if not chosen:
                chosen.append(remaining.pop(0))
                continue

            best_idx = 0
            best_value = -1.0
            for idx, (score, offer_idx) in enumerate(remaining):
                relevance = score / max_score
                novelty = 1.0 - max(
                    self._jaccard(self.offer_tags[offer_idx], self.offer_tags[sel_idx])
                    for _, sel_idx in chosen
                )
                value = (diversity_lambda * relevance) + (
                    (1.0 - diversity_lambda) * novelty
                )
                if value > best_value:
                    best_value = value
                    best_idx = idx

            chosen.append(remaining.pop(best_idx))

        results: list[dict[str, Any]] = []
        for score, idx in chosen:
            offer = self.offers[idx]
            matched_tag_ids = [
                tag_id for tag_id in self.offer_tags[idx] if tag_id in selected
            ]
            tag_labels = [
                self.topic_labels[tag_id]
                for tag_id in self.offer_tags[idx]
                if tag_id < len(self.topic_labels)
            ]
            results.append(
                {
                    "score": score,
                    "offer_id": offer.offer_id,
                    "title": offer.title,
                    "tags": self.offer_tags[idx],
                    "matched_tag_ids": matched_tag_ids,
                    "tag_labels": tag_labels,
                    "is_active": self._is_active(offer.raw),
                    "offer": offer.raw,
                }
            )

        return results

    def list_offers(
        self, offset: int, limit: int, active_only: bool = False
    ) -> list[dict[str, Any]]:
        if offset < 0 or limit < 1:
            return []

        results: list[dict[str, Any]] = []
        count = 0
        start = min(offset, len(self.offers))

        for idx in range(start, len(self.offers)):
            offer = self.offers[idx]
            if active_only and not self._is_active(offer.raw):
                continue
            results.append(
                {
                    "offer_id": offer.offer_id,
                    "title": offer.title,
                    "tags": self.offer_tags[idx],
                    "is_active": self._is_active(offer.raw),
                    "offer": offer.raw,
                }
            )
            count += 1
            if count >= limit:
                break

        return results

    def count_offers(self, active_only: bool = False) -> int:
        if not active_only:
            return len(self.offers)
        return sum(1 for offer in self.offers if self._is_active(offer.raw))

    def count_offers_filtered(
        self,
        active_only: bool = False,
        tag_ids: list[int] | None = None,
        require_tag_match: bool = True,
    ) -> int:
        selected = tag_ids or []
        count = 0
        for idx, offer in enumerate(self.offers):
            if active_only and not self._is_active(offer.raw):
                continue
            if selected and require_tag_match:
                if not any(tag_id in self.offer_tags[idx] for tag_id in selected):
                    continue
            count += 1
        return count

    def list_offer_outputs(
        self,
        offset: int,
        limit: int,
        active_only: bool = False,
        tag_ids: list[int] | None = None,
        require_tag_match: bool = True,
    ) -> list[dict[str, Any]]:
        if offset < 0 or limit < 1:
            return []

        results: list[dict[str, Any]] = []
        count = 0
        start = min(offset, len(self.offers))

        selected = tag_ids or []
        for idx in range(start, len(self.offers)):
            offer = self.offers[idx]
            if active_only and not self._is_active(offer.raw):
                continue
            if selected and require_tag_match:
                if not any(tag_id in self.offer_tags[idx] for tag_id in selected):
                    continue
            results.append(
                {
                    "offer_id": offer.offer_id,
                    "title": offer.title,
                    "description": self._get_description(offer.raw),
                    "modalidade": offer.raw.get("modalidade"),
                    "area_principal": offer.raw.get("area_principal"),
                    "area_secundaria": offer.raw.get("area_secundaria"),
                    "data_inicio_inscricoes": offer.raw.get("data_inicio_inscricoes"),
                    "data_termino_inscricoes": offer.raw.get("data_termino_inscricoes"),
                    "is_active": self._is_active(offer.raw),
                    "tags": self.offer_tags[idx],
                }
            )
            count += 1
            if count >= limit:
                break

        return results

    def list_offer_titles(
        self,
        offset: int,
        limit: int,
        active_only: bool = False,
        tag_ids: list[int] | None = None,
        require_tag_match: bool = True,
    ) -> list[dict[str, Any]]:
        if offset < 0 or limit < 1:
            return []

        results: list[dict[str, Any]] = []
        count = 0
        start = min(offset, len(self.offers))

        selected = tag_ids or []
        for idx in range(start, len(self.offers)):
            offer = self.offers[idx]
            if active_only and not self._is_active(offer.raw):
                continue
            if selected and require_tag_match:
                if not any(tag_id in self.offer_tags[idx] for tag_id in selected):
                    continue
            results.append(
                {
                    "title": offer.title,
                    "description": self._get_description(offer.raw),
                }
            )
            count += 1
            if count >= limit:
                break

        return results

    def infer(self, offers: list[OfferRecord]) -> list[dict[str, Any]]:
        if not offers:
            return []
        if not self.model or not self.vectorizer:
            return []

        tfidf = self.vectorizer.transform([offer.text for offer in offers])
        scores = self.model.transform(tfidf)
        results: list[dict[str, Any]] = []

        for offer, row in zip(offers, scores):
            tags = self._select_tags(row)
            tag_labels = [
                self.topic_labels[tag_id]
                for tag_id in tags
                if tag_id < len(self.topic_labels)
            ]
            results.append(
                {
                    "offer_id": offer.offer_id,
                    "title": offer.title,
                    "tags": tags,
                    "tag_labels": tag_labels,
                    "is_active": self._is_active(offer.raw),
                    "offer": offer.raw,
                }
            )

        return results

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return None
            raw = raw[:10]
            try:
                return datetime.strptime(raw, "%Y-%m-%d").date()
            except ValueError:
                return None
        return None

    def _is_active(self, offer: dict[str, Any]) -> bool:
        start = self._parse_date(offer.get("data_inicio_inscricoes"))
        end = self._parse_date(offer.get("data_termino_inscricoes"))
        today = date.today()

        if start and today < start:
            return False
        if end and today > end:
            return False
        return True

    def _score_candidates(
        self,
        selected: list[int],
        min_score: float,
        active_only: bool,
        require_tag_match: bool,
    ) -> list[tuple[float, int]]:
        if self.offer_scores is None:
            return []

        scored: list[tuple[float, int]] = []
        for idx, row in enumerate(self.offer_scores):
            if active_only and not self._is_active(self.offers[idx].raw):
                continue
            if require_tag_match and not any(
                tag_id in self.offer_tags[idx] for tag_id in selected
            ):
                continue
            score = float(np.sum(row[selected]))
            if score >= min_score:
                scored.append((score, idx))

        scored.sort(key=lambda item: item[0], reverse=True)
        return scored

    @staticmethod
    def _jaccard(a: list[int], b: list[int]) -> float:
        set_a = set(a)
        set_b = set(b)
        if not set_a and not set_b:
            return 0.0
        return len(set_a & set_b) / len(set_a | set_b)

    @staticmethod
    def _get_description(offer: dict[str, Any]) -> str:
        description = offer.get("descricao")
        if isinstance(description, str) and description.strip():
            return description.strip()
        resumo = offer.get("resumo")
        if isinstance(resumo, str) and resumo.strip():
            return resumo.strip()
        objetivos = offer.get("objetivos")
        if isinstance(objetivos, str) and objetivos.strip():
            return objetivos.strip()
        return ""
