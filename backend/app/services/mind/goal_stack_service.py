from typing import Any


class GoalStackService:
    def build_goal_stack(self, workspace: dict[str, Any], attention: dict[str, Any]) -> dict[str, Any]:
        brain_state = workspace.get("brain_state", {})
        world_model = workspace.get("world_model", {})
        reflection_layers = workspace.get("reflection", {}).get("layers", {})

        immediate = self._immediate_goal(brain_state, attention)
        session = reflection_layers.get("best_next_move") or "Kullanıcının mevcut isteğini netleştir"
        long_term = world_model.get("active_goals", []) or ["Kişisel AI robot beynini geliştirmek"]

        goals = [
            {"horizon": "immediate", "goal": immediate, "priority": 1.0},
            {"horizon": "session", "goal": session, "priority": 0.78},
        ]
        for index, goal in enumerate(long_term[:5]):
            goals.append({"horizon": "long_term", "goal": goal, "priority": round(0.64 - index * 0.05, 3)})

        return {
            "active_goal": goals[0],
            "goals": goals,
            "conflict_policy": "privacy > safety > emotion > explicit instruction > long-term learning > style",
        }

    def _immediate_goal(self, brain_state: dict[str, Any], attention: dict[str, Any]) -> str:
        top_type = attention.get("top_signal", {}).get("type")
        if top_type == "privacy":
            return "Mahremiyet sınırını koru ve hafızaya yazma"
        if brain_state.get("need") == "listen":
            return "Çözüm dayatmadan dinle ve güvenli alan aç"
        if brain_state.get("route") == "code_tutor":
            return "Kod problemini küçük doğrulanabilir adıma indir"
        if brain_state.get("route") == "scientific_tutor":
            return "Kavramı bilimsel ama anlaşılır şekilde kur"
        return "Kullanıcıya en faydalı sonraki adımı ver"


goal_stack_service = GoalStackService()
