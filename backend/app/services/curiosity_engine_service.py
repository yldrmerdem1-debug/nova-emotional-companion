from typing import Any


class CuriosityEngineService:
    def generate_question(
        self,
        message: str,
        brain_state: dict[str, Any],
        memory_context: dict[str, Any],
        emotional_context: dict[str, Any],
        learning_context: dict[str, Any],
    ) -> dict[str, Any]:
        if brain_state.get("route") == "privacy_boundary" or brain_state.get("need") == "do_not_store":
            return {"should_ask": False, "question": None, "reason": "privacy_boundary"}

        normalized = self._normalize(message)
        if self._is_micro_conversation(normalized):
            return {"should_ask": False, "question": None, "reason": "micro_conversation"}

        route = str(brain_state.get("route", "general_chat"))
        need = str(brain_state.get("need", "clarification"))
        support_mode = str(brain_state.get("support_mode", "listen"))
        emotional_summary = emotional_context.get("emotional_summary", {}) if isinstance(emotional_context, dict) else {}
        learning_summary = learning_context.get("learning_summary", {}) if isinstance(learning_context, dict) else {}
        profile = memory_context.get("profile_summary", {}) if isinstance(memory_context, dict) else {}

        if support_mode == "brief":
            return {"should_ask": False, "question": None, "reason": "brief_mode"}
        if support_mode == "think" and route not in {"code_tutor", "scientific_tutor"}:
            return {
                "should_ask": True,
                "question": "İstersen en çok yoran kısmı tek cümleyle yaz; oradan sakin sakin ilerleyelim.",
                "reason": "reflect_then_step_followup",
            }

        if route == "emotional_support" or need == "listen":
            return {
                "should_ask": True,
                "question": "İstersen sadece anlatmaya devam edebilirsin; ben çözüm dayatmadan dinlerim.",
                "reason": "emotional_followup",
            }

        support_preference = emotional_summary.get("support_preference")
        dominant_mood = emotional_summary.get("dominant_mood")
        if route == "emotional_support" and support_preference == "listen_first" and dominant_mood in {"low", "sad", "frustrated"}:
            return {
                "should_ask": True,
                "question": "Geçenlerde dinlenmek istediğin moddaydın; bugün de önce seni dinleyeyim mi?",
                "reason": "mood_timeline_followup",
            }

        learning_topics = profile.get("learning_profile", []) if isinstance(profile, dict) else []
        if support_mode == "think" and learning_topics and route in {"code_tutor", "scientific_tutor", "general_chat"}:
            last_topic = learning_topics[-1]
            topic = last_topic.get("key") if isinstance(last_topic, dict) else None
            if topic:
                return {
                    "should_ask": True,
                    "question": f"{topic} tarafında önceki takıldığın yeri devam ettirelim mi, yoksa bugünkü hedef başka mı?",
                    "reason": "learning_profile_followup",
                }

        open_questions = learning_summary.get("open_questions", []) if isinstance(learning_summary, dict) else []
        if open_questions:
            return {
                "should_ask": True,
                "question": "Bir açık soru yakaladım; bunu bilgi bankasına ekleyip sonra daha güçlü cevaplamamı ister misin?",
                "reason": "open_question_followup",
            }

        if route == "style_adaptation":
            return {
                "should_ask": True,
                "question": "Bu konuşma stilini kalıcı tercih olarak hatırlamamı ister misin?",
                "reason": "style_preference_confirmation",
            }

        return {"should_ask": False, "question": None, "reason": "no_high_value_question"}

    def _is_micro_conversation(self, normalized: str) -> bool:
        return self._contains_any(
            normalized,
            {
                "selam",
                "merhaba",
                "naber",
                "nasılsın",
                "nasilsin",
                "soru soracam",
                "soru soracağım",
                "soru sorucam",
                "bir soru soracağım",
                "bir şey soracağım",
                "bir sey soracagim",
            },
        ) or normalized in {"sa", "s.a", "s a"}

    def _contains_any(self, text: str, terms: set[str]) -> bool:
        return any(term in text for term in terms)

    def _normalize(self, text: str) -> str:
        return " ".join(text.strip().casefold().split())


curiosity_engine_service = CuriosityEngineService()
