from typing import Any


class MetaCognitionService:
    def evaluate(
        self,
        workspace: dict[str, Any],
        attention: dict[str, Any],
        contradictions: dict[str, Any],
        causal_graph: dict[str, Any],
    ) -> dict[str, Any]:
        confidence = self._confidence(workspace, attention, contradictions)
        actions = []
        if contradictions.get("max_severity") in {"critical", "high"}:
            actions.append("repair_before_answer")
        if confidence < 0.62:
            actions.append("ask_clarifying_question")
        if attention.get("top_signal", {}).get("type") == "privacy":
            actions.append("disable_memory_and_keep_short")
        if workspace.get("reflection", {}).get("should_expand_answer") and confidence >= 0.7:
            actions.append("expand_with_reasoned_structure")
        if not actions:
            actions.append("answer_normally")

        return {
            "confidence": confidence,
            "uncertainty": round(1.0 - confidence, 3),
            "recommended_actions": actions,
            "self_check": self._self_check(workspace, contradictions, causal_graph),
        }

    def _confidence(self, workspace: dict[str, Any], attention: dict[str, Any], contradictions: dict[str, Any]) -> float:
        brain_meta = workspace.get("brain_state", {}).get("brain_meta", {})
        base = float(brain_meta.get("confidence", 0.72)) if isinstance(brain_meta, dict) else 0.72
        if workspace.get("knowledge_context"):
            base += 0.05
        if attention.get("top_signal", {}).get("score", 0) >= 0.9:
            base += 0.04
        if contradictions.get("has_contradiction"):
            severity = contradictions.get("max_severity")
            base -= {"critical": 0.35, "high": 0.25, "medium": 0.14, "low": 0.06}.get(severity, 0.1)
        return round(max(0.05, min(0.99, base)), 3)

    def _self_check(
        self,
        workspace: dict[str, Any],
        contradictions: dict[str, Any],
        causal_graph: dict[str, Any],
    ) -> list[str]:
        checks = []
        checks.append("Brain route, need, emotion, memory and response strategy were inspected.")
        checks.append(f"Causal graph built with {len(causal_graph.get('nodes', []))} nodes.")
        if contradictions.get("has_contradiction"):
            checks.append("Contradictions detected; repair policy should run.")
        else:
            checks.append("No major contradiction detected.")
        if workspace.get("world_model", {}).get("weaknesses"):
            checks.append("World model weaknesses are available for future curriculum.")
        return checks


metacognition_service = MetaCognitionService()
