from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str | None = None
    conversation_id: str | None = None
    message: str
    present_people: list[str] | None = None
    context_mode: str = "private"
    scene_context: str | None = None
    companion_name: str | None = None


class RobotState(BaseModel):
    emotion: str
    face: str
    eyes: str
    mouth: str
    voice_tone: str
    body_action: str
    head_motion: str
    eye_contact: str
    movement_intensity: str
    should_speak: bool


class MemoryUpdate(BaseModel):
    type: str
    content: str
    importance: float
    privacy: str
    related_people: list[str] | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    reply: str
    brain_state: dict = Field(default_factory=dict)
    speech: str
    robot_state: RobotState
    memory_updates: list[MemoryUpdate] = Field(default_factory=list)
    privacy_notes: list[str] = Field(default_factory=list)
    used_memories: list[str] = Field(default_factory=list)
