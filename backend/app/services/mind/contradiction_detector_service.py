from typing import Any


class ContradictionDetectorService:
    def detect(self, workspace: dict[str, Any]) -> dict[str, Any]:
        contradictions = []
        brain_state = workspace.get("brain_state", {})
        memory_context = workspace.get("memory_context", {})
        response_meta = workspace.get("response_meta", {})
        emotional = workspace.get("emotional_context", {}).get("emotional_summary", {})
        curiosity = workspace.get("curiosity", {})

        if brain_state.get("route") == "privacy_boundary":
            saved = memory_context.get("saved_memories", []) if isinstance(memory_context, dict) else []
            if saved:
                contradictions.append(self._issue("critical", "privacy_memory_conflict", "Privacy route varken memory kayıt oluşmuş."))
            if curiosity.get("should_ask"):
                contradictions.append(self._issue("high", "privacy_curiosity_conflict", "Privacy sınırında merak sorusu sorulmamalı."))

        if brain_state.get("need") == "listen":
            strategy = str(response_meta.get("strategy", ""))
            if "direct_solution" in strategy or "debug" in strategy:
                contradictions.append(self._issue("medium", "listen_solution_conflict", "Kullanıcı dinlenmek isterken çözüm modu öne çıkmış."))

        if emotional.get("support_preference") == "listen_first" and brain_state.get("tone") in {"serious_direct", "plain_direct"}:
            contradictions.append(self._issue("low", "emotional_tone_tension", "Duygusal hafıza yumuşak destek isterken ton fazla direkt."))

        local_llm = response_meta.get("local_llm", {}) if isinstance(response_meta, dict) else {}
        if isinstance(local_llm, dict) and local_llm.get("status") == "ok" and brain_state.get("route") == "privacy_boundary":
            contradictions.append(self._issue("critical", "llm_privacy_conflict", "Privacy route sırasında LLM cevabı kullanılmamalı."))

        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        contradictions.sort(key=lambda item: severity_order.get(item["severity"], 0), reverse=True)
        return {
            "has_contradiction": bool(contradictions),
            "max_severity": contradictions[0]["severity"] if contradictions else "none",
            "contradictions": contradictions,
        }

    def _issue(self, severity: str, code: str, description: str) -> dict[str, str]:
        return {"severity": severity, "code": code, "description": description}


contradiction_detector_service = ContradictionDetectorService()
