from pathlib import Path
from tempfile import TemporaryDirectory

from app.services.deep_memory_service import DeepMemoryService
from app.services.response_generation_service import ResponseGenerationService


BASE_BRAIN = {
    "route": "general_chat",
    "emotion": "neutral",
    "need": "clarification",
    "tone": "calm",
    "style": "natural_casual",
    "memory_allowed": True,
    "robot_state": {},
    "model_version": "turkish_v3",
    "loaded_models": [],
}


def main() -> None:
    failures = []
    with TemporaryDirectory() as temp_dir:
        memory = DeepMemoryService()
        memory.store_path = Path(temp_dir) / "deep_memory_store.jsonl"
        response_service = ResponseGenerationService()

        result = memory.process_message("bana reis de kanka deme", BASE_BRAIN)
        if len(result["saved_memories"]) < 2:
            failures.append("preferred and avoided address not saved")

        context = memory.process_message("nasılsın", BASE_BRAIN)
        reply = response_service.generate_reply("nasılsın", BASE_BRAIN, {"deep_memory": context})["reply"]
        if "reis" not in reply or "kanka" in reply:
            failures.append(f"address personalization failed: {reply}")

        memory.process_message("kısa ve net ol uzatma", BASE_BRAIN)
        context = memory.process_message("C++ hata verdi önce neye bakayım", BASE_BRAIN)
        reply = response_service.generate_reply(
            "C++ hata verdi önce neye bakayım",
            {**BASE_BRAIN, "route": "code_tutor"},
            {"deep_memory": context},
        )["reply"]
        if len(reply) > 160:
            failures.append(f"short_direct personalization failed: {reply}")

        memory.process_message("C++ öğreniyorum pointerlarda zorlanıyorum", BASE_BRAIN)
        context = memory.process_message("beni tanıyor musun", BASE_BRAIN)
        reply = response_service.generate_reply("beni tanıyor musun", BASE_BRAIN, {"deep_memory": context})["reply"]
        if "cpp" not in reply.casefold() and "c++" not in reply.casefold():
            failures.append(f"profile reflection missed learning profile: {reply}")

        private_brain = {**BASE_BRAIN, "memory_allowed": False}
        before_count = len(memory.list_recent())
        memory.process_message("bugün kötüyüm ama bunu hafızaya alma", private_brain)
        after_count = len(memory.list_recent())
        if before_count != after_count:
            failures.append("memory was saved despite memory_allowed=false")

        memory.process_message("küçük detay aklımda tut mavi defteri seviyorum", BASE_BRAIN)
        if not any(record.get("memory_type") == "tiny_detail" for record in memory.list_recent()):
            failures.append("tiny detail was not saved")

    print(f"deep_memory_eval_failed={len(failures)}")
    for failure in failures:
        print(failure)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
