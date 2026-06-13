import json
from pathlib import Path
from typing import Any


class VocabularyStyleService:
    def __init__(self) -> None:
        self.bank_path = Path(__file__).resolve().parents[1] / "data" / "turkish_vocabulary_bank.json"
        self.bank = self._load_bank()

    def enrich_reply(
        self,
        reply: str,
        brain_state: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not reply.strip() or brain_state.get("route") == "privacy_boundary":
            return {"reply": reply, "vocabulary_meta": {"applied": False, "reason": "privacy_or_empty"}}

        context = context or {}
        route = str(brain_state.get("route", "general_chat"))
        mode = self._mode(route, context)
        opener = self._select("openers", mode)
        connector = self._select_list("connectors")
        closer = self._select("closers", mode)

        if self._already_has_strong_opening(reply):
            enriched = reply
        else:
            enriched = f"{opener} {reply}"

        should_add_closer = len(enriched) < 420 and closer and closer not in enriched
        if should_add_closer and mode in {"code", "math", "deep"}:
            enriched = f"{enriched} {connector} {closer}"

        return {
            "reply": enriched,
            "vocabulary_meta": {
                "applied": enriched != reply,
                "mode": mode,
                "opener": opener,
                "connector": connector,
                "closer": closer if should_add_closer else None,
            },
        }

    def diagnostics(self) -> dict[str, Any]:
        return {
            "bank_path": str(self.bank_path),
            "openers": {key: len(value) for key, value in self.bank.get("openers", {}).items() if isinstance(value, list)},
            "connectors": len(self.bank.get("connectors", [])),
            "reasoning_phrases": len(self.bank.get("reasoning_phrases", [])),
        }

    def _mode(self, route: str, context: dict[str, Any]) -> str:
        reflection = context.get("reflection", {})
        if isinstance(reflection, dict) and reflection.get("should_expand_answer"):
            return "deep"
        if route == "code_tutor":
            return "code"
        if route == "scientific_tutor":
            return "math"
        if route == "emotional_support":
            return "emotional"
        return "general"

    def _select(self, group: str, mode: str) -> str:
        options = self.bank.get(group, {}).get(mode) if isinstance(self.bank.get(group), dict) else None
        if isinstance(options, list) and options:
            return str(options[0])
        general = self.bank.get(group, {}).get("general") if isinstance(self.bank.get(group), dict) else None
        if isinstance(general, list) and general:
            return str(general[0])
        return ""

    def _select_list(self, group: str) -> str:
        options = self.bank.get(group, [])
        if isinstance(options, list) and options:
            return str(options[0])
        return ""

    def _already_has_strong_opening(self, reply: str) -> bool:
        normalized = reply.strip().casefold()
        return normalized.startswith(("tamam", "anladım", "anladim", "selam", "sor ", "sor,", "derin", "kod", "matematik", "duydum"))

    def _load_bank(self) -> dict[str, Any]:
        try:
            loaded = json.loads(self.bank_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return loaded if isinstance(loaded, dict) else {}


vocabulary_style_service = VocabularyStyleService()
