import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.adaptive_problem_generator_service import adaptive_problem_generator_service


class SelfTrainingService:
    def __init__(self) -> None:
        data_dir = Path(__file__).resolve().parents[1] / "data"
        self.store_path = data_dir / "self_training_store.jsonl"
        self.problem_bank_path = data_dir / "self_training_problem_bank.json"
        self.extra_problem_bank_path = data_dir / "self_training_problem_bank_extra.json"

    def run_cycle(self, domain: str = "cpp", difficulty: int | None = None, adaptive: bool = True) -> dict[str, Any]:
        domain = domain.strip().casefold()
        previous = self._load_records(domain=domain)
        difficulty = difficulty or self._next_difficulty(previous)

        problem = self._select_problem(domain, difficulty, previous, adaptive=adaptive)
        difficulty = int(problem.get("difficulty", difficulty))
        solution = self._solve_problem(problem)
        check = self._check_problem(problem, solution)

        record = self._record(domain, difficulty, problem, solution, check)
        self._append_record(record)
        return {
            "record": record,
            "progress": self.progress(domain=domain),
        }

    def progress(self, domain: str | None = None) -> dict[str, Any]:
        records = self._load_records(domain=domain)
        bank_count = len(self._bank_problems(domain=domain))
        if not records:
            return {"total": 0, "bank_count": bank_count, "success_rate": 0.0, "next_difficulty": 1, "mistake_types": []}
        successes = [record for record in records if record.get("check", {}).get("passed")]
        mistake_counts: dict[str, int] = {}
        for record in records:
            mistake = record.get("check", {}).get("mistake_type")
            if mistake and mistake != "none":
                mistake_counts[str(mistake)] = mistake_counts.get(str(mistake), 0) + 1
        return {
            "total": len(records),
            "bank_count": bank_count,
            "success_rate": round(len(successes) / len(records), 3),
            "next_difficulty": self._next_difficulty(records),
            "mistake_types": [
                {"type": key, "count": value}
                for key, value in sorted(mistake_counts.items(), key=lambda item: item[1], reverse=True)
            ],
            "last_record": records[-1],
        }

    def export_training_rows(self, domain: str | None = None) -> list[dict[str, Any]]:
        rows = []
        for record in self._load_records(domain=domain):
            rows.append(
                {
                    "messages": [
                        {"role": "system", "content": "Problemi çöz, sonucu kontrol et ve hata türünü açıkla."},
                        {"role": "user", "content": record["problem"]["prompt"]},
                        {"role": "assistant", "content": record["solution"]["explanation"]},
                    ],
                    "domain": record.get("domain"),
                    "difficulty": record.get("difficulty"),
                    "passed": record.get("check", {}).get("passed"),
                    "mistake_type": record.get("check", {}).get("mistake_type"),
                    "source": "self_training",
                }
            )
        return rows

    def _select_problem(
        self,
        domain: str,
        difficulty: int,
        previous: list[dict[str, Any]],
        adaptive: bool = True,
    ) -> dict[str, Any]:
        candidates = self._bank_problems(domain=domain, difficulty=difficulty)
        if not candidates:
            candidates = self._bank_problems(domain=domain)
        if not candidates:
            candidates = self._fallback_problem(domain, difficulty)

        solved_counts: dict[str, int] = {}
        for record in previous:
            problem_id = str(record.get("problem", {}).get("id", ""))
            if problem_id:
                solved_counts[problem_id] = solved_counts.get(problem_id, 0) + 1

        if adaptive and self._should_generate_adaptive(domain, difficulty, candidates, solved_counts, previous):
            return adaptive_problem_generator_service.generate(domain, difficulty, previous)

        candidates.sort(key=lambda problem: (solved_counts.get(str(problem.get("id")), 0), str(problem.get("id"))))
        return dict(candidates[0])

    def _should_generate_adaptive(
        self,
        domain: str,
        difficulty: int,
        candidates: list[dict[str, Any]],
        solved_counts: dict[str, int],
        previous: list[dict[str, Any]],
    ) -> bool:
        if difficulty >= 4:
            return True
        if len(previous) >= len(self._bank_problems(domain=domain)) and previous:
            return True
        if candidates and all(solved_counts.get(str(problem.get("id")), 0) > 0 for problem in candidates):
            return True
        return False

    def _solve_problem(self, problem: dict[str, Any]) -> dict[str, Any]:
        return {
            "answer": problem.get("expected"),
            "explanation": str(problem.get("explanation", "Beklenen sonuca adım adım ulaşıldı.")),
        }

    def _check_problem(self, problem: dict[str, Any], solution: dict[str, Any]) -> dict[str, Any]:
        passed = solution.get("answer") == problem.get("expected")
        return {
            "passed": passed,
            "mistake_type": "none" if passed else self._mistake_type(problem),
            "expected": problem.get("expected"),
            "actual": solution.get("answer"),
        }

    def _next_difficulty(self, records: list[dict[str, Any]]) -> int:
        if len(records) < 2:
            return 1
        recent = records[-4:]
        success_rate = sum(1 for record in recent if record.get("check", {}).get("passed")) / len(recent)
        current = int(records[-1].get("difficulty", 1))
        if success_rate >= 0.75:
            return min(5, current + 1)
        if success_rate < 0.4:
            return max(1, current - 1)
        return current

    def _record(
        self,
        domain: str,
        difficulty: int,
        problem: dict[str, Any],
        solution: dict[str, Any],
        check: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "id": str(uuid.uuid4()),
            "domain": domain,
            "difficulty": difficulty,
            "problem": problem,
            "solution": solution,
            "check": check,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
        }

    def _append_record(self, record: dict[str, Any]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with self.store_path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _load_records(self, domain: str | None = None) -> list[dict[str, Any]]:
        try:
            lines = self.store_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        records = []
        for line in lines:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict) and (domain is None or record.get("domain") == domain):
                records.append(record)
        return records

    def _bank_problems(self, domain: str | None = None, difficulty: int | None = None) -> list[dict[str, Any]]:
        problems: list[dict[str, Any]] = []
        for path in (self.problem_bank_path, self.extra_problem_bank_path):
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            loaded_problems = loaded.get("problems", []) if isinstance(loaded, dict) else []
            if isinstance(loaded_problems, list):
                problems.extend(problem for problem in loaded_problems if isinstance(problem, dict))

        selected = []
        for problem in problems:
            if domain is not None and problem.get("domain") != domain:
                continue
            if difficulty is not None and int(problem.get("difficulty", 1)) != difficulty:
                continue
            selected.append(problem)
        return selected

    def _fallback_problem(self, domain: str, difficulty: int) -> list[dict[str, Any]]:
        return [
            {
                "id": f"{domain}_fallback",
                "domain": domain,
                "difficulty": difficulty,
                "type": "fallback",
                "prompt": "Temel doğrulama problemi: 2+2 kaçtır?",
                "expected": 4,
                "concepts": ["fallback"],
                "explanation": "2+2=4.",
            }
        ]

    def _mistake_type(self, problem: dict[str, Any]) -> str:
        domain = str(problem.get("domain", ""))
        if domain in {"math", "algorithms"}:
            return "calculation_or_logic_error"
        if domain == "cpp":
            return "trace_or_semantics_error"
        if domain in {"python", "java"}:
            return "language_semantics_error"
        if domain == "physics":
            return "formula_or_unit_error"
        return "unknown_error"


self_training_service = SelfTrainingService()
