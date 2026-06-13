import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class LongContextMemoryService:
    def __init__(self) -> None:
        self.store_path = Path(__file__).resolve().parents[1] / "data" / "long_context_timeline.jsonl"

    def record_exchange(
        self,
        user_message: str,
        robot_reply: str,
        brain_state: dict[str, Any],
        memory_context: dict[str, Any],
        emotional_context: dict[str, Any],
        reflection: dict[str, Any],
        user_id: str = "default",
    ) -> dict[str, Any]:
        if brain_state.get("route") == "privacy_boundary" or brain_state.get("need") == "do_not_store":
            return {"saved": False, "reason": "privacy_boundary", "summary": self.build_context_summary(user_id)}

        record = self._record(
            user_id=user_id,
            user_message=user_message,
            robot_reply=robot_reply,
            brain_state=brain_state,
            memory_context=memory_context,
            emotional_context=emotional_context,
            reflection=reflection,
        )
        self._append_record(record)
        return {"saved": True, "record": record, "summary": self.build_context_summary(user_id)}

    def build_context_summary(self, user_id: str = "default", limit: int = 30) -> dict[str, Any]:
        records = self._load_records(user_id=user_id)[-limit:]
        if not records:
            return {
                "conversation_count": 0,
                "dominant_topics": [],
                "recurring_needs": [],
                "last_user_goals": [],
                "memory_strength": "empty",
            }

        topic_counts: dict[str, int] = {}
        need_counts: dict[str, int] = {}
        goals = []
        for record in records:
            topic = str(record.get("topic", "general"))
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
            need = str(record.get("need", "clarification"))
            need_counts[need] = need_counts.get(need, 0) + 1
            goal = record.get("long_term_goal")
            if goal and goal not in goals:
                goals.append(goal)

        return {
            "conversation_count": len(records),
            "dominant_topics": self._top_counts(topic_counts),
            "recurring_needs": self._top_counts(need_counts),
            "last_user_goals": goals[-5:],
            "memory_strength": self._memory_strength(len(records)),
            "last_seen_at": records[-1].get("created_at"),
        }

    def _record(
        self,
        user_id: str,
        user_message: str,
        robot_reply: str,
        brain_state: dict[str, Any],
        memory_context: dict[str, Any],
        emotional_context: dict[str, Any],
        reflection: dict[str, Any],
    ) -> dict[str, Any]:
        layers = reflection.get("layers", {}) if isinstance(reflection, dict) else {}
        emotional_summary = emotional_context.get("emotional_summary", {}) if isinstance(emotional_context, dict) else {}
        now = datetime.now(timezone.utc).isoformat()
        return {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "created_at": now,
            "topic": self._topic(user_message, brain_state),
            "route": brain_state.get("route"),
            "need": brain_state.get("need"),
            "emotion": brain_state.get("emotion"),
            "mood": emotional_summary.get("dominant_mood"),
            "support_preference": emotional_summary.get("support_preference"),
            "user_summary": self._summarize_text(user_message),
            "robot_summary": self._summarize_text(robot_reply),
            "long_term_goal": layers.get("long_term_user_goal"),
            "hidden_need": layers.get("possible_hidden_need"),
            "saved_memory_count": len(memory_context.get("saved_memories", [])) if isinstance(memory_context, dict) else 0,
            "importance": self._importance(brain_state, emotional_summary, reflection),
            "privacy": "private",
            "status": "active",
        }

    def _importance(
        self,
        brain_state: dict[str, Any],
        emotional_summary: dict[str, Any],
        reflection: dict[str, Any],
    ) -> float:
        importance = 0.45
        if brain_state.get("route") in {"emotional_support", "code_tutor", "scientific_tutor"}:
            importance += 0.15
        if emotional_summary.get("dominant_mood") in {"low", "sad", "frustrated"}:
            importance += 0.15
        if reflection.get("should_expand_answer"):
            importance += 0.12
        if brain_state.get("brain_meta", {}).get("risk_flags"):
            importance += 0.1
        return round(min(1.0, importance), 2)

    def _topic(self, message: str, brain_state: dict[str, Any]) -> str:
        normalized = self._normalize(message)
        topics = {
            "cpp": {"c++", "cpp", "pointer", "array", "compile"},
            "python": {"python"},
            "ai_robot": {"robot", "yapay zeka", "beyin", "hafıza", "hafiza", "llm"},
            "philosophy": {"felsefe", "bilinç", "bilinc", "anlam", "etik"},
            "emotion": {"kötüyüm", "kotuyum", "moral", "dinle", "sinir"},
        }
        for topic, terms in topics.items():
            if any(term in normalized for term in terms):
                return topic
        return str(brain_state.get("route", "general"))

    def _summarize_text(self, text: str) -> str:
        normalized = " ".join(text.strip().split())
        return normalized[:260]

    def _top_counts(self, counts: dict[str, int]) -> list[dict[str, Any]]:
        return [
            {"value": value, "count": count}
            for value, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:8]
        ]

    def _memory_strength(self, count: int) -> str:
        if count >= 50:
            return "strong"
        if count >= 15:
            return "growing"
        if count >= 5:
            return "early"
        return "seed"

    def _append_record(self, record: dict[str, Any]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with self.store_path.open("a", encoding="utf-8") as output:
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

    def _normalize(self, text: str) -> str:
        return " ".join(text.strip().casefold().split())


long_context_memory_service = LongContextMemoryService()
