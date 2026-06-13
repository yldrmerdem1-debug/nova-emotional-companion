import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import Memory, Person
from app.services.openai_service import openai_service


ALLOWED_MEMORY_TYPES = {
    "user_identity",
    "user_goal",
    "preference",
    "person_profile",
    "relationship",
    "event",
    "emotional_pattern",
    "boundary",
    "project_context",
}
ALLOWED_PRIVACY_LEVELS = {"private", "shared", "public", "sensitive"}


class MemoryService:
    def extract_memory_updates(
        self,
        user_message: str,
        assistant_speech: str,
        emotion_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        result = openai_service.generate_json_response(
            system_prompt=(
                "You extract important long-term memories for an AI companion robot.\n"
                "Return JSON only with this shape: {\"memories\": [...]}.\n"
                "Do not store random trivial facts.\n"
                "Store stable preferences, goals, people, relationships, projects, "
                "emotional patterns, boundaries.\n"
                "If third-party people are mentioned, store them carefully with privacy.\n"
                "Sensitive personal issues should be private or sensitive.\n"
                "Return an empty memories array if nothing is worth storing."
            ),
            user_prompt=(
                "Each memory item must include: type, content, importance, privacy, "
                "related_people.\n"
                "type must be one of: user_identity, user_goal, preference, "
                "person_profile, relationship, event, emotional_pattern, boundary, "
                "project_context.\n"
                "privacy must be one of: private, shared, public, sensitive.\n"
                "importance must be a number from 0.0 to 1.0.\n\n"
                f"User message: {user_message}\n"
                f"Assistant speech: {assistant_speech}\n"
                f"Emotion result: {emotion_result}"
            ),
        )

        memories = result.get("memories", [])
        if not isinstance(memories, list):
            return []

        return [
            normalized
            for item in memories
            if isinstance(item, dict)
            for normalized in [self._normalize_memory_update(item)]
            if normalized is not None
        ]

    def save_memories(
        self,
        db: Session,
        user_id: str | uuid.UUID,
        updates: list[dict[str, Any]],
    ) -> list[Memory]:
        saved_memories: list[Memory] = []
        parsed_user_id = self._parse_user_id(user_id)
        do_not_store_names = self._get_do_not_store_names(db, parsed_user_id)

        for update in updates:
            normalized = self._normalize_memory_update(update)
            if normalized is None:
                continue
            if self._mentions_do_not_store_person(normalized, do_not_store_names):
                continue

            embedding = openai_service.embed_text(normalized["content"]) or None
            memory = Memory(
                user_id=parsed_user_id,
                memory_type=normalized["type"],
                content=normalized["content"],
                importance=normalized["importance"],
                emotion=normalized.get("emotion"),
                privacy_level=normalized["privacy"],
                related_people=normalized.get("related_people"),
                embedding=embedding,
            )
            db.add(memory)
            saved_memories.append(memory)

        if not saved_memories:
            return []

        try:
            db.commit()
        except (AttributeError, SQLAlchemyError, ValueError):
            db.rollback()
            return []

        for memory in saved_memories:
            db.refresh(memory)

        return saved_memories

    def retrieve_relevant_memories(
        self,
        db: Session,
        user_id: str | uuid.UUID,
        message: str,
        limit: int = 8,
    ) -> list[Memory]:
        parsed_user_id = self._parse_user_id(user_id)
        capped_limit = min(limit, 8)
        embedding = openai_service.embed_text(message)

        if embedding:
            memories = self._retrieve_with_pgvector(db, parsed_user_id, embedding, capped_limit)
            if memories:
                self._mark_memories_used(db, memories)
                return memories

        memories = self._retrieve_fallback_memories(db, parsed_user_id, message, capped_limit)
        self._mark_memories_used(db, memories)
        return memories

    def format_memories_for_prompt(self, memories: list[Memory]) -> str:
        if not memories:
            return "No relevant long-term memories."

        return "\n".join(
            f"- [{memory.privacy_level}] ({memory.memory_type}, "
            f"importance {memory.importance:.2f}) {memory.content}"
            for memory in memories
        )

    def consolidate_memories(self, db: Session, user_id: str | uuid.UUID) -> dict[str, int]:
        parsed_user_id = self._parse_user_id(user_id)
        memories = (
            db.query(Memory)
            .filter(Memory.user_id == parsed_user_id, Memory.archived.is_(False))
            .order_by(desc(Memory.importance), desc(Memory.created_at))
            .all()
        )
        groups: dict[str, list[Memory]] = {}

        for memory in memories:
            normalized_content = self._normalize_content_key(memory.content)
            if not normalized_content:
                continue
            groups.setdefault(normalized_content, []).append(memory)

        merged_groups = 0
        archived_count = 0

        for duplicates in groups.values():
            if len(duplicates) < 2:
                continue

            keeper = self._select_memory_keeper(duplicates)
            duplicate_memories = [memory for memory in duplicates if memory.id != keeper.id]
            keeper.importance = max(memory.importance for memory in duplicates)
            keeper.related_people = self._merge_related_people(duplicates)
            keeper.content = self._select_clearer_content(duplicates)

            for memory in duplicate_memories:
                memory.archived = True

            merged_groups += 1
            archived_count += len(duplicate_memories)

        if archived_count:
            try:
                db.commit()
            except SQLAlchemyError:
                db.rollback()
                return {"merged_groups": 0, "archived_memories": 0}

        return {"merged_groups": merged_groups, "archived_memories": archived_count}

    def remember(self, message: str) -> None:
        # Temporary compatibility for the placeholder chat route.
        return None

    def _retrieve_with_pgvector(
        self,
        db: Session,
        user_id: uuid.UUID,
        embedding: list[float],
        limit: int,
    ) -> list[Memory]:
        try:
            cosine_distance = Memory.embedding.cosine_distance(embedding)
            combined_score = cosine_distance - (Memory.importance * 0.15)

            memories = (
                db.query(Memory)
                .filter(
                    Memory.user_id == user_id,
                    Memory.archived.is_(False),
                    Memory.embedding.is_not(None),
                )
                .order_by(combined_score, desc(Memory.importance), desc(Memory.created_at))
                .limit(limit * 3)
                .all()
            )
            return self._dedupe_memories(memories, limit)
        except (AttributeError, SQLAlchemyError, ValueError):
            db.rollback()
            return []

    def _retrieve_fallback_memories(
        self,
        db: Session,
        user_id: uuid.UUID,
        message: str,
        limit: int,
    ) -> list[Memory]:
        candidates: list[Memory] = []

        candidates.extend(
            db.query(Memory)
            .filter(Memory.user_id == user_id, Memory.archived.is_(False))
            .order_by(desc(Memory.importance), desc(Memory.created_at))
            .limit(limit * 2)
            .all()
        )
        candidates.extend(
            db.query(Memory)
            .filter(Memory.user_id == user_id, Memory.archived.is_(False))
            .order_by(desc(Memory.created_at))
            .limit(limit * 2)
            .all()
        )

        keywords = self._extract_keywords(message)
        if keywords:
            keyword_filters = [Memory.content.ilike(f"%{keyword}%") for keyword in keywords]
            candidates.extend(
                db.query(Memory)
                .filter(Memory.user_id == user_id, Memory.archived.is_(False), or_(*keyword_filters))
                .order_by(desc(Memory.importance), desc(Memory.created_at))
                .limit(limit * 2)
                .all()
            )

        return self._rank_fallback_memories(candidates, keywords, limit)

    def _rank_fallback_memories(
        self,
        memories: list[Memory],
        keywords: set[str],
        limit: int,
    ) -> list[Memory]:
        deduped = self._dedupe_memories(memories, limit=len(memories))
        ranked = sorted(
            deduped,
            key=lambda memory: (
                self._keyword_overlap(memory.content, keywords),
                memory.importance,
                memory.created_at or datetime.min.replace(tzinfo=timezone.utc),
            ),
            reverse=True,
        )
        return ranked[:limit]

    def _dedupe_memories(self, memories: list[Memory], limit: int) -> list[Memory]:
        deduped = []
        seen_content = set()

        for memory in memories:
            normalized_content = memory.content.strip().lower()
            if normalized_content in seen_content:
                continue
            deduped.append(memory)
            seen_content.add(normalized_content)
            if len(deduped) >= limit:
                break

        return deduped

    def _mark_memories_used(self, db: Session, memories: list[Memory]) -> None:
        if not memories:
            return

        used_at = datetime.now(timezone.utc)
        for memory in memories:
            memory.last_used_at = used_at

        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()

    def _extract_keywords(self, message: str) -> set[str]:
        stop_words = {
            "about",
            "again",
            "ben",
            "bir",
            "bunu",
            "can",
            "cok",
            "daha",
            "gibi",
            "icin",
            "ile",
            "sey",
            "tell",
            "the",
            "this",
            "what",
            "when",
            "with",
        }
        cleaned = "".join(character.lower() if character.isalnum() else " " for character in message)
        return {
            word
            for word in cleaned.split()
            if len(word) >= 3 and word not in stop_words
        }

    def _keyword_overlap(self, content: str, keywords: set[str]) -> int:
        if not keywords:
            return 0

        normalized_content = content.lower()
        return sum(1 for keyword in keywords if keyword in normalized_content)

    def _normalize_content_key(self, content: str) -> str:
        return " ".join(content.strip().lower().split())

    def _select_memory_keeper(self, memories: list[Memory]) -> Memory:
        return max(
            memories,
            key=lambda memory: (
                memory.importance,
                len(memory.content.strip()),
                memory.created_at or datetime.min.replace(tzinfo=timezone.utc),
            ),
        )

    def _select_clearer_content(self, memories: list[Memory]) -> str:
        return max((memory.content.strip() for memory in memories), key=len)

    def _merge_related_people(self, memories: list[Memory]) -> list[str]:
        merged_people = []
        seen_people = set()

        for memory in memories:
            related_people = memory.related_people or []
            if not isinstance(related_people, list):
                continue

            for person in related_people:
                if not isinstance(person, str) or not person.strip():
                    continue
                normalized_person = person.strip().lower()
                if normalized_person in seen_people:
                    continue
                merged_people.append(person.strip())
                seen_people.add(normalized_person)

        return merged_people

    def _get_do_not_store_names(self, db: Session, user_id: uuid.UUID) -> set[str]:
        people = (
            db.query(Person)
            .filter(Person.user_id == user_id, Person.consent_status == "do_not_store")
            .all()
        )
        return {person.name.strip().lower() for person in people if person.name.strip()}

    def _mentions_do_not_store_person(
        self,
        memory_update: dict[str, Any],
        do_not_store_names: set[str],
    ) -> bool:
        if not do_not_store_names:
            return False

        related_people = memory_update.get("related_people") or []
        for person in related_people:
            if isinstance(person, str) and person.strip().lower() in do_not_store_names:
                return True

        content = memory_update["content"].lower()
        return any(name in content for name in do_not_store_names)

    def _normalize_memory_update(self, update: dict[str, Any]) -> dict[str, Any] | None:
        memory_type = update.get("type")
        content = update.get("content")
        privacy = update.get("privacy")
        related_people = update.get("related_people") or []

        if memory_type not in ALLOWED_MEMORY_TYPES:
            return None
        if privacy not in ALLOWED_PRIVACY_LEVELS:
            return None
        if not isinstance(content, str) or not content.strip():
            return None
        if not isinstance(related_people, list):
            related_people = []

        try:
            importance = float(update.get("importance"))
        except (TypeError, ValueError):
            return None

        if not 0.0 <= importance <= 1.0:
            return None

        return {
            "type": memory_type,
            "content": content.strip(),
            "importance": importance,
            "privacy": privacy,
            "related_people": [
                person for person in related_people if isinstance(person, str) and person.strip()
            ],
        }

    def _parse_user_id(self, user_id: str | uuid.UUID) -> uuid.UUID:
        if isinstance(user_id, uuid.UUID):
            return user_id
        return uuid.UUID(user_id)


memory_service = MemoryService()
