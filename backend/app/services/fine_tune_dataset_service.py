import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class FineTuneDatasetService:
    def __init__(self) -> None:
        self.data_dir = Path(__file__).resolve().parents[1] / "data"
        self.export_dir = self.data_dir / "generated"

    def export_datasets(self) -> dict[str, Any]:
        self.export_dir.mkdir(parents=True, exist_ok=True)
        response_rows = self._response_rows()
        preference_rows = self._preference_rows()
        brain_rows = self._brain_rows()

        response_path = self.export_dir / "local_llm_finetune.jsonl"
        preference_path = self.export_dir / "response_preference_pairs.jsonl"
        brain_path = self.export_dir / "brain_meta_training.jsonl"
        self._write_jsonl(response_path, response_rows)
        self._write_jsonl(preference_path, preference_rows)
        self._write_jsonl(brain_path, brain_rows)
        return {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "files": {
                "local_llm_finetune": str(response_path),
                "response_preference_pairs": str(preference_path),
                "brain_meta_training": str(brain_path),
            },
            "counts": {
                "local_llm_finetune": len(response_rows),
                "response_preference_pairs": len(preference_rows),
                "brain_meta_training": len(brain_rows),
            },
        }

    def _response_rows(self) -> list[dict[str, Any]]:
        rows = []
        for record in self._read_jsonl(self.data_dir / "response_training_corpus.jsonl"):
            user_message = record.get("user_message")
            ideal_reply = record.get("ideal_reply") or record.get("robot_reply")
            if not isinstance(user_message, str) or not isinstance(ideal_reply, str) or not ideal_reply.strip():
                continue
            rows.append(
                {
                    "messages": [
                        {
                            "role": "system",
                            "content": "Türkçe konuşan, sıcak, bilgili, offline kişisel robot olarak cevap ver.",
                        },
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": ideal_reply.strip()},
                    ],
                    "source": "response_feedback",
                    "quality": record.get("rating", "unknown"),
                }
            )
        return rows

    def _preference_rows(self) -> list[dict[str, Any]]:
        rows = []
        for record in self._read_jsonl(self.data_dir / "response_training_corpus.jsonl"):
            if record.get("rating") != "bad":
                continue
            if not record.get("ideal_reply") or not record.get("robot_reply"):
                continue
            rows.append(
                {
                    "prompt": record.get("user_message"),
                    "chosen": record.get("ideal_reply"),
                    "rejected": record.get("robot_reply"),
                    "source": "human_correction",
                }
            )
        return rows

    def _brain_rows(self) -> list[dict[str, Any]]:
        rows = []
        for record in self._read_jsonl(self.data_dir / "deep_memory_store.jsonl"):
            evidence = record.get("evidence")
            if not isinstance(evidence, str) or not evidence.strip():
                continue
            rows.append(
                {
                    "message": evidence,
                    "labels": {
                        "memory_type": record.get("memory_type"),
                        "memory_key": record.get("key"),
                        "brain_route": record.get("brain_route"),
                        "brain_need": record.get("brain_need"),
                    },
                    "source": "deep_memory",
                }
            )
        for record in self._read_jsonl(self.data_dir / "learning_loop_store.jsonl"):
            evidence = record.get("evidence")
            if not isinstance(evidence, str) or not evidence.strip():
                continue
            rows.append(
                {
                    "message": evidence,
                    "labels": {
                        "record_type": record.get("record_type"),
                        "topic": record.get("topic"),
                    },
                    "source": "learning_loop",
                }
            )
        for record in self._read_jsonl(self.data_dir / "self_training_store.jsonl"):
            problem = record.get("problem", {})
            if not isinstance(problem, dict):
                continue
            prompt = problem.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                continue
            rows.append(
                {
                    "message": prompt,
                    "labels": {
                        "domain": record.get("domain"),
                        "difficulty": record.get("difficulty"),
                        "passed": record.get("check", {}).get("passed") if isinstance(record.get("check"), dict) else None,
                        "mistake_type": record.get("check", {}).get("mistake_type") if isinstance(record.get("check"), dict) else None,
                    },
                    "source": "self_training",
                }
            )
        return rows

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
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
            if isinstance(record, dict):
                records.append(record)
        return records

    def _write_jsonl(self, path: Path, rows: list[dict[str, Any]]) -> None:
        with path.open("w", encoding="utf-8") as output:
            for row in rows:
                output.write(json.dumps(row, ensure_ascii=False) + "\n")


fine_tune_dataset_service = FineTuneDatasetService()
