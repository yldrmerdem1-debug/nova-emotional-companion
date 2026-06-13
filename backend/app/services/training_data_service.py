import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.models import HumanCorrection, TrainingExample


class TrainingDataService:
    def record_response_feedback(
        self,
        user_message: str,
        brain_state: dict[str, Any],
        robot_reply: str,
        rating: str,
        ideal_reply: str | None = None,
        notes: str | None = None,
        response_meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "task_type": "response_generation",
            "user_message": user_message,
            "brain_state": brain_state,
            "robot_reply": robot_reply,
            "rating": rating,
            "ideal_reply": ideal_reply,
            "notes": notes,
            "response_meta": response_meta or {},
            "source": "frontend_feedback",
        }
        self._append_jsonl(self._response_corpus_path(), record)
        return record

    def _response_corpus_path(self) -> Path:
        return Path(__file__).resolve().parents[1] / "data" / "response_training_corpus.jsonl"

    def _append_jsonl(self, path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as output_file:
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def record_chat_examples(
        self,
        db: Session,
        user_id: uuid.UUID,
        user_message: str,
        assistant_speech: str,
        emotion_result: dict[str, Any],
        memory_updates: list[dict[str, Any]],
        privacy_notes: list[str],
        social_graph: dict[str, list[dict[str, Any]]],
        robot_state: dict[str, Any],
        context: dict[str, Any],
    ) -> None:
        examples = [
            self._build_example(
                user_id,
                "emotion_classification",
                {"message": user_message, "context": context},
                emotion_result,
                confidence=float(emotion_result.get("confidence", 0.5)),
            ),
            self._build_example(
                user_id,
                "memory_importance_scoring",
                {"message": user_message, "assistant_speech": assistant_speech},
                {"memory_updates": memory_updates},
                confidence=0.6,
            ),
            self._build_example(
                user_id,
                "privacy_classification",
                {"message": user_message, "context": context},
                {"privacy_notes": privacy_notes},
                confidence=0.7,
            ),
            self._build_example(
                user_id,
                "person_relationship_extraction",
                {"message": user_message},
                social_graph,
                confidence=0.6,
            ),
            self._build_example(
                user_id,
                "robot_action_selection",
                {"message": user_message, "emotion_result": emotion_result, "context": context},
                {"robot_state": robot_state},
                confidence=0.7,
            ),
        ]
        db.add_all(examples)
        db.commit()

    def list_examples(
        self,
        db: Session,
        task_type: str | None = None,
        limit: int = 100,
    ) -> list[TrainingExample]:
        query = db.query(TrainingExample)
        if task_type:
            query = query.filter(TrainingExample.task_type == task_type)
        return query.order_by(desc(TrainingExample.created_at)).limit(limit).all()

    def approve_example(self, db: Session, example_id: uuid.UUID) -> TrainingExample | None:
        example = db.get(TrainingExample, example_id)
        if example is None:
            return None
        example.approved = True
        db.commit()
        db.refresh(example)
        return example

    def correct_example(
        self,
        db: Session,
        example_id: uuid.UUID,
        corrected_target_json: dict[str, Any],
        notes: str | None,
    ) -> HumanCorrection | None:
        example = db.get(TrainingExample, example_id)
        if example is None:
            return None

        correction = HumanCorrection(
            training_example_id=example_id,
            corrected_target_json=corrected_target_json,
            notes=notes,
        )
        example.target_json = corrected_target_json
        example.approved = True
        db.add(correction)
        db.commit()
        db.refresh(correction)
        return correction

    def export_examples(
        self,
        db: Session,
        task_type: str | None = None,
        approved_only: bool = False,
    ) -> list[dict[str, Any]]:
        query = db.query(TrainingExample)
        if task_type:
            query = query.filter(TrainingExample.task_type == task_type)
        if approved_only:
            query = query.filter(TrainingExample.approved.is_(True))

        return [self.serialize_example(example) for example in query.order_by(TrainingExample.created_at).all()]

    def serialize_example(self, example: TrainingExample) -> dict[str, Any]:
        return {
            "id": str(example.id),
            "user_id": str(example.user_id),
            "task_type": example.task_type,
            "input_json": example.input_json,
            "target_json": example.target_json,
            "source": example.source,
            "confidence": example.confidence,
            "approved": example.approved,
            "created_at": example.created_at,
        }

    def serialize_correction(self, correction: HumanCorrection) -> dict[str, Any]:
        return {
            "id": str(correction.id),
            "training_example_id": str(correction.training_example_id),
            "corrected_target_json": correction.corrected_target_json,
            "notes": correction.notes,
            "created_at": correction.created_at,
        }

    def _build_example(
        self,
        user_id: uuid.UUID,
        task_type: str,
        input_json: dict[str, Any],
        target_json: dict[str, Any],
        confidence: float,
    ) -> TrainingExample:
        return TrainingExample(
            user_id=user_id,
            task_type=task_type,
            input_json=input_json,
            target_json=target_json,
            source="chat_pipeline",
            confidence=max(0.0, min(confidence, 1.0)),
            approved=False,
        )


training_data_service = TrainingDataService()
