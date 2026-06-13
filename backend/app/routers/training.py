import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.training_data_service import training_data_service

router = APIRouter(prefix="/training", tags=["training"])


class CorrectionRequest(BaseModel):
    corrected_target_json: dict[str, Any]
    notes: str | None = None


class ResponseFeedbackRequest(BaseModel):
    user_message: str
    brain_state: dict[str, Any]
    robot_reply: str
    rating: str
    ideal_reply: str | None = None
    notes: str | None = None
    response_meta: dict[str, Any] | None = None


@router.post("/response-feedback")
def record_response_feedback(request: ResponseFeedbackRequest) -> dict[str, Any]:
    if request.rating not in {"good", "bad"}:
        raise HTTPException(status_code=400, detail="rating must be 'good' or 'bad'.")
    if request.rating == "bad" and not (request.ideal_reply or "").strip():
        raise HTTPException(status_code=400, detail="ideal_reply is required for bad responses.")

    record = training_data_service.record_response_feedback(
        user_message=request.user_message,
        brain_state=request.brain_state,
        robot_reply=request.robot_reply,
        rating=request.rating,
        ideal_reply=request.ideal_reply,
        notes=request.notes,
        response_meta=request.response_meta,
    )
    return {
        "saved": True,
        "record": record,
    }


@router.get("/examples")
def get_training_examples(
    task_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    examples = training_data_service.list_examples(db, task_type=task_type, limit=limit)
    return [training_data_service.serialize_example(example) for example in examples]


@router.post("/examples/{example_id}/approve")
def approve_training_example(example_id: uuid.UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    example = training_data_service.approve_example(db, example_id)
    if example is None:
        raise HTTPException(status_code=404, detail="Training example not found.")
    return training_data_service.serialize_example(example)


@router.post("/examples/{example_id}/correct")
def correct_training_example(
    example_id: uuid.UUID,
    request: CorrectionRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    correction = training_data_service.correct_example(
        db=db,
        example_id=example_id,
        corrected_target_json=request.corrected_target_json,
        notes=request.notes,
    )
    if correction is None:
        raise HTTPException(status_code=404, detail="Training example not found.")
    return training_data_service.serialize_correction(correction)


@router.get("/export")
def export_training_examples(
    task_type: str | None = None,
    approved_only: bool = False,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    examples = training_data_service.export_examples(
        db,
        task_type=task_type,
        approved_only=approved_only,
    )
    return {
        "task_type": task_type,
        "approved_only": approved_only,
        "count": len(examples),
        "examples": examples,
    }
