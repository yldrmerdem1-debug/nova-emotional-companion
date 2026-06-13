from typing import Any


class SelfExplanationService:
    def explain(
        self,
        workspace: dict[str, Any],
        attention: dict[str, Any],
        contradictions: dict[str, Any],
        goal_stack: dict[str, Any],
        metacognition: dict[str, Any],
    ) -> dict[str, Any]:
        brain_state = workspace.get("brain_state", {})
        top_signal = attention.get("top_signal", {})
        active_goal = goal_stack.get("active_goal", {})
        response_meta = workspace.get("response_meta", {})

        compact = (
            f"Route={brain_state.get('route')} seçildi, çünkü baskın sinyal {top_signal.get('type')} "
            f"({top_signal.get('reason')}). Aktif hedef: {active_goal.get('goal')}. "
            f"Cevap stratejisi={response_meta.get('strategy')}, güven={metacognition.get('confidence')}."
        )
        if contradictions.get("has_contradiction"):
            compact += f" Çelişki bulundu: {contradictions.get('max_severity')}."

        return {
            "compact": compact,
            "decision_factors": [
                {"factor": "route", "value": brain_state.get("route")},
                {"factor": "need", "value": brain_state.get("need")},
                {"factor": "attention", "value": top_signal},
                {"factor": "goal", "value": active_goal},
                {"factor": "strategy", "value": response_meta.get("strategy")},
            ],
            "user_visible_if_debug": compact,
        }


self_explanation_service = SelfExplanationService()
