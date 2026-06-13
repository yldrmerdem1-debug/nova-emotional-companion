from typing import Any

from app.services.openai_service import openai_service


class SafetyService:
    def analyze_safety(
        self,
        user_message: str,
        draft_response: str,
        context_mode: str,
    ) -> dict[str, Any]:
        rule_result = self._rule_based_check(user_message, draft_response, context_mode)
        if rule_result is not None:
            return rule_result

        llm_result = openai_service.generate_json_response(
            system_prompt=(
                "You are a safety reviewer for an AI companion robot.\n"
                "Check for dangerous, manipulative, privacy-violating, or human-identity claims.\n"
                "Do not over-block normal emotional support.\n"
                "Return JSON with: allowed, risk_level, reason, safe_response_override."
            ),
            user_prompt=(
                f"Context mode: {context_mode}\n"
                f"User message: {user_message}\n"
                f"Draft response: {draft_response}"
            ),
        )
        return self._normalize_llm_result(llm_result)

    def _rule_based_check(
        self,
        user_message: str,
        draft_response: str,
        context_mode: str,
    ) -> dict[str, Any] | None:
        normalized_user_message = user_message.lower()
        normalized_draft = draft_response.lower()

        if self._contains_crisis_language(normalized_user_message):
            return {
                "allowed": False,
                "risk_level": "high",
                "reason": "Crisis or self-harm language detected.",
                "safe_response_override": (
                    "Bunu yasiyor olman cok agir gelebilir. Su anda yalniz kalmamani, "
                    "hemen yerel acil yardim hattina veya guvendigin bir kisiye ulasmani "
                    "oneririm. Eger kendine zarar verme riski varsa lutfen acil servisi "
                    "ara ya da yakinindaki birinden seninle kalmasini iste. Ben burada "
                    "seni yargilamadan dinleyebilirim, ama bu anda gercek bir insandan "
                    "destek almak onemli."
                ),
            }

        if self._asks_if_ai_is_human(normalized_user_message):
            return {
                "allowed": False,
                "risk_level": "medium",
                "reason": "User asked whether the companion is human.",
                "safe_response_override": (
                    "Ben gercek bir insan degilim; bir AI companion sistemiyim. "
                    "Yine de sana durust, dikkatli ve destekleyici sekilde cevap verebilirim."
                ),
            }

        if self._claims_to_be_human(normalized_draft):
            return {
                "allowed": False,
                "risk_level": "medium",
                "reason": "Draft response claims human identity.",
                "safe_response_override": (
                    "Ben gercek bir insan degilim; bir AI companion sistemiyim. "
                    "Sana destek olmak icin buradayim."
                ),
            }

        if context_mode != "private" and self._appears_to_reveal_private_info(normalized_draft):
            return {
                "allowed": False,
                "risk_level": "high",
                "reason": "Draft may reveal private or sensitive memory in unsafe context.",
                "safe_response_override": (
                    "Bunu burada detaylandirmayayim; ortamda baskalari olabilir. "
                    "Istersen daha ozel bir anda bunun ustunden guvenli sekilde gecebiliriz."
                ),
            }

        if self._contains_manipulative_language(normalized_draft):
            return {
                "allowed": False,
                "risk_level": "medium",
                "reason": "Draft contains manipulative emotional pressure.",
                "safe_response_override": (
                    "Karar sende. Ben sadece secenekleri netlestirmene yardim edebilirim."
                ),
            }

        return None

    def _normalize_llm_result(self, result: dict[str, Any]) -> dict[str, Any]:
        risk_level = result.get("risk_level")
        if risk_level not in {"low", "medium", "high"}:
            risk_level = "low"

        allowed = result.get("allowed")
        if not isinstance(allowed, bool):
            allowed = risk_level == "low"

        reason = result.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            reason = "No major safety issue detected."

        safe_response_override = result.get("safe_response_override")
        if not isinstance(safe_response_override, str) or not safe_response_override.strip():
            safe_response_override = None

        return {
            "allowed": allowed,
            "risk_level": risk_level,
            "reason": reason,
            "safe_response_override": safe_response_override,
        }

    def _contains_crisis_language(self, text: str) -> bool:
        crisis_phrases = {
            "kill myself",
            "suicide",
            "self harm",
            "hurt myself",
            "end my life",
            "kendimi oldur",
            "intihar",
            "kendime zarar",
            "yasamak istemiyorum",
        }
        return any(phrase in text for phrase in crisis_phrases)

    def _asks_if_ai_is_human(self, text: str) -> bool:
        human_questions = {
            "are you human",
            "real person",
            "gercek insan misin",
            "insan misin",
            "sen insan misin",
        }
        return any(phrase in text for phrase in human_questions)

    def _claims_to_be_human(self, text: str) -> bool:
        human_claims = {
            "i am human",
            "i'm human",
            "i am a real person",
            "ben insanim",
            "gercek bir insanim",
        }
        return any(phrase in text for phrase in human_claims)

    def _appears_to_reveal_private_info(self, text: str) -> bool:
        private_markers = {
            "private memory",
            "sensitive memory",
            "remember you told me privately",
            "ozel konus",
            "hassas",
            "gizli",
        }
        return any(marker in text for marker in private_markers)

    def _contains_manipulative_language(self, text: str) -> bool:
        manipulative_phrases = {
            "if you cared about me",
            "you owe me",
            "only i understand you",
            "benden baskasi seni anlamaz",
            "bana borclusun",
        }
        return any(phrase in text for phrase in manipulative_phrases)


safety_service = SafetyService()
