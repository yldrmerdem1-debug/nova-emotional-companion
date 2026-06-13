import uuid
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import Event, Person, Relationship
from app.services.openai_service import openai_service


RELATIONSHIPS_TO_USER = {"friend", "family", "teammate", "teacher", "unknown"}
PERSON_PRIVACY_LEVELS = {"normal", "private", "sensitive"}
EVENT_PRIVACY_LEVELS = {"private", "shared", "public", "sensitive"}
CONSENT_STATUSES = {"unknown", "user_introduced", "person_confirmed", "do_not_store"}


class SocialGraphService:
    def extract_people_and_relationships(self, user_message: str) -> dict[str, list[dict[str, Any]]]:
        result = openai_service.generate_json_response(
            system_prompt=(
                "You extract people, relationships, and meaningful events for an AI "
                "companion robot.\n"
                "Return JSON only.\n"
                "Be conservative.\n"
                "Do not assume romantic, family, teammate, teacher, or other "
                "relationships unless directly stated.\n"
                "Unknown people should remain unknown.\n"
                "Track third-party memory consent conservatively."
            ),
            user_prompt=(
                "Return this exact JSON shape: "
                "{\"people\": [], \"relationships\": [], \"events\": []}.\n"
                "People fields: name, relationship_to_user, notes, privacy_level, consent_status.\n"
                "relationship_to_user must be one of: friend, family, teammate, "
                "teacher, unknown.\n"
                "person privacy_level must be one of: normal, private, sensitive.\n"
                "consent_status must be one of: unknown, user_introduced, "
                "person_confirmed, do_not_store.\n"
                "Use user_introduced only when the user clearly introduces the person "
                "or states their relationship, like 'Bu Ali, arkadasim' or "
                "'Ali diye arkadasim var'.\n"
                "Use person_confirmed only when the person directly consents to being remembered.\n"
                "Use do_not_store when the user or person says not to remember/store them.\n"
                "Relationship fields: person_a, person_b, relationship_type, notes.\n"
                "Event fields: title, description, emotion, importance, "
                "people_involved, privacy_level.\n"
                "event privacy_level must be one of: private, shared, public, "
                "sensitive.\n"
                "importance must be 0.0 to 1.0.\n"
                "Return empty arrays for anything not clearly present.\n\n"
                f"User message: {user_message}"
            ),
        )

        return {
            "people": self._normalize_people(result.get("people", [])),
            "relationships": self._normalize_relationships(result.get("relationships", [])),
            "events": self._normalize_events(result.get("events", [])),
        }

    def save_social_graph(
        self,
        db: Session,
        user_id: str | uuid.UUID,
        extracted: dict[str, list[dict[str, Any]]],
    ) -> dict[str, int]:
        parsed_user_id = self._parse_user_id(user_id)
        people_by_name: dict[str, Person] = {}
        saved_counts = {"people": 0, "relationships": 0, "events": 0}

        try:
            for person_data in self._normalize_people(extracted.get("people", [])):
                person = self._upsert_person(db, parsed_user_id, person_data)
                people_by_name[person.name.lower()] = person
                saved_counts["people"] += 1

            for event_data in self._normalize_events(extracted.get("events", [])):
                if event_data["importance"] <= 0.5:
                    continue
                if self._has_do_not_store_person(event_data.get("people_involved"), people_by_name):
                    continue

                db.add(
                    Event(
                        user_id=parsed_user_id,
                        title=event_data["title"],
                        description=event_data["description"],
                        emotion=event_data.get("emotion"),
                        importance=event_data["importance"],
                        people_involved=event_data.get("people_involved"),
                        privacy_level=event_data["privacy_level"],
                    )
                )
                saved_counts["events"] += 1

            for relationship_data in self._normalize_relationships(
                extracted.get("relationships", [])
            ):
                person_a = people_by_name.get(relationship_data["person_a"].lower())
                person_b = people_by_name.get(relationship_data["person_b"].lower())
                if person_a is None or person_b is None:
                    continue
                if (
                    person_a.consent_status == "do_not_store"
                    or person_b.consent_status == "do_not_store"
                ):
                    continue

                db.add(
                    Relationship(
                        user_id=parsed_user_id,
                        person_a_id=person_a.id,
                        person_b_id=person_b.id,
                        relationship_type=relationship_data["relationship_type"],
                        notes=relationship_data.get("notes"),
                    )
                )
                saved_counts["relationships"] += 1

            db.commit()
        except SQLAlchemyError:
            db.rollback()
            return {"people": 0, "relationships": 0, "events": 0}

        return saved_counts

    def get_people_context(
        self,
        db: Session,
        user_id: str | uuid.UUID,
        present_people: list[str],
    ) -> str:
        parsed_user_id = self._parse_user_id(user_id)
        names = [name.strip() for name in present_people if name.strip()]
        if not names:
            return "No specific people are currently marked as present."

        known_people = (
            db.query(Person)
            .filter(
                Person.user_id == parsed_user_id,
                func.lower(Person.name).in_([name.lower() for name in names]),
            )
            .all()
        )
        known_by_name = {person.name.lower(): person for person in known_people}
        unknown_names = [name for name in names if name.lower() not in known_by_name]

        lines = []
        if known_people:
            lines.append("People currently present:")
            lines.extend(
                f"- {person.name}: {person.relationship_to_user or 'unknown'}; "
                f"privacy={person.privacy_level}; consent={person.consent_status}; "
                f"notes={person.notes or 'none'}"
                for person in known_people
            )

        if unknown_names:
            lines.append(
                "Privacy warning: unknown people are present "
                f"({', '.join(unknown_names)}). Avoid sharing private or sensitive details."
            )

        return "\n".join(lines)

    def extract_relationships(self, message: str) -> list[dict[str, Any]]:
        # Temporary compatibility for the placeholder chat route.
        return self.extract_people_and_relationships(message)["relationships"]

    def _upsert_person(
        self,
        db: Session,
        user_id: uuid.UUID,
        person_data: dict[str, Any],
    ) -> Person:
        person = (
            db.query(Person)
            .filter(
                Person.user_id == user_id,
                func.lower(Person.name) == person_data["name"].lower(),
            )
            .one_or_none()
        )

        if person is None:
            consent_status = person_data["consent_status"]
            notes = person_data.get("notes")
            if consent_status == "unknown":
                notes = None

            person = Person(
                user_id=user_id,
                name=person_data["name"],
                relationship_to_user=person_data["relationship_to_user"],
                notes=notes,
                privacy_level=person_data["privacy_level"],
                consent_status=consent_status,
            )
            db.add(person)
            db.flush()
            return person

        if person.consent_status == "do_not_store":
            return person

        consent_status = self._stronger_consent_status(
            person.consent_status,
            person_data["consent_status"],
        )
        person.consent_status = consent_status
        person.relationship_to_user = person_data["relationship_to_user"]
        if consent_status != "unknown":
            person.notes = person_data.get("notes") or person.notes
        person.privacy_level = person_data["privacy_level"]
        return person

    def _normalize_people(self, people: Any) -> list[dict[str, Any]]:
        if not isinstance(people, list):
            return []

        normalized = []
        for person in people:
            if not isinstance(person, dict):
                continue

            name = person.get("name")
            if not isinstance(name, str) or not name.strip():
                continue

            relationship_to_user = person.get("relationship_to_user")
            if relationship_to_user not in RELATIONSHIPS_TO_USER:
                relationship_to_user = "unknown"

            privacy_level = person.get("privacy_level")
            if privacy_level not in PERSON_PRIVACY_LEVELS:
                privacy_level = "private"

            notes = person.get("notes")
            consent_status = person.get("consent_status")
            if consent_status not in CONSENT_STATUSES:
                consent_status = "user_introduced" if relationship_to_user != "unknown" else "unknown"
            if consent_status == "unknown":
                notes = None
            if consent_status == "do_not_store":
                relationship_to_user = "unknown"
                notes = None
                privacy_level = "private"

            normalized.append(
                {
                    "name": name.strip(),
                    "relationship_to_user": relationship_to_user,
                    "notes": notes.strip() if isinstance(notes, str) else None,
                    "privacy_level": privacy_level,
                    "consent_status": consent_status,
                }
            )

        return normalized

    def _normalize_relationships(self, relationships: Any) -> list[dict[str, Any]]:
        if not isinstance(relationships, list):
            return []

        normalized = []
        for relationship in relationships:
            if not isinstance(relationship, dict):
                continue

            person_a = relationship.get("person_a")
            person_b = relationship.get("person_b")
            relationship_type = relationship.get("relationship_type")
            if not all(
                isinstance(value, str) and value.strip()
                for value in [person_a, person_b, relationship_type]
            ):
                continue

            notes = relationship.get("notes")
            normalized.append(
                {
                    "person_a": person_a.strip(),
                    "person_b": person_b.strip(),
                    "relationship_type": relationship_type.strip(),
                    "notes": notes.strip() if isinstance(notes, str) else None,
                }
            )

        return normalized

    def _normalize_events(self, events: Any) -> list[dict[str, Any]]:
        if not isinstance(events, list):
            return []

        normalized = []
        for event in events:
            if not isinstance(event, dict):
                continue

            title = event.get("title")
            description = event.get("description")
            if not isinstance(title, str) or not title.strip():
                continue
            if not isinstance(description, str) or not description.strip():
                continue

            try:
                importance = float(event.get("importance"))
            except (TypeError, ValueError):
                continue

            if not 0.0 <= importance <= 1.0:
                continue

            privacy_level = event.get("privacy_level")
            if privacy_level not in EVENT_PRIVACY_LEVELS:
                privacy_level = "private"

            people_involved = event.get("people_involved") or []
            if not isinstance(people_involved, list):
                people_involved = []

            emotion = event.get("emotion")
            normalized.append(
                {
                    "title": title.strip(),
                    "description": description.strip(),
                    "emotion": emotion.strip() if isinstance(emotion, str) else None,
                    "importance": importance,
                    "people_involved": [
                        person
                        for person in people_involved
                        if isinstance(person, str) and person.strip()
                    ],
                    "privacy_level": privacy_level,
                }
            )

        return normalized

    def _has_do_not_store_person(
        self,
        people_involved: Any,
        people_by_name: dict[str, Person],
    ) -> bool:
        if not isinstance(people_involved, list):
            return False

        for name in people_involved:
            if not isinstance(name, str):
                continue
            person = people_by_name.get(name.strip().lower())
            if person is not None and person.consent_status == "do_not_store":
                return True

        return False

    def _stronger_consent_status(self, current_status: str, next_status: str) -> str:
        priority = {
            "unknown": 0,
            "user_introduced": 1,
            "person_confirmed": 2,
            "do_not_store": 3,
        }
        if priority.get(next_status, 0) > priority.get(current_status, 0):
            return next_status
        return current_status

    def _parse_user_id(self, user_id: str | uuid.UUID) -> uuid.UUID:
        if isinstance(user_id, uuid.UUID):
            return user_id
        return uuid.UUID(user_id)


social_graph_service = SocialGraphService()
