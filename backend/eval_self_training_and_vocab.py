from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference.turkish_brain_router import turkish_brain_router
from app.services.fine_tune_dataset_service import fine_tune_dataset_service
from app.services.knowledge_base_service import knowledge_base_service
from app.services.self_training_service import self_training_service
from app.services.vocabulary_style_service import vocabulary_style_service


def main() -> None:
    failures = []

    brain_state = turkish_brain_router.predict_brain_state("C++ RAII unique_ptr memory anlat")
    knowledge = knowledge_base_service.retrieve("C++ RAII unique_ptr memory anlat", brain_state, limit=3)
    ids = {item.get("id") for item in knowledge}
    if "cpp_raii_memory" not in ids:
        failures.append(("advanced_knowledge_raii", ids))

    enriched = vocabulary_style_service.enrich_reply(
        "Pointer adres tutar ve sınır kontrolü gerekir.",
        brain_state,
        context={},
    )
    if not enriched["vocabulary_meta"].get("applied"):
        failures.append(("vocabulary_applied", enriched))
    if "Kod tarafında" not in enriched["reply"]:
        failures.append(("vocabulary_code_opener", enriched["reply"]))

    original_self_path = self_training_service.store_path
    original_data_dir = fine_tune_dataset_service.data_dir
    original_export_dir = fine_tune_dataset_service.export_dir
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        self_training_service.store_path = temp_path / "self_training.jsonl"
        fine_tune_dataset_service.data_dir = temp_path
        fine_tune_dataset_service.export_dir = temp_path / "generated"

        cpp_cycle = self_training_service.run_cycle("cpp")
        math_cycle = self_training_service.run_cycle("math")
        if not cpp_cycle["record"]["check"]["passed"]:
            failures.append(("cpp_cycle_passed", cpp_cycle))
        if not math_cycle["record"]["check"]["passed"]:
            failures.append(("math_cycle_passed", math_cycle))
        if self_training_service.progress("cpp").get("total") != 1:
            failures.append(("self_training_progress", self_training_service.progress("cpp")))

        (temp_path / "self_training_store.jsonl").write_text(
            "\n".join(
                [
                    self_training_service.store_path.read_text(encoding="utf-8"),
                ]
            ),
            encoding="utf-8",
        )
        exported = fine_tune_dataset_service.export_datasets()
        if exported.get("counts", {}).get("brain_meta_training", 0) < 2:
            failures.append(("self_training_export", exported))

    self_training_service.store_path = original_self_path
    fine_tune_dataset_service.data_dir = original_data_dir
    fine_tune_dataset_service.export_dir = original_export_dir

    client = TestClient(app)
    response = client.post("/debug/self-training/run", json={"domain": "cpp", "difficulty": 1})
    if response.status_code != 200:
        failures.append(("debug_self_training_status", response.status_code))
    else:
        data = response.json()
        if not data.get("record", {}).get("check", {}).get("passed"):
            failures.append(("debug_self_training_passed", data))

    if failures:
        for name, details in failures:
            print(f"FAIL {name}: {details}")
        raise SystemExit(1)

    print("self_training_vocab_eval_failed=0")


if __name__ == "__main__":
    main()
