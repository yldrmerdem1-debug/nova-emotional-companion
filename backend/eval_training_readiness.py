from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.main import app
from app.services.self_training_service import self_training_service
from app.services.training_readiness_service import training_readiness_service


def main() -> None:
    failures = []
    readiness = training_readiness_service.evaluate(["cpp", "python", "java", "math", "physics", "algorithms"])
    domains = {report.get("domain"): report for report in readiness.get("domains", [])}

    for domain in ("cpp", "python", "java", "math", "physics", "algorithms"):
        report = domains.get(domain)
        if not report:
            failures.append((f"missing_domain_{domain}", readiness))
            continue
        if report.get("problem_count", 0) <= 0:
            failures.append((f"missing_problems_{domain}", report))
        if report.get("knowledge_count", 0) <= 0:
            failures.append((f"missing_knowledge_{domain}", report))
        if 1 not in report.get("covered_difficulties", []):
            failures.append((f"missing_basic_difficulty_{domain}", report))

    original_path = self_training_service.store_path
    with TemporaryDirectory() as temp_dir:
        self_training_service.store_path = Path(temp_dir) / "self_training.jsonl"
        for domain in ("python", "java", "physics"):
            result = self_training_service.run_cycle(domain)
            if result["record"]["domain"] != domain:
                failures.append((f"cycle_domain_{domain}", result))
            if not result["record"]["check"]["passed"]:
                failures.append((f"cycle_passed_{domain}", result))
    self_training_service.store_path = original_path

    client = TestClient(app)
    response = client.get("/debug/training-readiness")
    if response.status_code != 200:
        failures.append(("readiness_endpoint_status", response.status_code))
    else:
        data = response.json()
        if "readiness_score" not in data or "domains" not in data:
            failures.append(("readiness_endpoint_shape", data))

    skipped = client.post("/debug/self-training/run", json={"domain": "python", "force": False})
    if skipped.status_code != 200:
        failures.append(("self_training_gate_status", skipped.status_code))
    elif "readiness" not in skipped.json():
        failures.append(("self_training_gate_readiness", skipped.json()))

    if failures:
        for name, details in failures:
            print(f"FAIL {name}: {details}")
        raise SystemExit(1)

    print("training_readiness_eval_failed=0")


if __name__ == "__main__":
    main()
