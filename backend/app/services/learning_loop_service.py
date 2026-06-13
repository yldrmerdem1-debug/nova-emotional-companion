import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class LearningLoopService:
    def __init__(self) -> None:
        self.store_path = Path(__file__).resolve().parents[1] / "data" / "learning_loop_store.jsonl"

    def process_exchange(
        self,
        user_message: str,
        robot_reply: str,
        brain_state: dict[str, Any],
        memory_context: dict[str, Any],
        knowledge_context: list[dict[str, Any]],
        reasoning_plan: dict[str, Any],
        user_id: str = "default",
    ) -> dict[str, Any]:
        if brain_state.get("route") == "privacy_boundary" or brain_state.get("need") == "do_not_store":
            return {
                "saved_learning_records": [],
                "learning_summary": {"status": "skipped_privacy_boundary"},
            }

        candidates = self._build_candidates(
            user_message,
            robot_reply,
            brain_state,
            memory_context,
            knowledge_context,
            reasoning_plan,
            user_id,
        )
        saved = self._save_candidates(candidates)
        return {
            "saved_learning_records": saved,
            "learning_summary": self.build_learning_summary(user_id=user_id),
        }

    def build_learning_summary(self, user_id: str = "default") -> dict[str, Any]:
        records = self._load_records(user_id=user_id)
        summary = {
            "total_records": len(records),
            "strong_topics": [],
            "open_questions": [],
            "recent_mistakes": [],
            "knowledge_candidates": [],
        }
        topic_counts: dict[str, int] = {}
        for record in records:
            topic = str(record.get("topic", "general"))
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
            if record.get("record_type") == "open_question":
                summary["open_questions"].append(record)
            elif record.get("record_type") == "mistake_signal":
                summary["recent_mistakes"].append(record)
            elif record.get("record_type") == "knowledge_candidate":
                summary["knowledge_candidates"].append(record)

        summary["strong_topics"] = [
            {"topic": topic, "count": count}
            for topic, count in sorted(topic_counts.items(), key=lambda item: item[1], reverse=True)[:8]
        ]
        summary["open_questions"] = summary["open_questions"][-5:]
        summary["recent_mistakes"] = summary["recent_mistakes"][-5:]
        summary["knowledge_candidates"] = summary["knowledge_candidates"][-5:]
        return summary

    def _build_candidates(
        self,
        user_message: str,
        robot_reply: str,
        brain_state: dict[str, Any],
        memory_context: dict[str, Any],
        knowledge_context: list[dict[str, Any]],
        reasoning_plan: dict[str, Any],
        user_id: str,
    ) -> list[dict[str, Any]]:
        normalized = self._normalize(user_message)
        route = str(brain_state.get("route", "general_chat"))
        topic = self._topic_from_message(normalized, route)
        candidates = [
            self._record(
                user_id=user_id,
                record_type="exchange_trace",
                topic=topic,
                evidence=user_message,
                value={
                    "route": route,
                    "need": brain_state.get("need"),
                    "strategy": reasoning_plan.get("strategy"),
                    "knowledge_used": [item.get("id") for item in knowledge_context if item.get("id")],
                    "reply_preview": robot_reply[:220],
                },
                confidence=0.72,
                importance=0.55,
            )
        ]

        if self._contains_any(normalized, {"yanlış", "yanlis", "olmadı", "olmadi", "saçma", "sacma", "düzelt", "duzelt"}):
            candidates.append(
                self._record(
                    user_id=user_id,
                    record_type="mistake_signal",
                    topic=topic,
                    evidence=user_message,
                    value={"message": user_message, "robot_reply": robot_reply[:300]},
                    confidence=0.88,
                    importance=0.9,
                )
            )

        if self._contains_any(normalized, {"şunu öğren", "sunu ogren", "bilgi olarak", "not et", "aklında tut"}):
            candidates.append(
                self._record(
                    user_id=user_id,
                    record_type="knowledge_candidate",
                    topic=topic,
                    evidence=user_message,
                    value={"candidate_text": user_message, "source": "user_conversation"},
                    confidence=0.78,
                    importance=0.82,
                )
            )

        if "?" in user_message and not knowledge_context:
            candidates.append(
                self._record(
                    user_id=user_id,
                    record_type="open_question",
                    topic=topic,
                    evidence=user_message,
                    value={"question": user_message, "reason": "no_local_knowledge_match"},
                    confidence=0.7,
                    importance=0.74,
                )
            )

        saved_memory_count = len(memory_context.get("saved_memories", [])) if isinstance(memory_context, dict) else 0
        if saved_memory_count:
            candidates.append(
                self._record(
                    user_id=user_id,
                    record_type="memory_learning_trace",
                    topic="personal_memory",
                    evidence=user_message,
                    value={"saved_memory_count": saved_memory_count},
                    confidence=0.86,
                    importance=0.78,
                )
            )

        return candidates

    def _record(
        self,
        user_id: str,
        record_type: str,
        topic: str,
        evidence: str,
        value: dict[str, Any],
        confidence: float,
        importance: float,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "record_type": record_type,
            "topic": topic,
            "evidence": evidence,
            "value": value,
            "confidence": confidence,
            "importance": importance,
            "created_at": now,
            "last_seen_at": now,
            "status": "active",
        }

    def _save_candidates(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        existing = self._load_records(include_all_users=True)
        saved = []
        for candidate in candidates:
            duplicate = self._find_duplicate(candidate, existing)
            if duplicate is not None:
                duplicate["last_seen_at"] = candidate["last_seen_at"]
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

    def _find_duplicate(self, candidate: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any] | None:
        for record in records:
            if record.get("user_id") != candidate.get("user_id"):
                continue
            if record.get("record_type") != candidate.get("record_type"):
                continue
            if record.get("topic") != candidate.get("topic"):
                continue
            if self._normalize(str(record.get("evidence", ""))) == self._normalize(str(candidate.get("evidence", ""))):
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

    def _load_records(self, user_id: str = "default", include_all_users: bool = False) -> list[dict[str, Any]]:
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
            if isinstance(record, dict) and (include_all_users or record.get("user_id", "default") == user_id):
                records.append(record)
        return records

    def _topic_from_message(self, normalized: str, route: str) -> str:
        topics = {
            "cpp": {"c++", "cpp", "pointer", "array", "compile"},
            "python": {"python"},
            "physics": {"fizik", "kuvvet", "enerji"},
            "math": {"matematik", "formül", "formul", "kanıt", "kanit"},
            "ai_robot": {"robot", "yapay zeka", "model", "beyin", "hafıza", "hafiza"},
            "emotional": {"kötüyüm", "kotuyum", "moralim", "dinle", "üzgün", "uzgun"},
        }
        for topic, terms in topics.items():
            if self._contains_any(normalized, terms):
                return topic
        return route or "general"

    def _contains_any(self, text: str, terms: set[str]) -> bool:
        return any(term in text for term in terms)

    def _normalize(self, text: str) -> str:
        return " ".join(text.strip().casefold().split())


learning_loop_service = LearningLoopService()
