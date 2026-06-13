import base64
from typing import Any


class VoiceService:
    def transcribe_audio(self, file: Any) -> str:
        # Future integration point for Whisper/OpenAI/local STT providers.
        filename = getattr(file, "filename", None) or "audio"
        return f"[Voice transcription placeholder: received {filename}, but no STT provider is configured.]"

    def text_to_speech(self, text: str, voice: str = "default") -> bytes:
        # Future integration point for OpenAI TTS/local TTS providers.
        return b""

    def audio_base64(self, audio: bytes) -> str:
        if not audio:
            return ""
        return base64.b64encode(audio).decode("ascii")

    def synthesize_speech(self, text: str, voice_tone: str) -> bytes:
        # Backward-compatible alias for the previous endpoint contract.
        return self.text_to_speech(text, voice_tone)

    def choose_voice_params(self, robot_state: dict[str, Any]) -> dict[str, Any]:
        # Keep voice selection separate from TTS provider details.
        return {
            "voice_tone": robot_state.get("voice_tone", "calm"),
            "emotion": robot_state.get("emotion", "neutral"),
            "speaking_rate": "normal",
            "pitch": "neutral",
        }


voice_service = VoiceService()
