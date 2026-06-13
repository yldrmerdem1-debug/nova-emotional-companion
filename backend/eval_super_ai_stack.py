from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference.turkish_brain_router import turkish_brain_router
from app.services.fine_tune_dataset_service import fine_tune_dataset_service
from app.services.knowledge_base_service import knowledge_base_service
from app.services.local_llm_service import local_llm_service
from app.services.long_context_memory_service import long_context_memory_service
from app.services.tool_diagnostic_service import tool_diagnostic_service


def main() -> None:
    failures = []

    llm_health = local_llm_service.health()
    if "status" not in llm_health:
        failures.append(("local_llm_health", llm_health))

    brain_state = turkish_brain_router.predict_brain_state("C++ pointer array compile hatası")
    knowledge = knowledge_base_service.retrieve("C++ pointer array compile hatası", brain_state)
    if not knowledge:
        failures.append(("semantic_knowledge_empty", knowledge))
    else:
        first = knowledge[0]
        if "retrieval" not in first:
            failures.append(("knowledge_retrieval_meta", first))
        if "verification" not in first:
            failures.append(("knowledge_verification_meta", first))

    diagnostic = tool_diagnostic_service.inspect_project()
    if diagnostic.get("health_score", {}).get("score", 0) <= 0:
        failures.append(("tool_diagnostic_health", diagnostic))

    original_long_path = long_context_memory_service.store_path
    original_export_dir = fine_tune_dataset_service.export_dir
    original_data_dir = fine_tune_dataset_service.data_dir
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        long_context_memory_service.store_path = temp_path / "long_context.jsonl"
        fine_tune_dataset_service.data_dir = temp_path
        fine_tune_dataset_service.export_dir = temp_path / "generated"
        (temp_path / "response_training_corpus.jsonl").write_text(
            '{"user_message":"selam","robot_reply":"Selam kral.","rating":"good"}\n'
            '{"user_message":"hata","robot_reply":"Yanlış","ideal_reply":"Doğru cevap","rating":"bad"}\n',
            encoding="utf-8",
        )
        (temp_path / "deep_memory_store.jsonl").write_text(
            '{"evidence":"bana kral de","memory_type":"communication_preference","key":"preferred_address","brain_route":"style_adaptation"}\n',
            encoding="utf-8",
        )
        (temp_path / "learning_loop_store.jsonl").write_text(
            '{"evidence":"C++ pointer öğreniyorum","record_type":"exchange_trace","topic":"cpp"}\n',
            encoding="utf-8",
        )

        saved = long_context_memory_service.record_exchange(
            "C++ pointer öğreniyorum",
            "Pointer adres tutar.",
            brain_state,
            {"saved_memories": []},
            {"emotional_summary": {"dominant_mood": "neutral"}},
            {"layers": {"long_term_user_goal": "C++ öğrenmek"}, "should_expand_answer": False},
        )
        if not saved.get("saved"):
            failures.append(("long_context_saved", saved))
        if saved.get("summary", {}).get("conversation_count") != 1:
            failures.append(("long_context_summary", saved))

        exported = fine_tune_dataset_service.export_datasets()
        counts = exported.get("counts", {})
        if counts.get("local_llm_finetune", 0) < 2:
            failures.append(("finetune_export_response_count", exported))
        if counts.get("response_preference_pairs", 0) < 1:
            failures.append(("finetune_export_preference_count", exported))
        if counts.get("brain_meta_training", 0) < 2:
            failures.append(("finetune_export_brain_count", exported))

    long_context_memory_service.store_path = original_long_path
    fine_tune_dataset_service.export_dir = original_export_dir
    fine_tune_dataset_service.data_dir = original_data_dir

    client = TestClient(app)
    response = client.get("/debug/local-ai-stack")
    if response.status_code != 200:
        failures.append(("debug_local_ai_stack_status", response.status_code))
    else:
        data = response.json()
        for key in ("local_llm", "project", "training_export", "long_context"):
            if key not in data:
                failures.append((f"debug_missing_{key}", data.keys()))

    if failures:
        for name, details in failures:
            print(f"FAIL {name}: {details}")
        raise SystemExit(1)

    print("super_ai_stack_eval_failed=0")


if __name__ == "__main__":
    main()
