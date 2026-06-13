from pathlib import Path
from tempfile import TemporaryDirectory

from app.ml.inference.turkish_brain_router import turkish_brain_router
from app.services.knowledge_base_service import knowledge_base_service
from app.services.self_training_service import self_training_service


def main() -> None:
    failures = []

    cpp_state = turkish_brain_router.predict_brain_state("C++ move semantics std::move anlat")
    cpp_knowledge = knowledge_base_service.retrieve("C++ move semantics std::move anlat", cpp_state, limit=5)
    cpp_ids = {item.get("id") for item in cpp_knowledge}
    if "cpp_move_semantics" not in cpp_ids:
        failures.append(("cpp_move_knowledge", cpp_ids))

    algo_knowledge = knowledge_base_service.retrieve(
        "dynamic programming state transition memoization",
        {"route": "code_tutor", "need": "debug_or_explain"},
        limit=5,
    )
    algo_ids = {item.get("id") for item in algo_knowledge}
    if "algo_dynamic_programming_core" not in algo_ids:
        failures.append(("dp_knowledge", algo_ids))

    original_path = self_training_service.store_path
    with TemporaryDirectory() as temp_dir:
        self_training_service.store_path = Path(temp_dir) / "self_training.jsonl"
        for domain in ("cpp", "math", "algorithms"):
            for _ in range(4):
                result = self_training_service.run_cycle(domain)
                if not result["record"]["check"]["passed"]:
                    failures.append((f"{domain}_cycle_failed", result))
            progress = self_training_service.progress(domain)
            if progress.get("bank_count", 0) < 4:
                failures.append((f"{domain}_bank_count", progress))
            if progress.get("total") != 4:
                failures.append((f"{domain}_progress_total", progress))
    self_training_service.store_path = original_path

    if failures:
        for name, details in failures:
            print(f"FAIL {name}: {details}")
        raise SystemExit(1)

    print("emperor_learning_pack_eval_failed=0")


if __name__ == "__main__":
    main()
