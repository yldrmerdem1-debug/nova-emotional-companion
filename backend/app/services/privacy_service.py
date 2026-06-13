class PrivacyService:
    def filter_memories_for_context(
        self,
        memories,
        context_mode: str,
        present_people: list[str],
        scene_context: str | None = None,
    ) -> tuple[list, list[str]]:
        allowed_memories = []
        privacy_notes = []
        effective_context_mode = self.get_effective_context_mode(
            context_mode,
            present_people,
            scene_context,
        )

        if effective_context_mode != context_mode:
            privacy_notes.append("Scene context suggests others may be present; private memories restricted.")

        for memory in memories:
            note = self._privacy_note(memory, effective_context_mode, present_people)
            if self.can_say_memory(memory, effective_context_mode, present_people):
                allowed_memories.append(memory)
            if note:
                privacy_notes.append(note)

        return allowed_memories, privacy_notes

    def can_say_memory(self, memory, context_mode: str, present_people: list[str]) -> bool:
        privacy_level = self._privacy_level(memory)

        if privacy_level == "public":
            return True

        if privacy_level == "shared":
            return context_mode == "private" or self._has_related_person_present(
                memory,
                present_people,
            )

        if privacy_level == "private":
            return context_mode == "private"

        if privacy_level == "sensitive":
            # Sensitive memories need a stricter future relevance check before use.
            return False

        return False

    def sanitize(self, message: str) -> str:
        return message.strip()

    def get_effective_context_mode(
        self,
        context_mode: str,
        present_people: list[str],
        scene_context: str | None,
    ) -> str:
        if context_mode != "private":
            return context_mode
        if present_people:
            return "friends_present"
        if self._scene_implies_others_present(scene_context):
            return "unknown_people_present"
        return "private"

    def _privacy_note(self, memory, context_mode: str, present_people: list[str]) -> str | None:
        privacy_level = self._privacy_level(memory)

        if privacy_level == "private" and context_mode != "private":
            return "Private memory hidden because other people may be present."

        if privacy_level == "sensitive":
            if context_mode == "private":
                return "Sensitive memory held back unless directly relevant and requested."
            return "Sensitive memory not used in public context."

        if privacy_level == "shared":
            if context_mode == "private":
                return None
            if self._has_related_person_present(memory, present_people):
                return "Shared memory allowed because related person is present."
            return "Shared memory hidden because related person is not present."

        return None

    def _privacy_level(self, memory) -> str:
        return getattr(memory, "privacy_level", "private")

    def _has_related_person_present(self, memory, present_people: list[str]) -> bool:
        related_people = getattr(memory, "related_people", None) or []
        normalized_present = {person.strip().lower() for person in present_people if person.strip()}

        return any(
            isinstance(person, str) and person.strip().lower() in normalized_present
            for person in related_people
        )

    def _scene_implies_others_present(self, scene_context: str | None) -> bool:
        if not scene_context:
            return False

        normalized_scene = scene_context.lower()
        private_cues = {"alone", "by myself", "tek basima", "room alone"}
        other_present_cues = {
            "nearby",
            "public",
            "family",
            "friend",
            "friends",
            "dinner",
            "call",
            "meeting",
            "school",
            "office",
            "cafe",
            "restaurant",
            "crowd",
            "people",
        }

        if any(cue in normalized_scene for cue in private_cues):
            return False
        return any(cue in normalized_scene for cue in other_present_cues)


privacy_service = PrivacyService()
