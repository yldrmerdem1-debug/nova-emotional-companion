from typing import Any

from app.services.openai_service import openai_service


FALLBACK_ANALYSIS = {
    "emotion": "neutral",
    "energy": "medium",
    "need": "clarification",
    "confidence": 0.3,
}


class EmotionService:
    def analyze_user_message(self, message: str) -> dict[str, Any]:
        result = openai_service.generate_json_response(
            system_prompt=(
                "You are an emotion and intent analyzer for an AI companion robot.\n"
                "Analyze the user's message.\n"
                "Return JSON only.\n"
                "Do not overdiagnose.\n"
                "Do not claim medical certainty.\n"
                "Focus on conversational emotion and need."
            ),
            user_prompt=(
                "Return exactly these keys: emotion, energy, need, confidence.\n"
                "emotion must be one of: angry, sad, excited, tired, neutral, anxious, focused.\n"
                "energy must be one of: low, medium, high.\n"
                "need must be one of: listen, direct_solution, motivation, clarification, planning, comfort.\n"
                f"Message: {message}"
            ),
        )

        return self._normalize_analysis(result)

    def _normalize_analysis(self, result: dict[str, Any]) -> dict[str, Any]:
        emotions = {"angry", "sad", "excited", "tired", "neutral", "anxious", "focused"}
        energies = {"low", "medium", "high"}
        needs = {
            "listen",
            "direct_solution",
            "motivation",
            "clarification",
            "planning",
            "comfort",
        }

        emotion = result.get("emotion")
        energy = result.get("energy")
        need = result.get("need")
        confidence = result.get("confidence")

        if emotion not in emotions or energy not in energies or need not in needs:
            return FALLBACK_ANALYSIS.copy()

        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            return FALLBACK_ANALYSIS.copy()

        if not 0.0 <= confidence_value <= 1.0:
            return FALLBACK_ANALYSIS.copy()

        return {
            "emotion": emotion,
            "energy": energy,
            "need": need,
            "confidence": confidence_value,
        }


emotion_service = EmotionService()
