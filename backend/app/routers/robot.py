import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import RobotAction, RobotDevice, RobotSensorEvent

router = APIRouter(prefix="/robot", tags=["robot"])


class RobotHeartbeatRequest(BaseModel):
    battery_level: float
    online: bool
    current_mode: str
    sensor_summary: dict = Field(default_factory=dict)
    device_name: str = "default"


class RobotSensorEventRequest(BaseModel):
    event_type: Literal["person_detected", "touch", "sound", "movement", "wake_word"]
    payload: dict = Field(default_factory=dict)


@router.get("/{user_id}/latest-action")
def get_latest_robot_action(user_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    action = (
        db.query(RobotAction)
        .filter(RobotAction.user_id == user_id)
        .order_by(desc(RobotAction.created_at))
        .first()
    )
    if action is None:
        return {"action": None}

    return {
        "id": str(action.id),
        "user_id": str(action.user_id),
        "conversation_id": str(action.conversation_id) if action.conversation_id else None,
        "emotion": action.emotion,
        "face": action.face,
        "eyes": action.eyes,
        "mouth": action.mouth,
        "voice_tone": action.voice_tone,
        "body_action": action.body_action,
        "head_motion": action.head_motion,
        "eye_contact": action.eye_contact,
        "movement_intensity": action.movement_intensity,
        "should_speak": action.should_speak,
        "raw_json": action.raw_json,
        "created_at": action.created_at,
    }


@router.post("/{user_id}/heartbeat")
def robot_heartbeat(
    user_id: uuid.UUID,
    request: RobotHeartbeatRequest,
    db: Session = Depends(get_db),
) -> dict:
    now = datetime.now(timezone.utc)
    device = (
        db.query(RobotDevice)
        .filter(
            RobotDevice.user_id == user_id,
            func.lower(RobotDevice.device_name) == request.device_name.lower(),
        )
        .one_or_none()
    )

    status = {
        "battery_level": request.battery_level,
        "online": request.online,
        "current_mode": request.current_mode,
        "sensor_summary": request.sensor_summary,
    }

    if device is None:
        device = RobotDevice(
            user_id=user_id,
            device_name=request.device_name,
            status=status,
            last_seen_at=now,
        )
        db.add(device)
    else:
        device.status = status
        device.last_seen_at = now

    db.commit()

    optional_instruction = None
    if request.battery_level < 15:
        optional_instruction = "battery_low_seek_charger"

    return {
        "acknowledged": True,
        "optional_instruction": optional_instruction,
    }


@router.post("/{user_id}/sensor-event")
def robot_sensor_event(
    user_id: uuid.UUID,
    request: RobotSensorEventRequest,
    db: Session = Depends(get_db),
) -> dict:
    event = RobotSensorEvent(
        user_id=user_id,
        event_type=request.event_type,
        payload=request.payload,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return {
        "acknowledged": True,
        "event_id": str(event.id),
        "message": "Sensor event logged.",
    }
