from fastapi import APIRouter
from pydantic import BaseModel

from app.ml.inference.turkish_brain_router import turkish_brain_router

router = APIRouter(prefix="/debug", tags=["debug"])


class TurkishBrainDebugRequest(BaseModel):
    message: str
    context: dict | None = None


@router.post("/turkish-brain-state")
def debug_turkish_brain_state(request: TurkishBrainDebugRequest) -> dict:
    return turkish_brain_router.predict_brain_state(request.message, request.context)
