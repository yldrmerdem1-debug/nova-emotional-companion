import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DeepMemoryService:
    def __init__(self) -> None:
        self.store_path = Path(__file__).resolve().parents[1] / "data" / "deep_memory_store.jsonl"

    def process_message(
        self,
        message: str,
        brain_state: dict[str, Any],
        user_id: str = "default",
        modality: str = "text",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        retrieved = self.retrieve_relevant(message, user_id=user_id, limit=8)
        saved = []

        if brain_state.get("memory_allowed", True):
            candidates = self.extract_memory_candidates(message, brain_state, modality, context or {})
            saved = self.save_candidates(candidates, user_id=user_id)

        return {
            "retrieved_memories": retrieved,
            "saved_memories": saved,
            "profile_summary": self.build_profile_summary(user_id=user_id),
        }

    def extract_memory_candidates(
        self,
        message: str,
        brain_state: dict[str, Any],
        modality: str = "text",
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        normalized = self._normalize(message)
        candidates: list[dict[str, Any]] = []

        if preferred_address := self._extract_preferred_address(normalized):
            candidates.append(
                self._candidate(
                    "communication_preference",
                    "preferred_address",
                    preferred_address,
                    message,
                    confidence=0.96,
                    importance=0.92,
                    modality=modality,
                    brain_state=brain_state,
                )
            )

        if avoided_address := self._extract_avoided_address(normalized):
            candidates.append(
                self._candidate(
                    "communication_boundary",
                    "avoid_address",
                    avoided_address,
                    message,
                    confidence=0.94,
                    importance=0.9,
                    modality=modality,
                    brain_state=brain_state,
                )
            )

        if style := self._extract_reply_style(normalized):
            candidates.append(
                self._candidate(
                    "communication_preference",
                    "reply_style",
                    style,
                    message,
                    confidence=0.9,
                    importance=0.86,
                    modality=modality,
                    brain_state=brain_state,
                )
            )

        for learning_memory in self._extract_learning_profile(normalized, message, modality, brain_state):
            candidates.append(learning_memory)

        for preference in self._extract_preferences(normalized, message, modality, brain_state):
            candidates.append(preference)

        if tiny_detail := self._extract_tiny_detail(normalized, message, modality, brain_state):
            candidates.append(tiny_detail)

        if project_memory := self._extract_project_context(normalized, message, modality, brain_state):
            candidates.append(project_memory)

        return candidates

    def save_candidates(self, candidates: list[dict[str, Any]], user_id: str = "default") -> list[dict[str, Any]]:
        existing = self._load_records(user_id=user_id)
        saved = []
        for candidate in candidates:
            candidate["user_id"] = user_id
            candidate["id"] = str(uuid.uuid4())
            candidate["created_at"] = datetime.now(timezone.utc).isoformat()
            candidate["last_seen_at"] = candidate["created_at"]

            duplicate = self._find_duplicate(candidate, existing)
            if duplicate is not None:
                duplicate["last_seen_at"] = candidate["created_at"]
                duplicate["seen_count"] = int(duplicate.get("seen_count", 1)) + 1
                duplicate["confidence"] = max(float(duplicate.get("confidence", 0.0)), candidate["confidence"])
                self._rewrite_records(existing)
                saved.append(duplicate)
                continue

            candidate["seen_count"] = 1
            self._append_record(candidate)
            existing.append(candidate)
            saved.append(candidate)
        return saved

    def retrieve_relevant(self, message: str, user_id: str = "default", limit: int = 8) -> list[dict[str, Any]]:
        normalized = self._normalize(message)
        query_terms = self._terms(normalized)
        records = self._load_records(user_id=user_id)
        if not query_terms:
            return self.list_recent(user_id=user_id, limit=limit)

        scored = []
        for record in records:
            if record.get("status") == "archived":
                continue
            score = self._relevance_score(record, query_terms, normalized)
            if score <= 0:
                continue
            scored.append((score, record))

        scored.sort(
            key=lambda item: (
                item[0],
                float(item[1].get("importance", 0.0)),
                str(item[1].get("last_seen_at", "")),
            ),
            reverse=True,
        )
        return [record for _, record in scored[:limit]]

    def list_recent(self, user_id: str = "default", limit: int = 50) -> list[dict[str, Any]]:
        records = [record for record in self._load_records(user_id=user_id) if record.get("status") != "archived"]
        records.sort(key=lambda record: str(record.get("last_seen_at", record.get("created_at", ""))), reverse=True)
        return records[:limit]

    def build_profile_summary(self, user_id: str = "default") -> dict[str, Any]:
        records = self._load_records(user_id=user_id)
        summary: dict[str, Any] = {
            "preferred_address": None,
            "avoid_address": [],
            "reply_style": None,
            "learning_profile": [],
            "preferences": [],
            "tiny_details": [],
            "project_context": [],
        }

        for record in records:
            memory_type = record.get("memory_type")
            key = record.get("key")
            value = record.get("value")
            if memory_type == "communication_preference" and key == "preferred_address":
                summary["preferred_address"] = value
            elif memory_type == "communication_boundary" and key == "avoid_address":
                summary["avoid_address"].append(value)
            elif memory_type == "communication_preference" and key == "reply_style":
                summary["reply_style"] = value
            elif memory_type == "learning_profile":
                summary["learning_profile"].append(record)
            elif memory_type == "preference":
                summary["preferences"].append(record)
            elif memory_type == "tiny_detail":
                summary["tiny_details"].append(record)
            elif memory_type == "project_context":
                summary["project_context"].append(record)

        return summary

    def _candidate(
        self,
        memory_type: str,
        key: str,
        value: Any,
        evidence: str,
        confidence: float,
        importance: float,
        modality: str,
        brain_state: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "memory_type": memory_type,
            "key": key,
            "value": value,
            "evidence": evidence,
            "confidence": confidence,
            "importance": importance,
            "privacy": "private",
            "modality": modality,
            "brain_route": brain_state.get("route"),
            "brain_need": brain_state.get("need"),
            "status": "active",
        }

    def _extract_preferred_address(self, normalized: str) -> str | None:
        for address in ("kral", "kanka", "aga", "abi", "reis", "bro"):
            if f"bana {address} de" in normalized:
                return address
        return None

    def _extract_avoided_address(self, normalized: str) -> str | None:
        for address in ("kral", "kanka", "aga", "abi", "reis", "bro"):
            if f"{address} deme" in normalized:
                return address
        return None

    def _extract_reply_style(self, normalized: str) -> str | None:
        if self._contains_any(normalized, {"resmi konuşma", "resmi olma", "casual konuş", "rahat konuş"}):
            return "casual_natural"
        if self._contains_any(normalized, {"kısa ve net", "kisa ve net", "uzatma", "direkt söyle"}):
            return "short_direct"
        if self._contains_any(normalized, {"bilimsel konuş", "akademik anlat"}):
            return "scientific_clear"
        return None

    def _extract_learning_profile(
        self,
        normalized: str,
        message: str,
        modality: str,
        brain_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        memories = []
        topics = {
            "cpp": {"c++", "cpp", "pointer", "array", "compile"},
            "python": {"python"},
            "math": {"matematik", "formül", "kanıt"},
            "physics": {"fizik", "hipotez"},
            "ai": {"yapay zeka", "ai", "model"},
            "robotics": {"robot", "robotik"},
        }
        for topic, terms in topics.items():
            if not self._contains_any(normalized, terms):
                continue
            difficulty = "unknown"
            if self._contains_any(normalized, {"zorlanıyorum", "zor", "anlamıyorum", "karıştı", "patladı"}):
                difficulty = "struggling"
            elif self._contains_any(normalized, {"öğreniyorum", "ogreniyorum", "başladım", "basladim"}):
                difficulty = "learning"
            memories.append(
                self._candidate(
                    "learning_profile",
                    topic,
                    {"topic": topic, "difficulty": difficulty},
                    message,
                    confidence=0.84,
                    importance=0.82,
                    modality=modality,
                    brain_state=brain_state,
                )
            )
        return memories

    def _extract_preferences(
        self,
        normalized: str,
        message: str,
        modality: str,
        brain_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        memories = []
        if "seviyorum" in normalized or "hoşuma gidiyor" in normalized:
            memories.append(
                self._candidate(
                    "preference",
                    "likes",
                    message,
                    message,
                    confidence=0.72,
                    importance=0.62,
                    modality=modality,
                    brain_state=brain_state,
                )
            )
        if "sevmiyorum" in normalized or "hoşuma gitmiyor" in normalized:
            memories.append(
                self._candidate(
                    "preference",
                    "dislikes",
                    message,
                    message,
                    confidence=0.72,
                    importance=0.62,
                    modality=modality,
                    brain_state=brain_state,
                )
            )
        return memories

    def _extract_tiny_detail(
        self,
        normalized: str,
        message: str,
        modality: str,
        brain_state: dict[str, Any],
    ) -> dict[str, Any] | None:
        if self._contains_any(normalized, {"küçük detay", "kucuk detay", "not al", "aklında tut"}):
            return self._candidate(
                "tiny_detail",
                "user_note",
                message,
                message,
                confidence=0.82,
                importance=0.58,
                modality=modality,
                brain_state=brain_state,
            )
        return None

    def _extract_project_context(
        self,
        normalized: str,
        message: str,
        modality: str,
        brain_state: dict[str, Any],
    ) -> dict[str, Any] | None:
        if self._contains_any(normalized, {"projem", "robot projesi", "uygulamam", "backend", "frontend"}):
            return self._candidate(
                "project_context",
                "active_project",
                message,
                message,
                confidence=0.78,
                importance=0.78,
                modality=modality,
                brain_state=brain_state,
            )
        return None

    def _find_duplicate(
        self,
        candidate: dict[str, Any],
        records: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        for record in records:
            if record.get("memory_type") != candidate.get("memory_type"):
                continue
            if record.get("key") != candidate.get("key"):
                continue
            if self._normalize(json.dumps(record.get("value"), ensure_ascii=False)) == self._normalize(
                json.dumps(candidate.get("value"), ensure_ascii=False)
            ):
                return record
        return None

    def _append_record(self, record: dict[str, Any]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with self.store_path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _rewrite_records(self, records: list[dict[str, Any]]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with self.store_path.open("w", encoding="utf-8") as output:
            for record in records:
                output.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _load_records(self, user_id: str = "default") -> list[dict[str, Any]]:
        try:
            lines = self.store_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        records = []
        for line in lines:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict) and record.get("user_id", "default") == user_id:
                records.append(record)
        return records

    def _relevance_score(self, record: dict[str, Any], query_terms: set[str], normalized: str) -> float:
        haystack = self._normalize(
            " ".join(
                [
                    str(record.get("memory_type", "")),
                    str(record.get("key", "")),
                    json.dumps(record.get("value", ""), ensure_ascii=False),
                    str(record.get("evidence", "")),
                ]
            )
        )
        hay_terms = self._terms(haystack)
        overlap = len(query_terms & hay_terms)
        key_bonus = 1.5 if str(record.get("key", "")) in normalized else 0.0
        type_bonus = 1.0 if str(record.get("memory_type", "")) in normalized else 0.0
        return overlap + key_bonus + type_bonus

    def _terms(self, text: str) -> set[str]:
        stop_words = {"ben", "bana", "bir", "bu", "şu", "ve", "ile", "ama", "kral", "kanka"}
        cleaned = "".join(character if character.isalnum() else " " for character in text)
        return {word for word in cleaned.split() if len(word) >= 3 and word not in stop_words}

    def _normalize(self, text: str) -> str:
        return " ".join(text.strip().casefold().split())

    def _contains_any(self, text: str, terms: set[str]) -> bool:
        return any(term in text for term in terms)


deep_memory_service = DeepMemoryService()
