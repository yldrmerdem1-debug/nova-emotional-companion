from typing import Any


class AttentionControllerService:
    PRIORITY_WEIGHTS = {
        "privacy": 1.0,
        "safety": 0.95,
        "high_emotion": 0.86,
        "explicit_user_instruction": 0.82,
        "active_goal": 0.76,
        "verification": 0.72,
        "knowledge": 0.64,
        "style": 0.5,
    }

    def rank_signals(self, workspace: dict[str, Any]) -> dict[str, Any]:
        signals = []
        brain_state = workspace.get("brain_state", {})
        brain_meta = brain_state.get("brain_meta", {}) if isinstance(brain_state, dict) else {}
        emotional = workspace.get("emotional_context", {}).get("emotional_summary", {})
        reflection = workspace.get("reflection", {})
        world_model = workspace.get("world_model", {})

        if brain_state.get("route") == "privacy_boundary" or brain_state.get("need") == "do_not_store":
            signals.append(self._signal("privacy", "Mahremiyet veya hafıza sınırı var", 1.0))
        if "high_emotion" in brain_meta.get("risk_flags", []):
            signals.append(self._signal("high_emotion", "Yüksek duygu sinyali var", 0.9))
        if emotional.get("dominant_mood") in {"low", "sad", "frustrated", "angry"}:
            signals.append(self._signal("high_emotion", "Duygusal hafıza düşük veya yoğun mod gösteriyor", 0.86))
        if brain_state.get("need") in {"direct_solution", "listen", "do_not_store"}:
            signals.append(self._signal("explicit_user_instruction", f"İhtiyaç: {brain_state.get('need')}", 0.84))
        if reflection.get("should_expand_answer"):
            signals.append(self._signal("active_goal", "Derin düşünme / geniş cevap modu", 0.78))
        if world_model.get("active_goals"):
            signals.append(self._signal("active_goal", "Uzun vadeli kullanıcı hedefi aktif", 0.74))
        if workspace.get("knowledge_context"):
            signals.append(self._signal("knowledge", "Lokal bilgi bulundu", 0.64))

        signals.sort(key=lambda signal: signal["score"], reverse=True)
        return {
            "top_signal": signals[0] if signals else self._signal("style", "Varsayılan doğal yardım modu", 0.5),
            "signals": signals,
            "policy_order": list(self.PRIORITY_WEIGHTS.keys()),
        }

    def _signal(self, signal_type: str, reason: str, score: float) -> dict[str, Any]:
        base = self.PRIORITY_WEIGHTS.get(signal_type, 0.45)
        return {
            "type": signal_type,
            "reason": reason,
            "score": round(min(1.0, max(base, score)), 3),
        }


attention_controller_service = AttentionControllerService()
