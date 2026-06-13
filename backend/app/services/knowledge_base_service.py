import json
import math
from pathlib import Path
from typing import Any


class KnowledgeBaseService:
    def __init__(self) -> None:
        self.knowledge_dir = Path(__file__).resolve().parents[1] / "data" / "knowledge_base"

    def retrieve(self, message: str, brain_state: dict[str, Any] | None = None, limit: int = 5) -> list[dict[str, Any]]:
        normalized = self._normalize(message)
        query_terms = self._terms(normalized)
        route = str((brain_state or {}).get("route", ""))
        need = str((brain_state or {}).get("need", ""))
        items = self._load_items()

        scored = []
        for item in items:
            lexical_score = self._score_item(item, query_terms, route, need)
            semantic_score = self._semantic_score(normalized, item, items)
            score = lexical_score + semantic_score
            if score > 0:
                enriched = self._with_retrieval_meta(item, score, lexical_score, semantic_score)
                scored.append((score, enriched))

        scored.sort(key=lambda entry: entry[0], reverse=True)
        return [item for _, item in scored[:limit]]

    def _load_items(self) -> list[dict[str, Any]]:
        items = []
        for path in sorted(self.knowledge_dir.glob("*.jsonl")):
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for line in lines:
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict):
                    item.setdefault("source_type", "local_seed")
                    item.setdefault("trust_level", "curated")
                    item.setdefault("confidence", 0.78)
                    item.setdefault("verification", {"status": "needs_review", "source": str(path.name)})
                    items.append(item)
        return items

    def _score_item(self, item: dict[str, Any], query_terms: set[str], route: str, need: str) -> float:
        keywords = {self._normalize(str(keyword)) for keyword in item.get("keywords", []) if isinstance(keyword, str)}
        text = self._normalize(
            " ".join(
                [
                    str(item.get("domain", "")),
                    str(item.get("title", "")),
                    str(item.get("summary", "")),
                    " ".join(keywords),
                ]
            )
        )
        item_terms = self._terms(text)
        score = float(len(query_terms & item_terms))
        score += 2.0 * len(query_terms & keywords)

        domain = str(item.get("domain", ""))
        if route == "code_tutor" and domain in {"cpp", "python"}:
            score += 3.0
        if route == "scientific_tutor" and domain in {"physics", "math"}:
            score += 3.0
        if route == "emotional_support" and domain == "emotional_support":
            score += 3.0
        if route == "privacy_boundary" and domain == "privacy":
            score += 5.0
        if "debug" in need and domain in {"cpp", "python"}:
            score += 2.0
        return score

    def _semantic_score(self, normalized_query: str, item: dict[str, Any], all_items: list[dict[str, Any]]) -> float:
        query_terms = self._terms(normalized_query)
        if not query_terms:
            return 0.0

        item_terms = self._terms(self._item_text(item))
        if not item_terms:
            return 0.0

        doc_count = max(len(all_items), 1)
        score = 0.0
        for term in query_terms:
            if term not in item_terms:
                continue
            containing = sum(1 for candidate in all_items if term in self._terms(self._item_text(candidate)))
            idf = math.log((doc_count + 1) / (containing + 1)) + 1
            score += idf

        query_norm = math.sqrt(len(query_terms))
        item_norm = math.sqrt(len(item_terms))
        if query_norm == 0 or item_norm == 0:
            return 0.0
        return round((score / (query_norm * item_norm)) * 4.0, 4)

    def _with_retrieval_meta(
        self,
        item: dict[str, Any],
        score: float,
        lexical_score: float,
        semantic_score: float,
    ) -> dict[str, Any]:
        enriched = dict(item)
        enriched["retrieval"] = {
            "score": round(score, 4),
            "lexical_score": round(lexical_score, 4),
            "semantic_score": round(semantic_score, 4),
            "method": "lexical_plus_tfidf_semantic",
        }
        enriched["verification"] = self._verification_meta(enriched)
        return enriched

    def _verification_meta(self, item: dict[str, Any]) -> dict[str, Any]:
        verification = item.get("verification")
        if not isinstance(verification, dict):
            verification = {}
        trust_level = str(item.get("trust_level", "unknown"))
        confidence = float(item.get("confidence", 0.5))
        return {
            "status": verification.get("status", "needs_review"),
            "source": verification.get("source", item.get("source_type", "unknown")),
            "trust_level": trust_level,
            "confidence": round(max(0.0, min(1.0, confidence)), 3),
            "can_use_in_answer": trust_level in {"curated", "user_verified", "system_generated"} and confidence >= 0.55,
        }

    def _item_text(self, item: dict[str, Any]) -> str:
        return " ".join(
            [
                str(item.get("domain", "")),
                str(item.get("level", "")),
                str(item.get("title", "")),
                str(item.get("summary", "")),
                " ".join(str(keyword) for keyword in item.get("keywords", []) if isinstance(keyword, str)),
                " ".join(str(step) for step in item.get("steps", []) if isinstance(step, str)),
            ]
        )

    def _terms(self, text: str) -> set[str]:
        stop_words = {"ben", "bana", "bir", "bu", "şu", "ve", "ile", "ama", "kral", "kanka", "için"}
        cleaned = "".join(character if character.isalnum() else " " for character in text)
        return {word for word in cleaned.split() if len(word) >= 3 and word not in stop_words}

    def _normalize(self, text: str) -> str:
        return " ".join(text.strip().casefold().split())


knowledge_base_service = KnowledgeBaseService()
