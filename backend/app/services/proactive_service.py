import uuid

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.models import Event, Memory, RobotAction


class ProactiveService:
    def suggest_next_checkin(self, db: Session, user_id: str | uuid.UUID) -> dict:
        parsed_user_id = self._parse_user_id(user_id)
        recent_memories = self._recent_memories(db, parsed_user_id)
        recent_emotions = self._recent_emotions(db, parsed_user_id)
        last_event = self._last_event(db, parsed_user_id)
        user_goals = [
            memory
            for memory in recent_memories
            if memory.memory_type in {"user_goal", "project_context"}
        ]

        emotional_suggestion = self._emotional_suggestion(recent_emotions)
        if emotional_suggestion is not None:
            return emotional_suggestion

        goal_suggestion = self._goal_suggestion(user_goals)
        if goal_suggestion is not None:
            return goal_suggestion

        if last_event is not None and last_event.importance >= 0.65:
            return {
                "should_check_in": True,
                "reason": f"Recent important event: {last_event.title}",
                "suggested_message": f"{last_event.title} hakkinda kisa bir devam adimi dusunmek ister misin?",
                "priority": min(last_event.importance, 0.8),
            }

        return {
            "should_check_in": False,
            "reason": "No strong recent goal, event, or emotional signal.",
            "suggested_message": "",
            "priority": 0.0,
        }

    def _recent_memories(self, db: Session, user_id: uuid.UUID) -> list[Memory]:
        return (
            db.query(Memory)
            .filter(Memory.user_id == user_id, Memory.archived.is_(False))
            .order_by(desc(Memory.created_at))
            .limit(20)
            .all()
        )

    def _recent_emotions(self, db: Session, user_id: uuid.UUID) -> list[str]:
        actions = (
            db.query(RobotAction)
            .filter(RobotAction.user_id == user_id)
            .order_by(desc(RobotAction.created_at))
            .limit(8)
            .all()
        )
        return [action.emotion for action in actions]

    def _last_event(self, db: Session, user_id: uuid.UUID) -> Event | None:
        return (
            db.query(Event)
            .filter(Event.user_id == user_id)
            .order_by(desc(Event.created_at))
            .first()
        )

    def _emotional_suggestion(self, emotions: list[str]) -> dict | None:
        difficult_emotions = {"angry", "sad", "anxious", "concerned"}
        if not any(emotion in difficult_emotions for emotion in emotions[:3]):
            return None

        return {
            "should_check_in": True,
            "reason": "Recent emotional state looked heavy.",
            "suggested_message": "Bugun fazla ustune gelmeden sadece nasil oldugunu sorabilirim.",
            "priority": 0.75,
        }

    def _goal_suggestion(self, goals: list[Memory]) -> dict | None:
        if not goals:
            return None

        strongest_goal = max(goals, key=lambda memory: memory.importance)
        content = strongest_goal.content.lower()
        if "robot" in content and ("ai" in content or "zeka" in content):
            message = "Bugun robotun memory graph tarafina 20 dakika bakmak ister misin?"
        else:
            message = f"Bugun su hedef icin kucuk bir adim atalim mi: {strongest_goal.content}"

        return {
            "should_check_in": True,
            "reason": f"Recent user goal: {strongest_goal.content}",
            "suggested_message": message,
            "priority": min(0.6 + strongest_goal.importance * 0.3, 0.9),
        }

    def _parse_user_id(self, user_id: str | uuid.UUID) -> uuid.UUID:
        if isinstance(user_id, uuid.UUID):
            return user_id
        return uuid.UUID(user_id)


proactive_service = ProactiveService()
