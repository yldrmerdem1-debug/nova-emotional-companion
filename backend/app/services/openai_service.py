import json
from typing import Any

from openai import OpenAI, OpenAIError

from app.core.config import settings


class OpenAIService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    def generate_chat_response(self, system_prompt: str, user_prompt: str) -> str:
        if self.client is None:
            return "AI service is not configured yet."

        try:
            response = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content or ""
        except OpenAIError:
            return "I am having trouble connecting to the AI service right now."

    def generate_json_response(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if self.client is None:
            return {"error": "openai_not_configured", "data": {}}

        json_system_prompt = (
            f"{system_prompt}\n\n"
            "Return valid JSON only. Do not include markdown, comments, or extra text."
        )

        try:
            response = self.client.chat.completions.create(
                model=settings.openai_model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": json_system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
            return {"error": "invalid_json_shape", "data": {}}
        except json.JSONDecodeError:
            return {"error": "invalid_json", "data": {}}
        except OpenAIError:
            return {"error": "openai_error", "data": {}}

    def embed_text(self, text: str) -> list[float]:
        if self.client is None:
            return []

        try:
            response = self.client.embeddings.create(
                model=settings.embedding_model,
                input=text,
            )
            return response.data[0].embedding
        except OpenAIError:
            return []


openai_service = OpenAIService()
