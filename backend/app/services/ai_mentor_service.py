from typing import Any

from app.services.openai_service import openai_service


class AIMentorService:
    def critique_training_record(self, record: dict[str, Any], verification: dict[str, Any]) -> dict[str, Any]:
        if getattr(openai_service, "client", None) is None:
            return self._heuristic_critique(record, verification)

        result = openai_service.generate_json_response(
            system_prompt=(
                "Sen bir yapay zeka eğitim mentorusun. "
                "Bir self-training kaydını değerlendir, kısa ve yapıcı geri bildirim ver. "
                "JSON dön: {\"score\":0.0,\"critique\":\"...\",\"next_drill\":\"...\"}"
            ),
            user_prompt=f"Training record: {record}\nVerification: {verification}",
        )
        score = result.get("score", verification.get("confidence", 0.6))
        return {
            "source": "api_mentor",
            "score": score if isinstance(score, (int, float)) else verification.get("confidence", 0.6),
            "critique": str(result.get("critique", "Kayıt değerlendirildi.")),
            "next_drill": str(result.get("next_drill", "Benzer bir problemi daha çöz.")),
        }

    def _heuristic_critique(self, record: dict[str, Any], verification: dict[str, Any]) -> dict[str, Any]:
        problem = record.get("problem", {})
        domain = record.get("domain", "general")
        if verification.get("verified"):
            critique = "Çözüm doğru ve eğitim kaydı kullanılabilir."
            next_drill = f"{domain} alanında aynı kavramı daha zor bir problemle pekiştir."
        else:
            issues = ", ".join(verification.get("issues", [])) or "belirsiz hata"
            critique = f"Çözümde geliştirme gerekiyor: {issues}."
            concepts = problem.get("concepts", []) if isinstance(problem, dict) else []
            next_drill = f"Önce şu kavramları tekrar et: {', '.join(str(item) for item in concepts[:3])}."
        return {
            "source": "heuristic_mentor",
            "score": verification.get("confidence", 0.5),
            "critique": critique,
            "next_drill": next_drill,
        }


ai_mentor_service = AIMentorService()
