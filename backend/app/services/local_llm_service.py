import json
import urllib.error
import urllib.request
from typing import Any

from app.core.config import settings


class LocalLLMService:
    def generate_reply(
        self,
        message: str,
        brain_state: dict[str, Any],
        context: dict[str, Any],
        fallback_reply: str,
    ) -> dict[str, Any]:
        provider = settings.local_llm_provider.strip().casefold()
        if provider == "ollama":
            return self._generate_with_ollama(message, brain_state, context, fallback_reply)
        if provider:
            return {
                "reply": None,
                "meta": {
                    "enabled": True,
                    "provider": provider,
                    "status": "unsupported_provider",
                },
            }
        return {
            "reply": None,
            "meta": {
                "enabled": False,
                "provider": None,
                "status": "not_configured",
            },
        }

    def health(self) -> dict[str, Any]:
        provider = settings.local_llm_provider.strip().casefold()
        if provider != "ollama":
            return {"enabled": bool(provider), "provider": provider or None, "status": "not_configured"}
        try:
            request = urllib.request.Request(f"{settings.local_llm_base_url.rstrip('/')}/api/tags", method="GET")
            with urllib.request.urlopen(request, timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            return {"enabled": True, "provider": "ollama", "status": "unreachable", "error": str(exc)}
        return {"enabled": True, "provider": "ollama", "status": "ok", "models": payload.get("models", [])}

    def _generate_with_ollama(
        self,
        message: str,
        brain_state: dict[str, Any],
        context: dict[str, Any],
        fallback_reply: str,
    ) -> dict[str, Any]:
        if brain_state.get("route") == "privacy_boundary":
            return {
                "reply": None,
                "meta": {
                    "enabled": True,
                    "provider": "ollama",
                    "status": "skipped_privacy_boundary",
                },
            }

        prompt = self._build_prompt(message, brain_state, context, fallback_reply)
        payload = {
            "model": settings.local_llm_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.35,
                "num_predict": settings.local_llm_num_predict,
            },
        }
        try:
            request = urllib.request.Request(
                f"{settings.local_llm_base_url.rstrip('/')}/api/generate",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=settings.local_llm_timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            return {
                "reply": None,
                "meta": {
                    "enabled": True,
                    "provider": "ollama",
                    "model": settings.local_llm_model,
                    "status": "failed",
                    "error": str(exc),
                },
            }

        reply = result.get("response")
        if isinstance(reply, str) and reply.strip():
            return {
                "reply": reply.strip(),
                "meta": {
                    "enabled": True,
                    "provider": "ollama",
                    "model": settings.local_llm_model,
                    "status": "ok",
                },
            }
        return {
            "reply": None,
            "meta": {
                "enabled": True,
                "provider": "ollama",
                "model": settings.local_llm_model,
                "status": "empty_response",
            },
        }

    def _build_prompt(
        self,
        message: str,
        brain_state: dict[str, Any],
        context: dict[str, Any],
        fallback_reply: str,
    ) -> str:
        safe_context = {
            "brain_state": {
                "route": brain_state.get("route"),
                "emotion": brain_state.get("emotion"),
                "need": brain_state.get("need"),
                "tone": brain_state.get("tone"),
                "style": brain_state.get("style"),
            },
            "knowledge": context.get("knowledge", [])[:4] if isinstance(context.get("knowledge"), list) else [],
            "reasoning_plan": context.get("reasoning_plan"),
            "reflection": context.get("reflection"),
            "emotional_memory": context.get("emotional_memory"),
            "fallback_reply": fallback_reply,
        }
        return (
            "Sen tamamen lokal çalışan Türkçe bir robot zihinsin. "
            "Kullanıcıya doğal, bilgili, sıcak ve kısa cevap ver. "
            "En fazla 3 kısa cümle kullan; kod gerekiyorsa minicik tek örnek ver. "
            "Verilen lokal bilgi ve hafızayı kullan; bilmediğin şeyi uydurma. "
            "Privacy veya hafıza kurallarını asla bozma.\n\n"
            f"Kullanıcı mesajı: {message}\n\n"
            f"Yerel bağlam JSON:\n{json.dumps(safe_context, ensure_ascii=False, indent=2)}\n\n"
            "Cevap:"
        )


local_llm_service = LocalLLMService()
