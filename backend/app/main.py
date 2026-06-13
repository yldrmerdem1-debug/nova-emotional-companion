from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import settings
from app.db import models  # noqa: F401
from app.db.database import Base, engine
from app.ml.inference.turkish_brain_router import turkish_brain_router
from app.routers import chat, debug_brain, robot, training, voice
from app.services.ai_mentor_service import ai_mentor_service
from app.services.curiosity_engine_service import curiosity_engine_service
from app.services.curriculum_engine_service import curriculum_engine_service
from app.services.deep_memory_service import deep_memory_service
from app.services.emotional_memory_service import emotional_memory_service
from app.services.fine_tune_dataset_service import fine_tune_dataset_service
from app.services.knowledge_base_service import knowledge_base_service
from app.services.learning_loop_service import learning_loop_service
from app.services.local_llm_service import local_llm_service
from app.services.long_context_memory_service import long_context_memory_service
from app.services.mind.global_workspace_service import global_workspace_service
from app.services.reasoning_planner_service import reasoning_planner_service
from app.services.reflection_engine_service import reflection_engine_service
from app.services.response_generation_service import response_generation_service
from app.services.safety_service import safety_service
from app.services.self_training_service import self_training_service
from app.services.solution_synthesizer_service import solution_synthesizer_service
from app.services.tool_diagnostic_service import tool_diagnostic_service
from app.services.training_readiness_service import training_readiness_service
from app.services.verifier_service import verifier_service
from app.services.vocabulary_style_service import vocabulary_style_service
from app.services.world_model_service import world_model_service

app = FastAPI(title=f"{settings.app_name} API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(robot.router, prefix="/api")
app.include_router(training.router, prefix="/api")
app.include_router(voice.router, prefix="/api")
app.include_router(voice.router)
app.include_router(debug_brain.router)


def create_all() -> None:
    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(bind=connection)
        if engine.dialect.name == "postgresql":
            connection.execute(
                text(
                    "ALTER TABLE memories "
                    "ADD COLUMN IF NOT EXISTS archived BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
            connection.execute(
                text(
                    "ALTER TABLE people "
                    "ADD COLUMN IF NOT EXISTS consent_status "
                    "VARCHAR(64) NOT NULL DEFAULT 'unknown'"
                )
            )
            robot_action_columns = {
                "eyes": "VARCHAR(255) NOT NULL DEFAULT 'center'",
                "mouth": "VARCHAR(255) NOT NULL DEFAULT 'small_smile'",
                "head_motion": "VARCHAR(255) NOT NULL DEFAULT 'none'",
                "eye_contact": "VARCHAR(255) NOT NULL DEFAULT 'medium'",
                "movement_intensity": "VARCHAR(255) NOT NULL DEFAULT 'low'",
                "should_speak": "BOOLEAN NOT NULL DEFAULT TRUE",
            }
            for column_name, column_definition in robot_action_columns.items():
                connection.execute(
                    text(
                        f"ALTER TABLE robot_actions ADD COLUMN IF NOT EXISTS "
                        f"{column_name} {column_definition}"
                    )
                )


@app.on_event("startup")
def on_startup() -> None:
    try:
        create_all()
    except Exception as exc:
        print(f"Database startup skipped: {exc}")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


class SimpleChatRequest(BaseModel):
    message: str
    support_mode: str = "listen"


def apply_support_mode(brain_state: dict, support_mode: str) -> dict:
    normalized_mode = support_mode if support_mode in {"listen", "think", "brief"} else "listen"
    updated = dict(brain_state)
    robot_state = dict(updated.get("robot_state", {}))

    if normalized_mode == "listen" and updated.get("route") not in {"code_tutor", "scientific_tutor"}:
        updated["route"] = "emotional_support"
        updated["need"] = "listen"
        updated["tone"] = "soft"
        updated["style"] = "calm_supportive"
        robot_state.update(
            {
                "emotion": "calm",
                "face": "concerned",
                "eyes": "soft",
                "mouth": "neutral",
                "voice_tone": "soft",
                "body_action": "look_at_user",
                "movement_intensity": "low",
            }
        )
    elif normalized_mode == "think":
        updated["need"] = "reflect_then_small_step"
        updated["tone"] = "calm"
        updated["style"] = "supportive_reflection"
    elif normalized_mode == "brief":
        updated["need"] = "brief_presence"
        updated["tone"] = "plain_direct"
        updated["style"] = "short_supportive"

    updated["support_mode"] = normalized_mode
    updated["robot_state"] = robot_state
    return updated


@app.post("/chat")
def simple_chat(request: SimpleChatRequest) -> dict:
    support_mode = request.support_mode if request.support_mode in {"listen", "think", "brief"} else "listen"
    profile_summary = deep_memory_service.build_profile_summary()
    try:
        brain_state = turkish_brain_router.predict_brain_state(
            request.message,
            context={"profile_summary": profile_summary},
        )
    except Exception:
        brain_state = {
            "route": "general_chat",
            "emotion": "neutral",
            "need": "clarification",
            "tone": "calm",
            "style": "default",
            "memory_allowed": True,
            "robot_state": {
                "emotion": "neutral",
                "face": "focused",
                "eyes": "center",
                "mouth": "neutral",
                "voice_tone": "calm",
                "body_action": "look_at_user",
                "head_motion": "none",
                "eye_contact": "medium",
                "movement_intensity": "low",
                "should_speak": True,
            },
            "model_version": "turkish_v3",
            "loaded_models": [],
            "brain_meta": {
                "version": "fallback",
                "confidence": 0.5,
                "risk_flags": ["router_exception"],
                "decisions": ["fallback_brain_state"],
                "needs_clarification": True,
            },
        }

    brain_state = apply_support_mode(brain_state, support_mode)
    memory_context = deep_memory_service.process_message(request.message, brain_state)
    emotional_context = emotional_memory_service.process_message(request.message, brain_state)
    knowledge_context = knowledge_base_service.retrieve(request.message, brain_state)
    reasoning_plan = reasoning_planner_service.build_plan(
        request.message,
        brain_state,
        memories=memory_context,
        knowledge=knowledge_context,
    )
    synthesis = solution_synthesizer_service.synthesize(
        request.message,
        brain_state,
        memory_context,
        knowledge_context,
        reasoning_plan,
    )
    reflection = reflection_engine_service.reflect(
        request.message,
        brain_state,
        memory_context,
        emotional_context,
        knowledge_context,
        reasoning_plan,
    )
    long_context_summary = long_context_memory_service.build_context_summary()
    world_model = world_model_service.build_world_model()
    response = response_generation_service.generate_reply(
        request.message,
        brain_state,
        context={
            "support_mode": support_mode,
            "deep_memory": memory_context,
            "emotional_memory": emotional_context,
            "knowledge": knowledge_context,
            "reasoning_plan": reasoning_plan,
            "synthesis": synthesis,
            "reflection": reflection,
            "long_context": {"summary": long_context_summary},
            "world_model": world_model,
        },
    )
    learning_context = learning_loop_service.process_exchange(
        request.message,
        response["reply"],
        brain_state,
        memory_context,
        knowledge_context,
        reasoning_plan,
    )
    curiosity = curiosity_engine_service.generate_question(
        request.message,
        brain_state,
        memory_context,
        emotional_context,
        learning_context,
    )
    long_context = long_context_memory_service.record_exchange(
        request.message,
        response["reply"],
        brain_state,
        memory_context,
        emotional_context,
        reflection,
    )
    mind_workspace = global_workspace_service.integrate(
        {
            "message": request.message,
            "brain_state": brain_state,
            "memory_context": memory_context,
            "emotional_context": emotional_context,
            "knowledge_context": knowledge_context,
            "reasoning_plan": reasoning_plan,
            "synthesis": synthesis,
            "reflection": reflection,
            "response_meta": response["response_meta"],
            "learning_context": learning_context,
            "curiosity": curiosity,
            "long_context": long_context,
            "long_context_summary": long_context_summary,
            "world_model": world_model,
        }
    )
    reply = response["reply"]
    if curiosity.get("should_ask") and curiosity.get("question"):
        reply = f"{reply}\n\n{curiosity['question']}"
    safety = safety_service.analyze_safety(request.message, reply, "private")
    if not safety.get("allowed", True) and safety.get("safe_response_override"):
        reply = safety["safe_response_override"]
        response["response_meta"]["safety"] = safety
    return {
        "message": request.message,
        "reply": reply,
        "brain_state": brain_state,
        "robot_state": brain_state.get("robot_state", {}),
        "response_meta": response["response_meta"],
        "memory_context": memory_context,
        "emotional_context": emotional_context,
        "knowledge_context": knowledge_context,
        "reasoning_plan": reasoning_plan,
        "synthesis": synthesis,
        "reflection": reflection,
        "learning_context": learning_context,
        "long_context": long_context,
        "curiosity": curiosity,
        "mind_workspace": mind_workspace,
    }


@app.get("/debug/deep-memory")
def debug_deep_memory() -> dict:
    return {
        "profile_summary": deep_memory_service.build_profile_summary(),
        "memories": deep_memory_service.list_recent(limit=50),
        "emotional_summary": emotional_memory_service.build_emotional_summary(),
        "learning_summary": learning_loop_service.build_learning_summary(),
        "long_context_summary": long_context_memory_service.build_context_summary(),
    }


@app.get("/debug/local-ai-stack")
def debug_local_ai_stack() -> dict:
    return {
        "local_llm": local_llm_service.health(),
        "project": tool_diagnostic_service.inspect_project(),
        "training_export": fine_tune_dataset_service.export_datasets(),
        "long_context": long_context_memory_service.build_context_summary(),
        "self_training": {
            "cpp": self_training_service.progress("cpp"),
            "python": self_training_service.progress("python"),
            "java": self_training_service.progress("java"),
            "math": self_training_service.progress("math"),
            "physics": self_training_service.progress("physics"),
            "algorithms": self_training_service.progress("algorithms"),
        },
        "training_readiness": training_readiness_service.evaluate(["cpp", "python", "java", "math", "physics", "algorithms"]),
        "world_model": world_model_service.build_world_model(),
        "curriculum": curriculum_engine_service.build_plan(world_model_service.build_world_model(), cycles=6),
        "mind_architecture": "global_workspace_v1",
        "vocabulary": vocabulary_style_service.diagnostics(),
    }


class SelfTrainingRequest(BaseModel):
    domain: str = "cpp"
    difficulty: int | None = None
    force: bool = True


@app.post("/debug/self-training/run")
def debug_self_training_run(request: SelfTrainingRequest) -> dict:
    readiness = training_readiness_service.evaluate([request.domain])
    if not request.force and not readiness.get("ready_for_self_training"):
        return {
            "skipped": True,
            "reason": "domain_not_ready_for_self_training",
            "readiness": readiness,
        }
    result = self_training_service.run_cycle(request.domain, request.difficulty)
    result["readiness"] = readiness
    return result


@app.get("/debug/training-readiness")
def debug_training_readiness() -> dict:
    return training_readiness_service.evaluate(["cpp", "python", "java", "math", "physics", "algorithms"])


@app.get("/debug/world-model")
def debug_world_model() -> dict:
    world_model = world_model_service.build_world_model()
    return {
        "world_model": world_model,
        "curriculum": curriculum_engine_service.build_plan(world_model, cycles=8),
    }


@app.post("/debug/brain-training/run")
def debug_brain_training_run() -> dict:
    world_model = world_model_service.build_world_model()
    task = curriculum_engine_service.next_task(world_model)
    result = self_training_service.run_cycle(task["domain"], task["difficulty"])
    verification = verifier_service.verify_training_record(result["record"])
    mentor = ai_mentor_service.critique_training_record(result["record"], verification)
    return {
        "world_focus": world_model.get("next_best_focus"),
        "task": task,
        "training_result": result,
        "verification": verification,
        "mentor": mentor,
        "updated_world_model": world_model_service.build_world_model(),
    }
