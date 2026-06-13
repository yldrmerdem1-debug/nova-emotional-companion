import json
from pathlib import Path
from typing import Any

from app.ml.inference.brain_meta_controller import brain_meta_controller

try:
    import joblib
except ImportError:  # pragma: no cover - keeps the app bootable without ML deps.
    joblib = None


MODEL_VERSION = "turkish_v3"

PRIVACY_TERMS = {
    "hafızaya alma",
    "kaydetme",
    "kalıcı tutma",
    "kalıcı kaydetme",
    "unut",
    "kayıt yok",
    "hatırlama",
}
SCIENTIFIC_TERMS = {
    "bilimsel",
    "fizik",
    "matematik",
    "formül",
    "kanıt",
    "akademik",
    "hipotez",
}
CODE_TERMS = {
    "C++",
    "c++",
    "python",
    "kod",
    "hata",
    "debug",
    "CLion",
    "pointer",
    "array",
    "compile",
    "derleme",
}
STYLE_TERMS = {
    "casual",
    "resmi olma",
    "sade konuş",
    "argo",
    "kanka deme",
    "kral de",
    "şakalı konuş",
}
EMOTIONAL_SUPPORT_TERMS = {
    "kötüyüm",
    "kotuyum",
    "moralim bozuk",
    "canım sıkkın",
    "canim sikkin",
    "çözüm istemiyorum",
    "cozum istemiyorum",
    "sadece dinle",
    "dinle",
}

ROBOT_MODEL_KEYS = {
    "emotion": "robot_action_emotion_v3",
    "face": "robot_action_face_v3",
    "eyes": "robot_action_eyes_v3",
    "mouth": "robot_action_mouth_v3",
    "voice_tone": "robot_action_voice_tone_v3",
    "body_action": "robot_action_body_action_v3",
    "head_motion": "robot_action_head_motion_v3",
    "eye_contact": "robot_action_eye_contact_v3",
    "movement_intensity": "robot_action_movement_intensity_v3",
    "should_speak": "robot_action_should_speak_v3",
}


class TurkishBrainRouter:
    def __init__(self, models_dir: Path | None = None) -> None:
        self.models_dir = models_dir or Path(__file__).resolve().parents[1] / "models"
        self.models: dict[str, Any] = {}
        self.load_models()

    def load_models(self) -> None:
        self.models = {}
        if joblib is None or not self.models_dir.exists():
            return

        for model_path in sorted(self.models_dir.glob("*.joblib")):
            try:
                self.models[model_path.stem] = joblib.load(model_path)
            except Exception:
                continue

    def predict_route(self, message: str) -> str:
        hard_rule = self._hard_rule_route(message)
        if hard_rule is not None:
            return hard_rule

        return self._predict_label("intent_router_v1", message, "general_chat")

    def predict_brain_state(self, message: str, context: dict | None = None) -> dict:
        route = self.predict_route(message)
        context = context or {}
        memory_allowed = True

        if route == "privacy_boundary":
            emotion = "neutral"
            need = "do_not_store"
            tone = "plain_direct"
            style = "plain_direct"
            memory_allowed = False
        elif route == "scientific_tutor":
            emotion = "focused"
            need = "explain_scientifically"
            tone = "scientific_clear"
            style = "scientific_clear"
        elif route == "code_tutor":
            emotion = "focused"
            need = "debug_or_explain"
            tone = "calm_confident"
            style = "student_friendly_direct"
        elif route == "style_adaptation":
            emotion = "focused"
            need = "style_adaptation"
            tone = self._predict_label("tone_classifier_v3", message, "calm_confident")
            style = self._predict_label("style_adapter_v2", message, "student_friendly_direct")
        elif route == "emotional_support":
            emotion = "sad"
            need = "listen"
            tone = "soft"
            style = "casual_supportive"
        else:
            emotion = self._predict_label("emotion_classifier_v3", message, "neutral")
            need = self._predict_label("need_classifier_v3", message, "clarification")
            tone = self._predict_label("tone_classifier_v3", message, "calm")
            style = self._predict_label("style_adapter_v2", message, tone)

        if memory_allowed:
            memory_allowed = self._predict_memory_allowed(message, context)

        if route == "privacy_boundary":
            robot_state = {
                **self._default_robot_state(emotion, tone),
                "face": "serious",
                "voice_tone": tone,
            }
        else:
            robot_state = self.predict_robot_state(message, emotion, need, tone)
        raw_state = {
            "route": route,
            "emotion": emotion,
            "need": need,
            "tone": tone,
            "style": style,
            "memory_allowed": memory_allowed,
            "robot_state": robot_state,
            "model_version": MODEL_VERSION,
            "loaded_models": self.loaded_models,
        }
        return brain_meta_controller.refine(message, raw_state, context)

    def predict_robot_state(self, message: str, emotion: str, need: str, tone: str) -> dict:
        default_state = self._default_robot_state(emotion, tone)
        features = {
            "message": message,
            "emotion": emotion,
            "need": need,
            "tone": tone,
        }

        combined_state = self._predict_structured("robot_action_selector_v3", features)
        if combined_state:
            return self._normalize_robot_state({**default_state, **combined_state})

        robot_state = default_state.copy()
        feature_text = self._feature_text(message, emotion, need, tone)
        for field, model_key in ROBOT_MODEL_KEYS.items():
            predicted = self._predict_raw(
                model_key,
                [[feature_text], [[message, emotion, need, tone]], feature_text],
            )
            if predicted is None:
                continue
            if field == "should_speak":
                robot_state[field] = self._coerce_bool(predicted, robot_state[field])
            elif isinstance(predicted, str) and predicted.strip():
                robot_state[field] = predicted.strip()

        return self._normalize_robot_state(robot_state)

    @property
    def loaded_models(self) -> list[str]:
        return sorted(self.models.keys())

    def _hard_rule_route(self, message: str) -> str | None:
        if self._contains_any(message, PRIVACY_TERMS):
            return "privacy_boundary"
        if self._contains_any(message, SCIENTIFIC_TERMS):
            return "scientific_tutor"
        if self._contains_any(message, CODE_TERMS):
            return "code_tutor"
        if self._contains_any(message, STYLE_TERMS):
            return "style_adaptation"
        if self._contains_any(message, EMOTIONAL_SUPPORT_TERMS):
            return "emotional_support"
        return None

    def _predict_label(self, model_key: str, message: str, default: str) -> str:
        predicted = self._predict_raw(model_key, [[message], message])
        if isinstance(predicted, str) and predicted.strip():
            return predicted.strip()
        return default

    def _predict_memory_allowed(self, message: str, context: dict) -> bool:
        features = {
            "message": message,
            "context": context,
        }
        memory_score = self._predict_raw(
            "memory_scorer_v2",
            [[features], [message], message],
        )
        allowed = self._interpret_memory_value(memory_score)
        if allowed is not None:
            return allowed

        privacy_label = self._predict_label("privacy_classifier_v3", message, "allow")
        return privacy_label.casefold() not in {
            "deny",
            "disallow",
            "blocked",
            "private",
            "sensitive",
            "do_not_store",
            "no_store",
            "false",
        }

    def _predict_structured(self, model_key: str, features: dict[str, Any]) -> dict[str, Any]:
        feature_text = self._feature_text(
            str(features.get("message", "")),
            str(features.get("emotion", "")),
            str(features.get("need", "")),
            str(features.get("tone", "")),
        )
        predicted = self._predict_raw(
            model_key,
            [[features], features, [feature_text], feature_text],
        )
        return self._coerce_dict(predicted)

    def _predict_raw(self, model_key: str, candidates: list[Any]) -> Any:
        model = self.models.get(model_key)
        if model is None:
            return None

        for candidate in candidates:
            try:
                if hasattr(model, "predict"):
                    return self._first_prediction(model.predict(candidate))
                if callable(model):
                    return self._first_prediction(model(candidate))
            except Exception:
                continue
        return None

    def _first_prediction(self, prediction: Any) -> Any:
        if isinstance(prediction, dict):
            return prediction
        if isinstance(prediction, str) or not hasattr(prediction, "__iter__"):
            return prediction

        try:
            first_item = next(iter(prediction))
        except StopIteration:
            return None
        except TypeError:
            return prediction
        return first_item

    def _coerce_dict(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return {}
            if isinstance(parsed, dict):
                return parsed
        return {}

    def _interpret_memory_value(self, value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, dict):
            for key in ("memory_allowed", "allowed", "should_store"):
                if key in value:
                    return self._coerce_bool(value[key], True)
            if "score" in value:
                return self._numeric_memory_allowed(value["score"])
        if isinstance(value, (int, float)):
            return self._numeric_memory_allowed(value)
        if isinstance(value, str):
            normalized = value.strip().casefold()
            if normalized in {"allow", "allowed", "store", "true", "yes", "1"}:
                return True
            if normalized in {"deny", "disallow", "blocked", "do_not_store", "no_store", "false", "0"}:
                return False
            try:
                return self._numeric_memory_allowed(float(normalized))
            except ValueError:
                return None
        return None

    def _numeric_memory_allowed(self, value: Any) -> bool | None:
        try:
            return float(value) >= 0.5
        except (TypeError, ValueError):
            return None

    def _default_robot_state(self, emotion: str, tone: str) -> dict[str, Any]:
        normalized_emotion = emotion.casefold()
        if normalized_emotion in {"sad", "anxious", "concerned", "tired"}:
            face = "soft_concerned"
        elif normalized_emotion in {"angry", "serious"}:
            face = "serious"
        else:
            face = "focused"

        return {
            "emotion": emotion,
            "face": face,
            "eyes": "center",
            "mouth": "neutral",
            "voice_tone": tone,
            "body_action": "look_at_user",
            "head_motion": "none",
            "eye_contact": "medium",
            "movement_intensity": "low",
            "should_speak": True,
        }

    def _normalize_robot_state(self, state: dict[str, Any]) -> dict[str, Any]:
        default_state = self._default_robot_state(
            str(state.get("emotion") or "neutral"),
            str(state.get("voice_tone") or "calm"),
        )
        normalized = {}
        for key, default_value in default_state.items():
            value = state.get(key, default_value)
            if key == "should_speak":
                normalized[key] = self._coerce_bool(value, bool(default_value))
            elif isinstance(value, str) and value.strip():
                normalized[key] = value.strip()
            else:
                normalized[key] = default_value
        return normalized

    def _coerce_bool(self, value: Any, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().casefold()
            if normalized in {"true", "yes", "1", "speak", "konuş"}:
                return True
            if normalized in {"false", "no", "0", "silent", "sus"}:
                return False
        return default

    def _feature_text(self, message: str, emotion: str, need: str, tone: str) -> str:
        return f"message={message}\nemotion={emotion}\nneed={need}\ntone={tone}"

    def _contains_any(self, message: str, terms: set[str]) -> bool:
        normalized_message = message.casefold()
        return any(term.casefold() in normalized_message for term in terms)


turkish_brain_router = TurkishBrainRouter()
