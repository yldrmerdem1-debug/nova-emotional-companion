from typing import Any

from app.services.mind.attention_controller_service import attention_controller_service
from app.services.mind.causal_reasoning_graph_service import causal_reasoning_graph_service
from app.services.mind.contradiction_detector_service import contradiction_detector_service
from app.services.mind.goal_stack_service import goal_stack_service
from app.services.mind.memory_consolidation_service import memory_consolidation_service
from app.services.mind.metacognition_service import metacognition_service
from app.services.mind.self_explanation_service import self_explanation_service


class GlobalWorkspaceService:
    def integrate(self, workspace: dict[str, Any]) -> dict[str, Any]:
        attention = attention_controller_service.rank_signals(workspace)
        contradictions = contradiction_detector_service.detect(workspace)
        causal_graph = causal_reasoning_graph_service.build_graph(workspace, attention)
        goal_stack = goal_stack_service.build_goal_stack(workspace, attention)
        metacognition = metacognition_service.evaluate(workspace, attention, contradictions, causal_graph)
        consolidation = memory_consolidation_service.consolidate(workspace, goal_stack)
        self_explanation = self_explanation_service.explain(
            workspace,
            attention,
            contradictions,
            goal_stack,
            metacognition,
        )

        return {
            "version": "global_workspace_v1",
            "attention": attention,
            "contradictions": contradictions,
            "causal_graph": causal_graph,
            "goal_stack": goal_stack,
            "metacognition": metacognition,
            "memory_consolidation": consolidation,
            "self_explanation": self_explanation,
            "final_policy": self._final_policy(attention, contradictions, metacognition),
        }

    def _final_policy(
        self,
        attention: dict[str, Any],
        contradictions: dict[str, Any],
        metacognition: dict[str, Any],
    ) -> dict[str, Any]:
        if contradictions.get("max_severity") in {"critical", "high"}:
            return {"action": "repair_or_abort", "reason": "serious_contradiction"}
        if "disable_memory_and_keep_short" in metacognition.get("recommended_actions", []):
            return {"action": "short_privacy_safe_answer", "reason": "privacy_attention"}
        if "ask_clarifying_question" in metacognition.get("recommended_actions", []):
            return {"action": "ask_clarifying_question", "reason": "low_confidence"}
        if attention.get("top_signal", {}).get("type") == "high_emotion":
            return {"action": "emotion_first_answer", "reason": "emotion_priority"}
        return {"action": "answer_with_context", "reason": "stable_workspace"}


global_workspace_service = GlobalWorkspaceService()
