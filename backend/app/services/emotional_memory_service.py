import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class EmotionalMemoryService:
    NEGATIVE_TERMS = {
        "kötüyüm",
        "kotuyum",
        "moralim bozuk",
        "canım sıkkın",
        "canim sikkin",
        "üzgün",
        "uzgun",
        "yalnız",
        "yalniz",
        "bunaldım",
        "bunaldim",
        "kaygılı",
        "kaygili",
        "sinir",
    }
    POSITIVE_TERMS = {"iyiyim", "mutluyum", "sevindim", "güzel", "guzel", "harika", "başardım", "basardim"}
    LISTEN_TERMS = {"sadece dinle", "çözüm istemiyorum", "cozum istemiyorum", "akıl verme", "akil verme", "yargılama", "yargilama"}
    SOLUTION_TERMS = {"çözüm bulalım", "cozum bulalim", "ne yapacağım", "ne yapacagim", "yardım et", "yardim et"}
    BRIEF_TERMS = {"kısa cevap", "kisa cevap", "uzatma", "kısa kes", "kisa kes"}

    def __init__(self) -> None:
        self.store_path = Path(__file__).resolve().parents[1] / "data" / "emotional_memory_store.jsonl"

    def process_message(
        self,
        message: str,
        brain_state: dict[str, Any],
        user_id: str = "default",
    ) -> dict[str, Any]:
        if brain_state.get("route") == "privacy_boundary" or brain_state.get("need") == "do_not_store":
            return {"saved_emotional_record": None, "emotional_summary": self.build_emotional_summary(user_id)}

        record = self._build_record(message, brain_state, user_id)
        saved = None
        if record["mood"] != "neutral" or record["support_preference"] != "unknown":
            self._append_record(record)
            saved = record
        return {
            "saved_emotional_record": saved,
            "emotional_summary": self.build_emotional_summary(user_id),
        }

    def build_emotional_summary(self, user_id: str = "default", limit: int = 12) -> dict[str, Any]:
        records = self._load_records(user_id=user_id)
        recent = records[-limit:]
        if not recent:
            return {
                "dominant_mood": "unknown",
                "support_preference": "unknown",
                "mood_timeline": [],
                "care_suggestions": [],
            }

        mood_counts: dict[str, int] = {}
        support_counts: dict[str, int] = {}
        for record in recent:
            mood = str(record.get("mood", "neutral"))
            mood_counts[mood] = mood_counts.get(mood, 0) + 1
            support = str(record.get("support_preference", "unknown"))
            if support != "unknown":
                support_counts[support] = support_counts.get(support, 0) + 1

        dominant_mood = max(mood_counts.items(), key=lambda item: item[1])[0]
        support_preference = max(support_counts.items(), key=lambda item: item[1])[0] if support_counts else "unknown"
        return {
            "dominant_mood": dominant_mood,
            "support_preference": support_preference,
            "mood_timeline": [
                {
                    "mood": record.get("mood"),
                    "intensity": record.get("intensity"),
                    "created_at": record.get("created_at"),
                    "trigger_terms": record.get("trigger_terms", []),
                }
                for record in recent
            ],
            "care_suggestions": self._care_suggestions(dominant_mood, support_preference),
        }

    def _build_record(self, message: str, brain_state: dict[str, Any], user_id: str) -> dict[str, Any]:
        normalized = self._normalize(message)
        mood = self._detect_mood(normalized, brain_state)
        support_preference = self._support_preference(normalized)
        trigger_terms = sorted(
            term
            for term in self.NEGATIVE_TERMS | self.POSITIVE_TERMS | self.LISTEN_TERMS | self.SOLUTION_TERMS | self.BRIEF_TERMS
            if term in normalized
        )
        intensity = self._intensity(normalized, mood)
        now = datetime.now(timezone.utc).isoformat()
        return {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "mood": mood,
            "intensity": intensity,
            "support_preference": support_preference,
            "trigger_terms": trigger_terms,
            "evidence": message,
            "brain_route": brain_state.get("route"),
            "brain_emotion": brain_state.get("emotion"),
            "created_at": now,
            "privacy": "private",
            "status": "active",
        }

    def _detect_mood(self, normalized: str, brain_state: dict[str, Any]) -> str:
        if self._contains_any(normalized, self.NEGATIVE_TERMS):
            if self._contains_any(normalized, {"sinir", "bıktım", "biktim", "deliricem"}):
                return "frustrated"
            return "low"
        if self._contains_any(normalized, self.POSITIVE_TERMS):
            return "positive"
        emotion = str(brain_state.get("emotion", "neutral"))
        if emotion in {"sad", "anxious", "frustrated", "angry"}:
            return emotion
        return "neutral"

    def _support_preference(self, normalized: str) -> str:
        if self._contains_any(normalized, self.LISTEN_TERMS):
            return "listen_first"
        if self._contains_any(normalized, self.SOLUTION_TERMS):
            return "reflect_then_solve"
        if self._contains_any(normalized, self.BRIEF_TERMS):
            return "brief"
        return "unknown"

    def _intensity(self, normalized: str, mood: str) -> float:
        if mood == "neutral":
            return 0.1
        intensity = 0.55
        if self._contains_any(normalized, {"çok", "cok", "aşırı", "asiri", "deliricem", "mahvoldum"}):
            intensity += 0.25
        if self._contains_any(normalized, {"biraz", "azıcık", "azicik"}):
            intensity -= 0.15
        return round(max(0.1, min(1.0, intensity)), 2)

    def _care_suggestions(self, dominant_mood: str, support_preference: str) -> list[str]:
        suggestions = []
        if support_preference == "listen_first":
            suggestions.append("Önce dinle, çözüm önermeden duyguyu kabul et.")
        if support_preference == "reflect_then_solve":
            suggestions.append("Önce duyguyu yansıt, sonra izin alıp tek küçük adım öner.")
        if support_preference == "brief":
            suggestions.append("Kısa, sakin ve düşük baskılı cevap ver.")
        if dominant_mood in {"low", "sad", "anxious"}:
            suggestions.append("Yumuşak ve düşük baskılı konuş.")
        if dominant_mood in {"frustrated", "angry"}:
            suggestions.append("Kısa, sakin ve kontrol hissi veren cevap ver.")
        if not suggestions:
            suggestions.append("Doğal, sıcak ve kısa devam et.")
        return suggestions

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

    def _contains_any(self, text: str, terms: set[str]) -> bool:
        return any(term in text for term in terms)

    def _normalize(self, text: str) -> str:
        return " ".join(text.strip().casefold().split())


emotional_memory_service = EmotionalMemoryService()
