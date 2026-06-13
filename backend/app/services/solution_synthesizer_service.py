from typing import Any


class SolutionSynthesizerService:
    def synthesize(
        self,
        message: str,
        brain_state: dict[str, Any],
        memory_context: dict[str, Any] | None,
        knowledge: list[dict[str, Any]],
        reasoning_plan: dict[str, Any],
    ) -> dict[str, Any]:
        route = str(brain_state.get("route", "general_chat"))
        strategy = str(reasoning_plan.get("strategy", "clarify_or_continue"))
        memories = memory_context or {}

        answer_points = self._answer_points(route, strategy, knowledge, reasoning_plan)
        personal_constraints = self._personal_constraints(memories)
        response_policy = self._response_policy(route, strategy, personal_constraints)

        return {
            "intent": self._intent(route, strategy),
            "strategy": strategy,
            "answer_points": answer_points,
            "personal_constraints": personal_constraints,
            "knowledge_used": [item.get("id") for item in knowledge if item.get("id")],
            "memory_used": self._memory_ids(memories),
            "response_policy": response_policy,
            "confidence": reasoning_plan.get("confidence", 0.7),
            "draft": self._draft(message, route, strategy, answer_points, personal_constraints),
        }

    def _answer_points(
        self,
        route: str,
        strategy: str,
        knowledge: list[dict[str, Any]],
        reasoning_plan: dict[str, Any],
    ) -> list[str]:
        points: list[str] = []
        for item in knowledge[:3]:
            summary = item.get("summary")
            if isinstance(summary, str) and summary:
                points.append(summary)

        for step in reasoning_plan.get("steps", [])[:4]:
            if isinstance(step, str) and step not in points:
                points.append(step)

        if route == "code_tutor" and not points:
            points.extend(["İlk hata mesajını bul", "Kod parçasını küçük parçaya indir", "Tek değişiklikle tekrar dene"])
        elif route == "scientific_tutor" and not points:
            points.extend(["Kavramı sade tanımla", "Formülü değişkenleriyle açıkla", "Kısa örnek ver"])
        elif route == "privacy_boundary":
            points = ["Bu içerik hafızaya alınmayacak", "Kısa ve net güvence verilecek"]
        elif not points:
            points.append("Kullanıcının isteğine doğrudan cevap ver")

        return points[:6]

    def _personal_constraints(self, memory_context: dict[str, Any]) -> dict[str, Any]:
        profile = memory_context.get("profile_summary", {}) if isinstance(memory_context, dict) else {}
        if not isinstance(profile, dict):
            return {}

        constraints: dict[str, Any] = {}
        if profile.get("preferred_address"):
            constraints["preferred_address"] = profile["preferred_address"]
        if profile.get("avoided_address"):
            constraints["avoided_address"] = profile["avoided_address"]
        if profile.get("reply_style"):
            constraints["reply_style"] = profile["reply_style"]
        if profile.get("learning_profile"):
            constraints["learning_profile"] = profile["learning_profile"]
        return constraints

    def _response_policy(self, route: str, strategy: str, constraints: dict[str, Any]) -> dict[str, Any]:
        policy = {
            "language": "tr",
            "offline_only": True,
            "avoid_claiming_external_access": True,
            "tone": "natural_direct",
            "max_sentences": 5,
        }
        if route == "privacy_boundary":
            policy["max_sentences"] = 2
            policy["store_memory"] = False
        if strategy in {"direct_answer", "respect_privacy"} or constraints.get("reply_style") == "short_direct":
            policy["max_sentences"] = min(int(policy["max_sentences"]), 3)
        if strategy == "listen_validate_then_invite":
            policy["tone"] = "warm_listening"
        return policy

    def _draft(
        self,
        message: str,
        route: str,
        strategy: str,
        answer_points: list[str],
        constraints: dict[str, Any],
    ) -> str:
        address = constraints.get("preferred_address")
        if route == "privacy_boundary":
            return self._addressed("Tamam, bunu hafızaya almıyorum. İçeriği saklamadan devam edebiliriz.", address)
        if strategy == "listen_validate_then_invite":
            return self._addressed("Tamam, çözüm dayatmadan dinliyorum. Anlatmak istersen buradayım.", address)
        if route == "code_tutor":
            return self._addressed(f"Önce ilk hata satırını yakalayalım. {answer_points[0]}", address)
        if route == "scientific_tutor":
            return self._addressed(f"Bunu bilimsel ama anlaşılır kuralım: {answer_points[0]}", address)
        return self._addressed(f"Anladım. {answer_points[0]}", address)

    def _addressed(self, reply: str, address: Any) -> str:
        if not isinstance(address, str) or not address.strip():
            return reply
        return f"{address.strip()}, {reply[0].lower()}{reply[1:]}"

    def _intent(self, route: str, strategy: str) -> str:
        if route == "code_tutor":
            return "debug_or_explain"
        if route == "scientific_tutor":
            return "scientific_reasoning"
        if route == "privacy_boundary":
            return "privacy_guard"
        if strategy == "listen_validate_then_invite":
            return "emotional_presence"
        return "offline_assistant_response"

    def _memory_ids(self, memory_context: dict[str, Any]) -> list[str]:
        memories = memory_context.get("relevant_memories", []) if isinstance(memory_context, dict) else []
        if not isinstance(memories, list):
            return []
        return [str(item.get("id")) for item in memories if isinstance(item, dict) and item.get("id")]


solution_synthesizer_service = SolutionSynthesizerService()
