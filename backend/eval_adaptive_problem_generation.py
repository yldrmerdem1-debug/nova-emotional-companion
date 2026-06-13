from pathlib import Path
from tempfile import TemporaryDirectory

from app.services.curriculum_engine_service import curriculum_engine_service
from app.services.self_training_service import self_training_service
from app.services.verifier_service import verifier_service
from app.services.world_model_service import world_model_service


def main() -> None:
    failures = []
    original_path = self_training_service.store_path

    with TemporaryDirectory() as temp_dir:
        self_training_service.store_path = Path(temp_dir) / "self_training.jsonl"

        for domain in ("cpp", "python", "java", "math", "physics", "algorithms"):
            result = self_training_service.run_cycle(domain, difficulty=4)
            record = result["record"]
            problem = record["problem"]
            verification = verifier_service.verify_training_record(record)

            if problem.get("source") != "adaptive_generated":
                failures.append((f"adaptive_source_{domain}", problem))
            if not problem.get("olympiad_style"):
                failures.append((f"olympiad_flag_{domain}", problem))
            if problem.get("training_stage") != "olympiad_preparation":
                failures.append((f"training_stage_{domain}", problem))
            if not record.get("check", {}).get("passed"):
                failures.append((f"adaptive_check_{domain}", record))
            if not verification.get("verified"):
                failures.append((f"adaptive_verification_{domain}", verification))

        world_model = world_model_service.build_world_model()
        curriculum = curriculum_engine_service.build_plan(world_model, cycles=12)
        domains = {task.get("domain") for task in curriculum.get("schedule", [])}
        expected_domains = {"cpp", "python", "java", "math", "physics", "algorithms"}
        if not expected_domains.issubset(domains):
            failures.append(("curriculum_domains_missing", curriculum))
        if not all("stage" in task for task in curriculum.get("schedule", [])):
            failures.append(("curriculum_stage_missing", curriculum))
        if max(int(task.get("difficulty", 1)) for task in curriculum.get("schedule", [])) < 4:
            failures.append(("curriculum_not_ramping", curriculum))

    self_training_service.store_path = original_path

    if failures:
        for name, details in failures:
            print(f"FAIL {name}: {details}")
        raise SystemExit(1)

    print("adaptive_problem_generation_eval_failed=0")


if __name__ == "__main__":
    main()
