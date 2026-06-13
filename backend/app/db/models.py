import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id"),
        nullable=False,
    )
    role = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Memory(Base):
    __tablename__ = "memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    memory_type = Column(String(64), nullable=False)
    content = Column(Text, nullable=False)
    importance = Column(Float, nullable=False)
    emotion = Column(String(64), nullable=True)
    privacy_level = Column(String(64), nullable=False)
    related_people = Column(JSON, nullable=True)
    # Requires the PostgreSQL pgvector extension. Startup creates it for local dev.
    embedding = Column(Vector(1536), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    archived = Column(Boolean, nullable=False, default=False, server_default="false")


class Person(Base):
    __tablename__ = "people"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    relationship_to_user = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    privacy_level = Column(String(64), nullable=False, default="normal")
    consent_status = Column(String(64), nullable=False, default="unknown", server_default="unknown")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Relationship(Base):
    __tablename__ = "relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    person_a_id = Column(UUID(as_uuid=True), ForeignKey("people.id"), nullable=True)
    person_b_id = Column(UUID(as_uuid=True), ForeignKey("people.id"), nullable=True)
    relationship_type = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    emotion = Column(String(64), nullable=True)
    importance = Column(Float, nullable=False)
    people_involved = Column(JSON, nullable=True)
    privacy_level = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RobotAction(Base):
    __tablename__ = "robot_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id"),
        nullable=True,
    )
    emotion = Column(String(64), nullable=False)
    face = Column(String(255), nullable=False)
    eyes = Column(String(255), nullable=False, default="center", server_default="center")
    mouth = Column(String(255), nullable=False, default="small_smile", server_default="small_smile")
    voice_tone = Column(String(255), nullable=False)
    body_action = Column(String(255), nullable=False)
    head_motion = Column(String(255), nullable=False, default="none", server_default="none")
    eye_contact = Column(String(255), nullable=False, default="medium", server_default="medium")
    movement_intensity = Column(String(255), nullable=False, default="low", server_default="low")
    should_speak = Column(Boolean, nullable=False, default=True, server_default="true")
    raw_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RobotDevice(Base):
    __tablename__ = "robot_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    device_name = Column(String(255), nullable=False)
    status = Column(JSON, nullable=False, default=dict)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RobotSensorEvent(Base):
    __tablename__ = "robot_sensor_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_type = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TrainingExample(Base):
    __tablename__ = "training_examples"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    task_type = Column(String(128), nullable=False)
    input_json = Column(JSON, nullable=False)
    target_json = Column(JSON, nullable=False)
    source = Column(String(128), nullable=False)
    confidence = Column(Float, nullable=False)
    approved = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class HumanCorrection(Base):
    __tablename__ = "human_corrections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    training_example_id = Column(
        UUID(as_uuid=True),
        ForeignKey("training_examples.id"),
        nullable=False,
    )
    corrected_target_json = Column(JSON, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    task_type = Column(String(128), nullable=False)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EvaluationCase(Base):
    __tablename__ = "evaluation_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type = Column(String(128), nullable=False)
    input_json = Column(JSON, nullable=False)
    expected_json = Column(JSON, nullable=False)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
