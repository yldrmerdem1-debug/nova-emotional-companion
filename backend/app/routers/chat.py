import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Event, Memory, Person
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.brain_service import brain_service
from app.services.memory_service import memory_service
from app.services.proactive_service import proactive_service

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    return brain_service.process_chat(db, request)


@router.get("/users/{user_id}/memories")
def get_user_memories(user_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    memories = db.query(Memory).filter(Memory.user_id == user_id).all()
    return [
        {
            "id": str(memory.id),
            "user_id": str(memory.user_id),
            "memory_type": memory.memory_type,
            "content": memory.content,
            "importance": memory.importance,
            "emotion": memory.emotion,
            "privacy_level": memory.privacy_level,
            "related_people": memory.related_people,
            "created_at": memory.created_at,
            "last_used_at": memory.last_used_at,
            "archived": memory.archived,
        }
        for memory in memories
    ]


@router.post("/users/{user_id}/memories/consolidate")
def consolidate_user_memories(user_id: uuid.UUID, db: Session = Depends(get_db)) -> dict[str, int]:
    return memory_service.consolidate_memories(db, user_id)


@router.get("/users/{user_id}/people")
def get_user_people(user_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    people = db.query(Person).filter(Person.user_id == user_id).all()
    return [
        {
            "id": str(person.id),
            "user_id": str(person.user_id),
            "name": person.name,
            "relationship_to_user": person.relationship_to_user,
            "notes": person.notes,
            "privacy_level": person.privacy_level,
            "consent_status": person.consent_status,
            "created_at": person.created_at,
        }
        for person in people
    ]


@router.get("/users/{user_id}/events")
def get_user_events(user_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    events = db.query(Event).filter(Event.user_id == user_id).all()
    return [
        {
            "id": str(event.id),
            "user_id": str(event.user_id),
            "title": event.title,
            "description": event.description,
            "emotion": event.emotion,
            "importance": event.importance,
            "people_involved": event.people_involved,
            "privacy_level": event.privacy_level,
            "created_at": event.created_at,
        }
        for event in events
    ]


@router.get("/users/{user_id}/proactive-suggestion")
def get_proactive_suggestion(user_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    return proactive_service.suggest_next_checkin(db, user_id)
