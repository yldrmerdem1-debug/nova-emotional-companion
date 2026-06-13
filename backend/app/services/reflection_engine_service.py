from typing import Any


class ReflectionEngineService:
    PHILOSOPHY_TERMS = {"felsefe", "anlam", "bilinç", "bilinc", "varoluş", "varolus", "etik", "özgür irade", "ozgur irade"}
    DEEP_TERMS = {"derin düşün", "derin dusun", "muhakeme", "neden", "mantık", "mantik", "analiz et"}

    def reflect(
        self,
        message: str,
        brain_state: dict[str, Any],
        memory_context: dict[str, Any],
        emotional_context: dict[str, Any],
        knowledge_context: list[dict[str, Any]],
        reasoning_plan: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = self._normalize(message)
        route = str(brain_state.get("route", "general_chat"))
        emotional_summary = emotional_context.get("emotional_summary", {}) if isinstance(emotional_context, dict) else {}

        layers = {
            "surface_intent": self._surface_intent(route, reasoning_plan),
            "possible_hidden_need": self._hidden_need(brain_state, emotional_summary),
            "long_term_user_goal": self._long_term_goal(memory_context),
            "knowledge_gap": self._knowledge_gap(message, knowledge_context),
            "risk_check": self._risk_check(brain_state),
            "best_next_move": self._best_next_move(route, emotional_summary, reasoning_plan),
        }

        reflection_type = "philosophical" if self._contains_any(normalized, self.PHILOSOPHY_TERMS) else "practical"
        if self._contains_any(normalized, self.DEEP_TERMS):
            reflection_type = "deep_reasoning"

        return {
            "reflection_type": reflection_type,
            "depth": self._depth(reflection_type, route),
            "layers": layers,
            "philosophical_frame": self._philosophical_frame(normalized, reflection_type),
            "should_expand_answer": reflection_type in {"philosophical", "deep_reasoning"},
        }

    def _surface_intent(self, route: str, reasoning_plan: dict[str, Any]) -> str:
        goal = reasoning_plan.get("goal")
        if isinstance(goal, str) and goal:
            return goal
        return {
            "code_tutor": "Kod problemini çözmek",
            "scientific_tutor": "Bilimsel açıklama almak",
            "emotional_support": "Duyulmak ve sakinleşmek",
            "privacy_boundary": "Mahremiyeti korumak",
        }.get(route, "Yardım almak")

    def _hidden_need(self, brain_state: dict[str, Any], emotional_summary: dict[str, Any]) -> str:
        if brain_state.get("need") == "listen":
            return "Çözümden önce güvenli bir alan isteği"
        dominant_mood = emotional_summary.get("dominant_mood")
        if dominant_mood in {"low", "sad", "frustrated"}:
            return "Cevabın yanında duygusal regülasyon ihtiyacı"
        if brain_state.get("need") == "direct_solution":
            return "Kontrolü hızlı geri kazanma ihtiyacı"
        return "Netlik ve ilerleme ihtiyacı"

    def _long_term_goal(self, memory_context: dict[str, Any]) -> str:
        profile = memory_context.get("profile_summary", {}) if isinstance(memory_context, dict) else {}
        projects = profile.get("project_context", []) if isinstance(profile, dict) else []
        if projects:
            return "Kullanıcının aktif robot/AI projesini büyütmek"
        learning = profile.get("learning_profile", []) if isinstance(profile, dict) else []
        if learning:
            return "Öğrendiği konularda kalıcı ilerleme sağlamak"
        return "Kullanıcıyı konuşarak daha iyi tanımak"

    def _knowledge_gap(self, message: str, knowledge_context: list[dict[str, Any]]) -> str:
        if knowledge_context:
            return "Lokal bilgi bulundu"
        if "?" in message:
            return "Bu soru için lokal bilgi bankası genişletilebilir"
        return "Bilgi gereksinimi düşük"

    def _risk_check(self, brain_state: dict[str, Any]) -> str:
        meta = brain_state.get("brain_meta", {})
        if isinstance(meta, dict) and meta.get("risk_flags"):
            return ", ".join(str(flag) for flag in meta.get("risk_flags", []))
        if not brain_state.get("memory_allowed", True):
            return "Hafızaya yazma riski"
        return "Belirgin risk yok"

    def _best_next_move(
        self,
        route: str,
        emotional_summary: dict[str, Any],
        reasoning_plan: dict[str, Any],
    ) -> str:
        if route == "emotional_support":
            return "Önce dinle, sonra izin alarak çözüm öner"
        if route in {"code_tutor", "scientific_tutor"}:
            return "Kavramı küçük parçalara böl ve örnekle ilerle"
        if emotional_summary.get("support_preference") == "listen_first":
            return "Kısa, sıcak ve düşük baskılı soru sor"
        steps = reasoning_plan.get("steps", [])
        if steps:
            return str(steps[0])
        return "Kısa netleştirme sorusu sor"

    def _philosophical_frame(self, normalized: str, reflection_type: str) -> dict[str, Any] | None:
        if reflection_type not in {"philosophical", "deep_reasoning"}:
            return None
        return {
            "core_question": "Burada sadece cevap değil, anlam ve amaç da sorgulanıyor.",
            "angles": ["pratik sonuç", "duygusal gerçeklik", "etik sınır", "uzun vadeli hedef"],
            "method": "Önce varsayımları ayır, sonra çelişki ve sonuçları tart.",
        }

    def _depth(self, reflection_type: str, route: str) -> int:
        if reflection_type == "philosophical":
            return 5
        if reflection_type == "deep_reasoning":
            return 4
        if route in {"code_tutor", "scientific_tutor"}:
            return 3
        return 2

    def _contains_any(self, text: str, terms: set[str]) -> bool:
        return any(term in text for term in terms)

    def _normalize(self, text: str) -> str:
        return " ".join(text.strip().casefold().split())


reflection_engine_service = ReflectionEngineService()
