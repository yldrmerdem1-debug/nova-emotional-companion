from typing import Any


class CausalReasoningGraphService:
    def build_graph(self, workspace: dict[str, Any], attention: dict[str, Any]) -> dict[str, Any]:
        brain_state = workspace.get("brain_state", {})
        emotional = workspace.get("emotional_context", {}).get("emotional_summary", {})
        world_model = workspace.get("world_model", {})
        nodes = []
        edges = []

        self._add(nodes, "user_message", "input", workspace.get("message", ""))
        self._add(nodes, "brain_route", "state", brain_state.get("route"))
        self._add(nodes, "need", "state", brain_state.get("need"))
        self._add(nodes, "mood", "state", emotional.get("dominant_mood"))
        self._add(nodes, "top_attention", "policy", attention.get("top_signal", {}).get("type"))
        self._add(nodes, "next_focus", "goal", world_model.get("next_best_focus", {}).get("domain"))
        self._add(nodes, "response_strategy", "action", workspace.get("response_meta", {}).get("strategy"))

        self._edge(edges, "user_message", "brain_route", "message classified into route")
        self._edge(edges, "brain_route", "need", "route constrains need")
        self._edge(edges, "mood", "top_attention", "emotion affects attention")
        self._edge(edges, "need", "top_attention", "explicit need affects priority")
        self._edge(edges, "top_attention", "response_strategy", "attention selects response policy")
        self._edge(edges, "next_focus", "response_strategy", "long-term goal biases next action")

        return {
            "nodes": nodes,
            "edges": edges,
            "causal_summary": self._summary(brain_state, emotional, attention, world_model),
        }

    def _add(self, nodes: list[dict[str, Any]], node_id: str, kind: str, value: Any) -> None:
        nodes.append({"id": node_id, "kind": kind, "value": value})

    def _edge(self, edges: list[dict[str, str]], source: str, target: str, relation: str) -> None:
        edges.append({"source": source, "target": target, "relation": relation})

    def _summary(
        self,
        brain_state: dict[str, Any],
        emotional: dict[str, Any],
        attention: dict[str, Any],
        world_model: dict[str, Any],
    ) -> str:
        return (
            f"Route={brain_state.get('route')} ve need={brain_state.get('need')} "
            f"duygu={emotional.get('dominant_mood', 'unknown')} ile birleşti. "
            f"En baskın sinyal={attention.get('top_signal', {}).get('type')}. "
            f"Uzun hedef odağı={world_model.get('next_best_focus', {}).get('domain', 'unknown')}."
        )


causal_reasoning_graph_service = CausalReasoningGraphService()
