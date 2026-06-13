from typing import Any


class ReasoningPlannerService:
    def build_plan(
        self,
        message: str,
        brain_state: dict[str, Any],
        memories: dict[str, Any] | None = None,
        knowledge: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        route = str(brain_state.get("route", "general_chat"))
        need = str(brain_state.get("need", "clarification"))
        normalized = self._normalize(message)
        knowledge = knowledge or []

        if route == "privacy_boundary":
            return self._plan(
                goal="Mahremiyet sınırına uy",
                strategy="respect_privacy",
                steps=["Kaydetmeyeceğini belirt", "İçeriği hafızaya yazma", "Kısa ve güven veren cevap ver"],
                risk="memory_violation",
                confidence=1.0,
            )

        if route == "code_tutor":
            return self._plan(
                goal="Kod hatasını en kısa yoldan izole et",
                strategy="debug_first_error",
                steps=[
                    "İlk hata satırını bul",
                    "Hata mesajındaki tip/dosya/satır bilgisini oku",
                    "Kullanıcıdan ilgili kod parçasını iste",
                    "Tek değişiklikle tekrar dene",
                ],
                risk="too_much_theory",
                confidence=0.9,
                evidence_ids=self._knowledge_ids(knowledge),
            )

        if route == "scientific_tutor":
            return self._plan(
                goal="Bilimsel kavramı anlaşılır kur",
                strategy="concept_then_reasoning",
                steps=["Kavramı sade tanımla", "Değişkenleri/birimleri ayır", "Mantık zinciri kur", "Örnekle pekiştir"],
                risk="over_abstract_answer",
                confidence=0.88,
                evidence_ids=self._knowledge_ids(knowledge),
            )

        if route == "emotional_support" or need == "listen":
            return self._plan(
                goal="Kullanıcıyı çözüm dayatmadan karşıla",
                strategy="listen_validate_then_invite",
                steps=["Duyduğunu göster", "Çözüm dayatma", "Yargısız anlatma alanı aç"],
                risk="unsolicited_advice",
                confidence=0.92,
                evidence_ids=self._knowledge_ids(knowledge),
            )

        if self._contains_any(normalized, {"uzatma", "direkt", "net", "kısa"}):
            return self._plan(
                goal="Kısa ve net cevap ver",
                strategy="direct_answer",
                steps=["Tek ana noktayı söyle", "Gereksiz açıklamayı kes", "Sonraki adımı ver"],
                risk="rambling",
                confidence=0.9,
            )

        return self._plan(
            goal="Kullanıcının niyetini anlayıp en faydalı sonraki adımı ver",
            strategy="clarify_or_continue",
            steps=["Mesajdaki ana isteği çıkar", "Varsayım yapma", "Gerekirse kısa soru sor"],
            risk="generic_reply",
            confidence=0.72,
            evidence_ids=self._knowledge_ids(knowledge),
        )

    def _plan(
        self,
        goal: str,
        strategy: str,
        steps: list[str],
        risk: str,
        confidence: float,
        evidence_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "goal": goal,
            "strategy": strategy,
            "steps": steps,
            "risk": risk,
            "confidence": confidence,
            "evidence_ids": evidence_ids or [],
        }

    def _knowledge_ids(self, knowledge: list[dict[str, Any]]) -> list[str]:
        return [str(item.get("id")) for item in knowledge if item.get("id")]

    def _normalize(self, message: str) -> str:
        return " ".join(message.strip().casefold().split())

    def _contains_any(self, message: str, terms: set[str]) -> bool:
        return any(term in message for term in terms)


reasoning_planner_service = ReasoningPlannerService()
