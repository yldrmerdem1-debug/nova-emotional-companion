from typing import Any


class MemoryConsolidationService:
    def consolidate(self, workspace: dict[str, Any], goal_stack: dict[str, Any]) -> dict[str, Any]:
        profile = workspace.get("memory_context", {}).get("profile_summary", {})
        emotional = workspace.get("emotional_context", {}).get("emotional_summary", {})
        long_context = workspace.get("long_context", {}).get("summary") or workspace.get("long_context_summary", {})
        world_model = workspace.get("world_model", {})

        themes = self._themes(profile, long_context, world_model)
        user_model_summary = self._user_model_summary(profile, emotional, themes)
        project_model_summary = self._project_model_summary(profile, long_context, world_model)

        return {
            "version": "memory_consolidation_v1",
            "themes": themes,
            "user_model_summary": user_model_summary,
            "project_model_summary": project_model_summary,
            "emotional_summary": emotional,
            "goal_alignment": self._goal_alignment(goal_stack, themes),
            "memory_write_policy": self._memory_write_policy(workspace),
        }

    def _themes(self, profile: dict[str, Any], long_context: dict[str, Any], world_model: dict[str, Any]) -> list[str]:
        themes = []
        for item in long_context.get("dominant_topics", []) if isinstance(long_context, dict) else []:
            value = item.get("value") if isinstance(item, dict) else None
            if value and value not in themes:
                themes.append(str(value))
        for goal in world_model.get("active_goals", [])[:5] if isinstance(world_model, dict) else []:
            if "robot" in str(goal).casefold() and "ai_robot" not in themes:
                themes.append("ai_robot")
        for learning in profile.get("learning_profile", [])[-5:] if isinstance(profile, dict) else []:
            key = learning.get("key") if isinstance(learning, dict) else None
            if key and key not in themes:
                themes.append(str(key))
        return themes[:8]

    def _user_model_summary(self, profile: dict[str, Any], emotional: dict[str, Any], themes: list[str]) -> str:
        address = profile.get("preferred_address") if isinstance(profile, dict) else None
        style = profile.get("reply_style") if isinstance(profile, dict) else None
        mood = emotional.get("dominant_mood", "unknown") if isinstance(emotional, dict) else "unknown"
        return f"Hitap={address or 'default'}, stil={style or 'default'}, baskın duygu={mood}, temalar={', '.join(themes[:4]) or 'yok'}."

    def _project_model_summary(
        self,
        profile: dict[str, Any],
        long_context: dict[str, Any],
        world_model: dict[str, Any],
    ) -> str:
        projects = profile.get("project_context", []) if isinstance(profile, dict) else []
        memory_strength = long_context.get("memory_strength", "unknown") if isinstance(long_context, dict) else "unknown"
        focus = world_model.get("next_best_focus", {}) if isinstance(world_model, dict) else {}
        return f"Proje kayıtları={len(projects)}, uzun hafıza gücü={memory_strength}, sıradaki odak={focus.get('domain', 'unknown')}."

    def _goal_alignment(self, goal_stack: dict[str, Any], themes: list[str]) -> dict[str, Any]:
        active = goal_stack.get("active_goal", {}).get("goal", "")
        overlap = [theme for theme in themes if theme.casefold() in str(active).casefold()]
        return {
            "active_goal": active,
            "theme_overlap": overlap,
            "aligned": bool(overlap) or "robot" in str(active).casefold() or "mahremiyet" in str(active).casefold(),
        }

    def _memory_write_policy(self, workspace: dict[str, Any]) -> dict[str, Any]:
        brain_state = workspace.get("brain_state", {})
        if brain_state.get("route") == "privacy_boundary" or brain_state.get("need") == "do_not_store":
            return {"allow": False, "reason": "privacy_boundary"}
        return {"allow": bool(brain_state.get("memory_allowed", True)), "reason": "brain_policy"}


memory_consolidation_service = MemoryConsolidationService()
