from typing import Any


class VerifierService:
    def verify_training_record(self, record: dict[str, Any]) -> dict[str, Any]:
        problem = record.get("problem", {})
        solution = record.get("solution", {})
        check = record.get("check", {})
        concepts = problem.get("concepts", []) if isinstance(problem, dict) else []
        explanation = str(solution.get("explanation", "")) if isinstance(solution, dict) else ""

        exact_match = bool(check.get("passed")) if isinstance(check, dict) else False
        concept_coverage = self._concept_coverage(concepts, explanation)
        explanation_quality = self._explanation_quality(explanation)
        confidence = self._confidence(exact_match, concept_coverage, explanation_quality)

        return {
            "verified": exact_match and (confidence >= 0.7 or explanation_quality >= 0.6),
            "exact_match": exact_match,
            "concept_coverage": concept_coverage,
            "explanation_quality": explanation_quality,
            "confidence": confidence,
            "issues": self._issues(exact_match, concept_coverage, explanation_quality),
        }

    def verify_reply(self, reply: str, brain_state: dict[str, Any]) -> dict[str, Any]:
        issues = []
        if brain_state.get("route") == "privacy_boundary" and any(term in reply.casefold() for term in ("kayded", "hatırlayacağım")):
            issues.append("privacy_reply_conflict")
        if len(reply.strip()) < 5:
            issues.append("too_short")
        return {
            "verified": not issues,
            "issues": issues,
            "confidence": 0.92 if not issues else 0.45,
        }

    def _concept_coverage(self, concepts: Any, explanation: str) -> float:
        if not isinstance(concepts, list) or not concepts:
            return 0.75
        normalized = explanation.casefold()
        matched = 0
        for concept in concepts:
            words = self._concept_words(str(concept))
            if any(word in normalized for word in words):
                matched += 1
        return round(matched / len(concepts), 3)

    def _concept_words(self, concept: str) -> list[str]:
        normalized = concept.replace("_", " ").casefold()
        aliases = {
            "binary search": ["binary", "search", "mid", "ikili", "arama"],
            "dynamic programming": ["dynamic", "programming", "dp", "alt", "problem", "state"],
            "vector": ["vector", "vektör", "eleman"],
            "loop": ["loop", "döngü"],
            "sum": ["sum", "toplam", "toplar"],
            "pointer": ["pointer", "adres"],
            "dereference": ["dereference", "*p", "değer"],
            "alias": ["alias", "başka", "adı", "adres"],
            "reference": ["reference", "referans"],
            "linear equation": ["denklem", "x=", "2x"],
            "quadratic": ["ikinci", "derece", "kök", "delta"],
            "series": ["seri", "toplam", "n(n+1)/2"],
            "induction": ["tümevarım", "formül", "n(n+1)/2"],
            "derivative": ["türev", "f'"],
            "function": ["fonksiyon", "f(", "f'"],
            "substitution": ["yerine", "koy", "f(", "="],
            "strings": ["string", "metin", "kelime", "karakter", "length"],
            "methods": ["method", "metod", "length", "çağrı", "karakter"],
            "stack": ["stack", "lifo", "son"],
            "queue": ["queue", "fifo", "ilk"],
        }
        words = normalized.split()
        for key, values in aliases.items():
            if key == normalized or key in normalized:
                words.extend(values)
        return words

    def _explanation_quality(self, explanation: str) -> float:
        if not explanation.strip():
            return 0.0
        score = 0.45
        if len(explanation.split()) >= 6:
            score += 0.2
        if any(marker in explanation for marker in ("=", "çünkü", "ise", "olur", "Bu yüzden", "bu yüzden")):
            score += 0.2
        if len(explanation) >= 80:
            score += 0.1
        return round(min(1.0, score), 3)

    def _confidence(self, exact_match: bool, concept_coverage: float, explanation_quality: float) -> float:
        score = (0.5 if exact_match else 0.0) + concept_coverage * 0.25 + explanation_quality * 0.25
        return round(min(1.0, score), 3)

    def _issues(self, exact_match: bool, concept_coverage: float, explanation_quality: float) -> list[str]:
        issues = []
        if not exact_match:
            issues.append("wrong_answer")
        if not exact_match and concept_coverage < 0.35:
            issues.append("low_concept_coverage")
        if explanation_quality < 0.55:
            issues.append("weak_explanation")
        return issues


verifier_service = VerifierService()
