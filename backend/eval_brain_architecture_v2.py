from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.main import app
from app.services.ai_mentor_service import ai_mentor_service
from app.services.curriculum_engine_service import curriculum_engine_service
from app.services.self_training_service import self_training_service
from app.services.verifier_service import verifier_service
from app.services.world_model_service import world_model_service


def main() -> None:
    failures = []
    original_path = self_training_service.store_path

    with TemporaryDirectory() as temp_dir:
        self_training_service.store_path = Path(temp_dir) / "self_training.jsonl"

        world_model = world_model_service.build_world_model()
        if "next_best_focus" not in world_model:
            failures.append(("world_model_focus", world_model))

        curriculum = curriculum_engine_service.build_plan(world_model, cycles=6)
        if len(curriculum.get("schedule", [])) != 6:
            failures.append(("curriculum_schedule", curriculum))

        task = curriculum_engine_service.next_task(world_model)
        result = self_training_service.run_cycle(task["domain"], task["difficulty"])
        verification = verifier_service.verify_training_record(result["record"])
        if not verification.get("verified"):
            failures.append(("verification", verification))

        mentor = ai_mentor_service.critique_training_record(result["record"], verification)
        if not mentor.get("critique") or not mentor.get("next_drill"):
            failures.append(("mentor", mentor))

        client = TestClient(app)
        world_response = client.get("/debug/world-model")
        if world_response.status_code != 200:
            failures.append(("debug_world_model_status", world_response.status_code))
        train_response = client.post("/debug/brain-training/run")
        if train_response.status_code != 200:
            failures.append(("debug_brain_training_status", train_response.status_code))
        else:
            data = train_response.json()
            for key in ("task", "training_result", "verification", "mentor", "updated_world_model"):
                if key not in data:
                    failures.append((f"debug_missing_{key}", data.keys()))

    self_training_service.store_path = original_path

    if failures:
        for name, details in failures:
            print(f"FAIL {name}: {details}")
        raise SystemExit(1)

    print("brain_architecture_v2_eval_failed=0")


if __name__ == "__main__":
    main()
