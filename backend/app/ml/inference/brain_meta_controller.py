from typing import Any


class BrainMetaController:
    """Hakem beyin: model çıktılarını risk, çakışma ve kullanıcı profiline göre düzeltir."""

    PRIVACY_TERMS = {
        "hafızaya alma",
        "hafizaya alma",
        "kaydetme",
        "kalıcı tutma",
        "kalici tutma",
        "kalıcı kaydetme",
        "kalici kaydetme",
        "kayıt yok",
        "kayit yok",
        "hatırlama",
        "hatirlama",
        "unut",
    }
    CODE_TERMS = {"c++", "cpp", "python", "kod", "hata", "debug", "compile", "derleme", "pointer", "array"}
    SCIENCE_TERMS = {"bilimsel", "fizik", "matematik", "formül", "formul", "kanıt", "kanit", "hipotez"}
    EMOTIONAL_TERMS = {
        "kötüyüm",
        "kotuyum",
        "moralim bozuk",
        "canım sıkkın",
        "canim sikkin",
        "sadece dinle",
        "çözüm istemiyorum",
        "cozum istemiyorum",
    }
    STYLE_TERMS = {"resmi olma", "casual", "sade konuş", "sade konus", "kanka deme", "kral de", "şakalı konuş"}
    ANGER_TERMS = {"sinir oldum", "sinirliyim", "bıktım", "biktim", "deliricem", "patladım", "patladim"}
    DIRECT_TERMS = {"uzatma", "direkt", "net konuş", "net konus", "kısa kes", "kisa kes"}

    def refine(
        self,
        message: str,
        raw_state: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = context or {}
        normalized = self._normalize(message)
        refined = dict(raw_state)
        route_scores = self._route_scores(normalized, raw_state)
        decisions: list[str] = []
        risk_flags: list[str] = []

        if self._contains_any(normalized, self.PRIVACY_TERMS):
            refined.update(
                {
                    "route": "privacy_boundary",
                    "emotion": "neutral",
                    "need": "do_not_store",
                    "tone": "plain_direct",
                    "style": "plain_direct",
                    "memory_allowed": False,
                }
            )
            decisions.append("privacy_terms_override_all")
            risk_flags.append("memory_violation")
        elif self._contains_any(normalized, self.EMOTIONAL_TERMS) and self._contains_any(normalized, {"sadece dinle", "çözüm istemiyorum", "cozum istemiyorum"}):
            refined.update(
                {
                    "route": "emotional_support",
                    "emotion": "sad",
                    "need": "listen",
                    "tone": "soft",
                    "style": "casual_supportive",
                }
            )
            decisions.append("explicit_listening_request_overrides_solution")
            risk_flags.append("unsolicited_advice")
        elif self._contains_any(normalized, self.CODE_TERMS):
            refined.update(
                {
                    "route": "code_tutor",
                    "need": "debug_or_explain",
                    "tone": "calm_confident",
                    "style": "student_friendly_direct",
                }
            )
            if self._contains_any(normalized, self.ANGER_TERMS | self.EMOTIONAL_TERMS):
                refined["emotion"] = "frustrated"
                refined["tone"] = "calm_supportive"
                decisions.append("code_task_kept_but_tone_softened")
            else:
                refined["emotion"] = "focused"
                decisions.append("code_signal_route_lock")
        elif self._contains_any(normalized, self.SCIENCE_TERMS):
            refined.update(
                {
                    "route": "scientific_tutor",
                    "emotion": "focused",
                    "need": "explain_scientifically",
                    "tone": "scientific_clear",
                    "style": "scientific_clear",
                }
            )
            decisions.append("science_signal_route_lock")
        elif self._contains_any(normalized, self.STYLE_TERMS):
            refined.update({"route": "style_adaptation", "emotion": "focused", "need": "style_adaptation"})
            decisions.append("style_signal_route_lock")
        elif self._contains_any(normalized, self.DIRECT_TERMS):
            refined.update(
                {
                    "route": "general_chat",
                    "emotion": "focused",
                    "need": "direct_solution",
                    "tone": "plain_direct",
                    "style": "short_direct",
                }
            )
            decisions.append("direct_text_control")

        self._apply_personalization(refined, context, decisions)
        self._apply_risk_policy(refined, normalized, risk_flags, decisions)
        refined["robot_state"] = self._refine_robot_state(refined, raw_state.get("robot_state", {}))
        refined["brain_meta"] = self._meta_payload(raw_state, refined, route_scores, decisions, risk_flags)
        return refined

    def _route_scores(self, normalized: str, raw_state: dict[str, Any]) -> dict[str, float]:
        scores = {
            "privacy_boundary": 0.0,
            "code_tutor": 0.0,
            "scientific_tutor": 0.0,
            "emotional_support": 0.0,
            "style_adaptation": 0.0,
            "general_chat": 0.0,
        }
        raw_route = str(raw_state.get("route", "general_chat"))
        scores[raw_route] = max(scores.get(raw_route, 0.0), 0.62)
        if self._contains_any(normalized, self.PRIVACY_TERMS):
            scores["privacy_boundary"] = 0.99
        if self._contains_any(normalized, self.CODE_TERMS):
            scores["code_tutor"] = max(scores["code_tutor"], 0.94)
        if self._contains_any(normalized, self.SCIENCE_TERMS):
            scores["scientific_tutor"] = max(scores["scientific_tutor"], 0.94)
        if self._contains_any(normalized, self.EMOTIONAL_TERMS):
            scores["emotional_support"] = max(scores["emotional_support"], 0.91)
        if self._contains_any(normalized, self.STYLE_TERMS):
            scores["style_adaptation"] = max(scores["style_adaptation"], 0.9)
        if self._contains_any(normalized, self.DIRECT_TERMS):
            scores["general_chat"] = max(scores["general_chat"], 0.65)
        return {route: round(score, 3) for route, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)}

    def _apply_personalization(self, refined: dict[str, Any], context: dict[str, Any], decisions: list[str]) -> None:
        profile = context.get("profile_summary", {}) if isinstance(context, dict) else {}
        if not isinstance(profile, dict):
            return
        reply_style = profile.get("reply_style")
        if reply_style == "short_direct" and refined.get("route") != "scientific_tutor":
            refined["tone"] = "plain_direct"
            refined["style"] = "short_direct"
            decisions.append("profile_short_direct_style")
        if reply_style == "scientific_clear" and refined.get("route") == "scientific_tutor":
            refined["tone"] = "scientific_clear"
            refined["style"] = "scientific_clear"
            decisions.append("profile_scientific_style")
        avoid_address = profile.get("avoid_address") or []
        if avoid_address:
            refined["addressing_constraints"] = {"avoid": avoid_address}
            decisions.append("profile_address_boundary")

    def _apply_risk_policy(
        self,
        refined: dict[str, Any],
        normalized: str,
        risk_flags: list[str],
        decisions: list[str],
    ) -> None:
        if refined.get("route") == "privacy_boundary" or refined.get("need") == "do_not_store":
            refined["memory_allowed"] = False
            risk_flags.append("do_not_store_enforced")
            decisions.append("memory_disabled_by_policy")
        if self._contains_any(normalized, self.ANGER_TERMS):
            risk_flags.append("high_emotion")
            if refined.get("route") not in {"privacy_boundary", "emotional_support"}:
                refined["tone"] = "calm_supportive"
                decisions.append("anger_tone_deescalation")

    def _refine_robot_state(self, refined: dict[str, Any], robot_state: dict[str, Any]) -> dict[str, Any]:
        state = dict(robot_state) if isinstance(robot_state, dict) else {}
        route = refined.get("route")
        emotion = str(refined.get("emotion", "neutral"))
        tone = str(refined.get("tone", "calm"))
        state["emotion"] = emotion
        state["voice_tone"] = tone

        if route == "privacy_boundary":
            state.update({"face": "serious", "eyes": "center", "mouth": "neutral", "movement_intensity": "low"})
        elif route == "emotional_support":
            state.update({"face": "soft_concerned", "eyes": "soft", "mouth": "neutral", "movement_intensity": "low"})
        elif emotion in {"frustrated", "angry"}:
            state.update({"face": "serious", "eyes": "focused", "movement_intensity": "medium"})
        elif route in {"code_tutor", "scientific_tutor"}:
            state.update({"face": "focused", "eyes": "center", "movement_intensity": "low"})

        state.setdefault("body_action", "look_at_user")
        state.setdefault("head_motion", "none")
        state.setdefault("eye_contact", "medium")
        state.setdefault("should_speak", True)
        return state

    def _meta_payload(
        self,
        raw_state: dict[str, Any],
        refined: dict[str, Any],
        route_scores: dict[str, float],
        decisions: list[str],
        risk_flags: list[str],
    ) -> dict[str, Any]:
        top_scores = list(route_scores.items())[:2]
        gap = top_scores[0][1] - top_scores[1][1] if len(top_scores) > 1 else top_scores[0][1]
        confidence = max(0.5, min(0.99, top_scores[0][1] if top_scores else 0.72))
        return {
            "version": "brain_meta_v1",
            "raw_route": raw_state.get("route"),
            "final_route": refined.get("route"),
            "route_scores": route_scores,
            "confidence": round(confidence, 3),
            "confidence_gap": round(gap, 3),
            "risk_flags": sorted(set(risk_flags)),
            "decisions": decisions,
            "needs_clarification": confidence < 0.68 or gap < 0.12,
        }

    def _contains_any(self, text: str, terms: set[str]) -> bool:
        return any(term in text for term in terms)

    def _normalize(self, text: str) -> str:
        return " ".join(text.strip().casefold().split())


brain_meta_controller = BrainMetaController()
