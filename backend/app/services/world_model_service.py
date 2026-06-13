from typing import Any

from app.services.deep_memory_service import deep_memory_service
from app.services.emotional_memory_service import emotional_memory_service
from app.services.learning_loop_service import learning_loop_service
from app.services.long_context_memory_service import long_context_memory_service
from app.services.self_training_service import self_training_service


class WorldModelService:
    def build_world_model(self, user_id: str = "default") -> dict[str, Any]:
        profile = deep_memory_service.build_profile_summary(user_id=user_id)
        emotional = emotional_memory_service.build_emotional_summary(user_id=user_id)
        learning = learning_loop_service.build_learning_summary(user_id=user_id)
        long_context = long_context_memory_service.build_context_summary(user_id=user_id)
        self_training = {
            "cpp": self_training_service.progress("cpp"),
            "python": self_training_service.progress("python"),
            "java": self_training_service.progress("java"),
            "math": self_training_service.progress("math"),
            "physics": self_training_service.progress("physics"),
            "algorithms": self_training_service.progress("algorithms"),
        }

        return {
            "version": "world_model_v1",
            "user_id": user_id,
            "user_profile": profile,
            "emotional_state": emotional,
            "learning_state": learning,
            "long_context": long_context,
            "self_training": self_training,
            "active_goals": self._active_goals(profile, long_context),
            "weaknesses": self._weaknesses(self_training),
            "strengths": self._strengths(self_training),
            "next_best_focus": self._next_best_focus(self_training, emotional),
        }

    def _active_goals(self, profile: dict[str, Any], long_context: dict[str, Any]) -> list[str]:
        goals = []
        for goal in long_context.get("last_user_goals", []):
            if isinstance(goal, str) and goal not in goals:
                goals.append(goal)
        projects = profile.get("project_context", []) if isinstance(profile, dict) else []
        if projects:
            goals.append("Kişisel AI robot projesini büyütmek")
        learning = profile.get("learning_profile", []) if isinstance(profile, dict) else []
        for item in learning[-3:]:
            if isinstance(item, dict) and item.get("key"):
                goals.append(f"{item['key']} öğrenimini güçlendirmek")
        return goals[:8]

    def _weaknesses(self, self_training: dict[str, Any]) -> list[dict[str, Any]]:
        weaknesses = []
        for domain, progress in self_training.items():
            success_rate = float(progress.get("success_rate", 0.0))
            total = int(progress.get("total", 0))
            bank_count = int(progress.get("bank_count", 0))
            if total < max(5, bank_count // 2):
                weaknesses.append({"domain": domain, "reason": "low_coverage", "total": total, "bank_count": bank_count})
            if success_rate < 0.8:
                weaknesses.append({"domain": domain, "reason": "low_success_rate", "success_rate": success_rate})
            for mistake in progress.get("mistake_types", [])[:3]:
                weaknesses.append({"domain": domain, "reason": "mistake_pattern", "mistake": mistake})
        return weaknesses

    def _strengths(self, self_training: dict[str, Any]) -> list[dict[str, Any]]:
        strengths = []
        for domain, progress in self_training.items():
            if int(progress.get("total", 0)) >= 5 and float(progress.get("success_rate", 0.0)) >= 0.9:
                strengths.append(
                    {
                        "domain": domain,
                        "reason": "high_success_rate",
                        "success_rate": progress.get("success_rate"),
                        "next_difficulty": progress.get("next_difficulty"),
                    }
                )
        return strengths

    def _next_best_focus(self, self_training: dict[str, Any], emotional: dict[str, Any]) -> dict[str, Any]:
        if emotional.get("dominant_mood") in {"low", "sad", "frustrated"}:
            return {"mode": "gentle_training", "domain": "math", "reason": "low_emotional_load"}

        candidates = []
        for domain, progress in self_training.items():
            total = int(progress.get("total", 0))
            bank_count = int(progress.get("bank_count", 0))
            success_rate = float(progress.get("success_rate", 0.0))
            coverage_gap = max(bank_count - total, 0)
            score = coverage_gap + (1.0 - success_rate) * 10
            candidates.append((score, domain, progress))
        candidates.sort(reverse=True)
        if not candidates:
            return {"mode": "seed_training", "domain": "cpp", "reason": "no_training_state"}
        _, domain, progress = candidates[0]
        return {
            "mode": "adaptive_training",
            "domain": domain,
            "difficulty": progress.get("next_difficulty", 1),
            "reason": "largest_coverage_or_error_gap",
        }


world_model_service = WorldModelService()
