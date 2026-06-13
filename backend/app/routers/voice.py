from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

from app.services.voice_service import voice_service

router = APIRouter(prefix="/voice", tags=["voice"])


class SynthesizeRequest(BaseModel):
    text: str
    voice_tone: str = "calm"


class SpeakRequest(BaseModel):
    text: str
    voice: str = "default"


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)) -> dict[str, str]:
    return {
        "text": voice_service.transcribe_audio(file),
        "language": "tr",
    }


@router.post("/speak")
def speak(request: SpeakRequest) -> dict[str, str]:
    audio = voice_service.text_to_speech(request.text, request.voice)
    return {
        "audio_url": "",
        "audio_base64": voice_service.audio_base64(audio),
        "message": (
            "TTS placeholder: no external provider is configured."
            if not audio
            else ""
        ),
    }


@router.post("/synthesize")
def synthesize_speech(request: SynthesizeRequest) -> dict[str, object]:
    voice_params = voice_service.choose_voice_params({"voice_tone": request.voice_tone})
    audio = voice_service.synthesize_speech(request.text, request.voice_tone)
    return {
        "status": "placeholder" if not audio else "ok",
        "message": (
            "Speech synthesis placeholder: no external provider is configured."
            if not audio
            else ""
        ),
        "audio_base64": voice_service.audio_base64(audio),
        "voice_params": voice_params,
    }
