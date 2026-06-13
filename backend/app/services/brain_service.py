import json
import uuid
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.persona import DEFAULT_PERSONA
from app.db.models import Conversation, Message, RobotAction, User
from app.ml.inference.turkish_brain_router import turkish_brain_router
from app.schemas.chat import ChatRequest, ChatResponse, RobotState
from app.services.emotion_service import emotion_service
from app.services.memory_service import memory_service
from app.services.openai_service import openai_service
from app.services.privacy_service import privacy_service
from app.services.safety_service import safety_service
from app.services.social_graph_service import social_graph_service
from app.services.training_data_service import training_data_service


class BrainService:
    def process_chat(self, db: Session, request: ChatRequest) -> ChatResponse:
        user_message = privacy_service.sanitize(request.message)
        present_people = request.present_people or []
        brain_state = turkish_brain_router.predict_brain_state(
            user_message,
            {
                "context_mode": request.context_mode,
                "present_people": present_people,
                "scene_context": request.scene_context,
                "companion_name": request.companion_name,
            },
        )

        user = self._ensure_user(db, request.user_id)
        conversation = self._ensure_conversation(db, request.conversation_id, user.id)
        if brain_state.get("route") == "privacy_boundary":
            return self._process_privacy_boundary_chat(db, conversation.id, user.id, brain_state)

        self._save_message(db, conversation.id, "user", user_message)
        self._commit(db)

        emotion_result = emotion_service.analyze_user_message(user_message)
        emotion_result["turkish_brain"] = {
            "route": brain_state.get("route"),
            "emotion": brain_state.get("emotion"),
            "need": brain_state.get("need"),
            "tone": brain_state.get("tone"),
            "style": brain_state.get("style"),
            "memory_allowed": brain_state.get("memory_allowed"),
        }
        relevant_memories = memory_service.retrieve_relevant_memories(
            db=db,
            user_id=user.id,
            message=user_message,
        )
        allowed_memories, privacy_notes = privacy_service.filter_memories_for_context(
            relevant_memories,
            request.context_mode,
            present_people,
            request.scene_context,
        )
        memories_context = memory_service.format_memories_for_prompt(allowed_memories)
        people_context = social_graph_service.get_people_context(db, user.id, present_people)

        ai_response = openai_service.generate_json_response(
            system_prompt=self._build_system_prompt(
                emotion_result=emotion_result,
                memories_context=memories_context,
                people_context=people_context,
                privacy_notes=privacy_notes,
                context_mode=request.context_mode,
                effective_context_mode=privacy_service.get_effective_context_mode(
                    request.context_mode,
                    present_people,
                    request.scene_context,
                ),
                present_people=present_people,
                scene_context=request.scene_context,
                companion_name=request.companion_name,
                brain_state=brain_state,
            ),
            user_prompt=user_message,
        )
        speech, robot_state, ai_privacy_notes = self._validate_ai_response(
            ai_response,
            emotion_result,
            brain_state.get("robot_state"),
        )
        ai_response["brain_state"] = brain_state
        all_privacy_notes = self._dedupe_notes([*privacy_notes, *ai_privacy_notes])
        if not brain_state.get("memory_allowed", True):
            all_privacy_notes = self._dedupe_notes(
                [*all_privacy_notes, "Turkish brain memory policy: memory updates disabled."]
            )
        safety_result = safety_service.analyze_safety(
            user_message=user_message,
            draft_response=speech,
            context_mode=privacy_service.get_effective_context_mode(
                request.context_mode,
                present_people,
                request.scene_context,
            ),
        )
        if not safety_result["allowed"] and safety_result.get("safe_response_override"):
            speech = safety_result["safe_response_override"]
            ai_response["speech"] = speech
            ai_response["safety"] = safety_result
            all_privacy_notes = self._dedupe_notes(
                [*all_privacy_notes, f"Safety override: {safety_result['reason']}"]
            )

        self._save_message(db, conversation.id, "assistant", speech)

        social_graph = {"people": [], "relationships": [], "events": []}
        saved_memory_updates = []
        if safety_result["risk_level"] != "high" and brain_state.get("memory_allowed", True):
            memory_updates = memory_service.extract_memory_updates(
                user_message=user_message,
                assistant_speech=speech,
                emotion_result=emotion_result,
            )
            social_graph = social_graph_service.extract_people_and_relationships(user_message)
            social_graph_service.save_social_graph(db, user.id, social_graph)
            saved_memories = memory_service.save_memories(db, user.id, memory_updates)
            saved_memory_updates = [
                {
                    "type": memory.memory_type,
                    "content": memory.content,
                    "importance": memory.importance,
                    "privacy": memory.privacy_level,
                    "related_people": memory.related_people,
                }
                for memory in saved_memories
            ]

        self._save_robot_action(db, user.id, conversation.id, robot_state, ai_response)
        self._commit(db)
        self._record_training_examples(
            db=db,
            user_id=user.id,
            user_message=user_message,
            assistant_speech=speech,
            emotion_result=emotion_result,
            memory_updates=saved_memory_updates,
            privacy_notes=all_privacy_notes,
            social_graph=social_graph,
            robot_state=robot_state,
            request=request,
        )

        return ChatResponse(
            conversation_id=str(conversation.id),
            message=user_message,
            reply=speech,
            brain_state=brain_state,
            speech=speech,
            robot_state=robot_state,
            memory_updates=saved_memory_updates,
            privacy_notes=all_privacy_notes,
            used_memories=[memory.content for memory in allowed_memories],
        )

    def _process_privacy_boundary_chat(
        self,
        db: Session,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        brain_state: dict[str, Any],
    ) -> ChatResponse:
        speech = "Tamam, bunu kaydetmeyeceğim. İçeriği saklamadan kısa cevap vereceğim."
        robot_state = self._robot_state_from_brain_state(brain_state)
        raw_response = {
            "speech": speech,
            "robot_state": robot_state.model_dump(),
            "privacy_notes": ["Privacy boundary matched; user content was not stored."],
            "brain_state": brain_state,
        }

        self._save_message(db, conversation_id, "user", "[privacy_boundary_message_omitted]")
        self._save_message(db, conversation_id, "assistant", speech)
        self._save_robot_action(db, user_id, conversation_id, robot_state, raw_response)
        self._commit(db)

        return ChatResponse(
            conversation_id=str(conversation_id),
            message="[privacy_boundary_message_omitted]",
            reply=speech,
            brain_state=brain_state,
            speech=speech,
            robot_state=robot_state,
            memory_updates=[],
            privacy_notes=["Privacy boundary matched; memory updates disabled."],
            used_memories=[],
        )

    def _record_training_examples(
        self,
        db: Session,
        user_id: uuid.UUID,
        user_message: str,
        assistant_speech: str,
        emotion_result: dict[str, Any],
        memory_updates: list[dict[str, Any]],
        privacy_notes: list[str],
        social_graph: dict[str, list[dict[str, Any]]],
        robot_state: RobotState,
        request: ChatRequest,
    ) -> None:
        try:
            training_data_service.record_chat_examples(
                db=db,
                user_id=user_id,
                user_message=user_message,
                assistant_speech=assistant_speech,
                emotion_result=emotion_result,
                memory_updates=memory_updates,
                privacy_notes=privacy_notes,
                social_graph=social_graph,
                robot_state=robot_state.model_dump(),
                context={
                    "context_mode": request.context_mode,
                    "present_people": request.present_people or [],
                    "scene_context": request.scene_context,
                },
            )
        except SQLAlchemyError:
            db.rollback()

    def _ensure_user(self, db: Session, user_id: str | None) -> User:
        parsed_user_id = self._parse_uuid(user_id)
        if parsed_user_id is not None:
            existing_user = db.get(User, parsed_user_id)
            if existing_user is not None:
                return existing_user

        user = User(id=parsed_user_id or uuid.uuid4(), display_name="Default User")
        db.add(user)
        db.flush()
        return user

    def _ensure_conversation(
        self,
        db: Session,
        conversation_id: str | None,
        user_id: uuid.UUID,
    ) -> Conversation:
        parsed_conversation_id = self._parse_uuid(conversation_id)
        if parsed_conversation_id is not None:
            existing_conversation = db.get(Conversation, parsed_conversation_id)
            if existing_conversation is not None and existing_conversation.user_id == user_id:
                return existing_conversation
            if existing_conversation is not None:
                parsed_conversation_id = None

        conversation = Conversation(
            id=parsed_conversation_id or uuid.uuid4(),
            user_id=user_id,
        )
        db.add(conversation)
        db.flush()
        return conversation

    def _save_message(
        self,
        db: Session,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
    ) -> Message:
        message = Message(conversation_id=conversation_id, role=role, content=content)
        db.add(message)
        db.flush()
        return message

    def _save_robot_action(
        self,
        db: Session,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        robot_state: RobotState,
        raw_json: dict[str, Any],
    ) -> RobotAction:
        robot_action = RobotAction(
            user_id=user_id,
            conversation_id=conversation_id,
            emotion=robot_state.emotion,
            face=robot_state.face,
            eyes=robot_state.eyes,
            mouth=robot_state.mouth,
            voice_tone=robot_state.voice_tone,
            body_action=robot_state.body_action,
            head_motion=robot_state.head_motion,
            eye_contact=robot_state.eye_contact,
            movement_intensity=robot_state.movement_intensity,
            should_speak=robot_state.should_speak,
            raw_json=raw_json,
        )
        db.add(robot_action)
        db.flush()
        return robot_action

    def _build_system_prompt(
        self,
        emotion_result: dict[str, Any],
        memories_context: str,
        people_context: str,
        privacy_notes: list[str],
        context_mode: str,
        effective_context_mode: str,
        present_people: list[str],
        scene_context: str | None,
        companion_name: str | None,
        brain_state: dict[str, Any] | None = None,
    ) -> str:
        persona_name = self._string_or_default(companion_name, DEFAULT_PERSONA["name"])
        brain_guidance = json.dumps(brain_state or {}, ensure_ascii=False)
        return (
            f"You are {persona_name}, a socially-aware embodied AI companion.\n"
            "You are not just a chatbot. You have continuity, memory, emotional "
            "awareness, and future robot embodiment.\n"
            f"Persona style: {DEFAULT_PERSONA['style']}.\n"
            f"Persona boundaries:\n{self._format_prompt_list(DEFAULT_PERSONA['boundaries'])}\n"
            f"Persona behavior:\n{self._format_prompt_list(DEFAULT_PERSONA['behavior'])}\n"
            "If a companion_name was provided, use that identity naturally in speech, "
            "but do not repeat the name excessively.\n"
            "You must be warm, direct, emotionally intelligent, and privacy-safe.\n"
            "You must adapt tone to user's emotional state.\n"
            "You must not reveal private/sensitive memories when other people are present.\n"
            "You must ask permission before permanently remembering third-party "
            "information if uncertain.\n"
            "When a new person is mentioned, do not sound repetitive, but you may "
            "naturally ask for consent before remembering more than basic name and "
            "relationship, for example: "
            "\"Ali'yi hafizama basitce arkadasin olarak kaydedeyim mi?\"\n"
            "If someone says not to remember a person, respect that and avoid storing "
            "future memories about that person.\n"
            "If scene context implies others are present, act privacy-safe even when "
            "context_mode says private.\n"
            "If present_people is empty but context_mode is public or "
            "unknown_people_present, avoid private memories.\n"
            "If a known person is present, use only shared/public information related "
            "to that person.\n"
            "You must return JSON only.\n"
            "speech should sound natural, not robotic.\n"
            "Do not mention internal implementation.\n"
            "Do not pretend to be human.\n"
            "Do not claim certainty about emotions; use soft language.\n\n"
            "Return this exact JSON shape:\n"
            "{\n"
            '  "speech": "...",\n'
            '  "robot_state": {\n'
            '    "emotion": "...",\n'
            '    "face": "...",\n'
            '    "eyes": "...",\n'
            '    "mouth": "...",\n'
            '    "voice_tone": "...",\n'
            '    "body_action": "...",\n'
            '    "head_motion": "...",\n'
            '    "eye_contact": "...",\n'
            '    "movement_intensity": "...",\n'
            '    "should_speak": true\n'
            "  },\n"
            '  "privacy_notes": ["..."]\n'
            "}\n\n"
            "Allowed robot_state examples:\n"
            "emotion: neutral, focused, concerned, playful, excited, calm, serious\n"
            "face: neutral, focused, soft_concerned, happy, serious, playful\n"
            "eyes: center, narrow, soft, wide, looking_left, looking_right\n"
            "mouth: neutral, smile, small_smile, flat, open\n"
            "voice_tone: calm, calm_confident, energetic, soft, serious, playful\n"
            "body_action: look_at_user, slight_head_tilt, small_nod, stay_still, idle\n"
            "head_motion: none, tilt_left, tilt_right, nod_once\n"
            "eye_contact: low, medium, high\n"
            "movement_intensity: low, medium, high\n\n"
            f"Context mode: {context_mode}\n"
            f"Effective privacy context: {effective_context_mode}\n"
            f"Scene context: {scene_context or 'not provided'}\n"
            f"Companion name: {persona_name}\n"
            f"Present people: {present_people or 'none'}\n"
            f"Emotion analysis: {emotion_result}\n"
            f"Turkish v3 brain guidance: {brain_guidance}\n"
            f"Allowed memory context:\n{memories_context}\n\n"
            f"People context:\n{people_context}\n\n"
            f"Privacy notes to respect:\n{privacy_notes or 'none'}"
        )

    def _validate_ai_response(
        self,
        response: dict[str, Any],
        emotion_result: dict[str, Any],
        fallback_robot_state_data: dict[str, Any] | None = None,
    ) -> tuple[str, RobotState, list[str]]:
        fallback_robot_state = self._robot_state_from_dict(
            fallback_robot_state_data,
            default_emotion=str(emotion_result.get("emotion", "neutral")),
            default_face="neutral",
            default_mouth="small_smile",
            default_voice_tone="calm",
            default_body_action="idle",
        )

        speech = response.get("speech")
        if not isinstance(speech, str) or not speech.strip():
            speech = "I hear you. Could you tell me a little more?"

        robot_state_data = response.get("robot_state")
        if isinstance(robot_state_data, dict):
            robot_state = self._robot_state_from_dict(
                robot_state_data,
                default_emotion=fallback_robot_state.emotion,
                default_face=fallback_robot_state.face,
                default_eyes=fallback_robot_state.eyes,
                default_mouth=fallback_robot_state.mouth,
                default_voice_tone=fallback_robot_state.voice_tone,
                default_body_action=fallback_robot_state.body_action,
                default_head_motion=fallback_robot_state.head_motion,
                default_eye_contact=fallback_robot_state.eye_contact,
                default_movement_intensity=fallback_robot_state.movement_intensity,
                default_should_speak=fallback_robot_state.should_speak,
            )
        else:
            robot_state = fallback_robot_state

        privacy_notes = response.get("privacy_notes")
        if not isinstance(privacy_notes, list):
            privacy_notes = []

        return (
            speech.strip(),
            robot_state,
            [note for note in privacy_notes if isinstance(note, str) and note.strip()],
        )

    def _robot_state_from_brain_state(self, brain_state: dict[str, Any]) -> RobotState:
        robot_state_data = brain_state.get("robot_state")
        if not isinstance(robot_state_data, dict):
            robot_state_data = {}

        return self._robot_state_from_dict(
            robot_state_data,
            default_emotion=str(brain_state.get("emotion", "neutral")),
            default_face="focused",
            default_mouth="neutral",
            default_voice_tone=str(brain_state.get("tone", "calm")),
            default_body_action="look_at_user",
        )

    def _robot_state_from_dict(
        self,
        robot_state_data: dict[str, Any] | None,
        default_emotion: str = "neutral",
        default_face: str = "neutral",
        default_eyes: str = "center",
        default_mouth: str = "neutral",
        default_voice_tone: str = "calm",
        default_body_action: str = "look_at_user",
        default_head_motion: str = "none",
        default_eye_contact: str = "medium",
        default_movement_intensity: str = "low",
        default_should_speak: bool = True,
    ) -> RobotState:
        data = robot_state_data or {}
        return RobotState(
            emotion=self._string_or_default(data.get("emotion"), default_emotion),
            face=self._string_or_default(data.get("face"), default_face),
            eyes=self._string_or_default(data.get("eyes"), default_eyes),
            mouth=self._string_or_default(data.get("mouth"), default_mouth),
            voice_tone=self._string_or_default(data.get("voice_tone"), default_voice_tone),
            body_action=self._string_or_default(data.get("body_action"), default_body_action),
            head_motion=self._string_or_default(data.get("head_motion"), default_head_motion),
            eye_contact=self._string_or_default(data.get("eye_contact"), default_eye_contact),
            movement_intensity=self._string_or_default(
                data.get("movement_intensity"),
                default_movement_intensity,
            ),
            should_speak=self._bool_or_default(data.get("should_speak"), default_should_speak),
        )

    def _commit(self, db: Session) -> None:
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise

    def _parse_uuid(self, value: str | None) -> uuid.UUID | None:
        if value is None:
            return None
        try:
            return uuid.UUID(value)
        except ValueError:
            return None

    def _string_or_default(self, value: Any, default: str) -> str:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return default

    def _bool_or_default(self, value: Any, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        return default

    def _format_prompt_list(self, values: list[str]) -> str:
        return "\n".join(f"- {value}" for value in values)

    def _dedupe_notes(self, notes: list[str]) -> list[str]:
        deduped = []
        seen = set()
        for note in notes:
            if not note or note in seen:
                continue
            deduped.append(note)
            seen.add(note)
        return deduped


brain_service = BrainService()
