from pathlib import Path
from typing import Any


class ToolDiagnosticService:
    def __init__(self) -> None:
        self.backend_root = Path(__file__).resolve().parents[2]

    def inspect_project(self) -> dict[str, Any]:
        return {
            "backend_root": str(self.backend_root),
            "critical_files": self._critical_files(),
            "data_stores": self._data_stores(),
            "ml_models": self._ml_models(),
            "health_score": self._health_score(),
        }

    def _critical_files(self) -> dict[str, bool]:
        files = {
            "main": self.backend_root / "app" / "main.py",
            "turkish_brain_router": self.backend_root / "app" / "ml" / "inference" / "turkish_brain_router.py",
            "brain_meta_controller": self.backend_root / "app" / "ml" / "inference" / "brain_meta_controller.py",
            "response_generation": self.backend_root / "app" / "services" / "response_generation_service.py",
            "deep_memory": self.backend_root / "app" / "services" / "deep_memory_service.py",
            "knowledge_base": self.backend_root / "app" / "services" / "knowledge_base_service.py",
            "local_llm": self.backend_root / "app" / "services" / "local_llm_service.py",
        }
        return {name: path.exists() for name, path in files.items()}

    def _data_stores(self) -> dict[str, Any]:
        data_dir = self.backend_root / "app" / "data"
        stores = {}
        for filename in [
            "deep_memory_store.jsonl",
            "emotional_memory_store.jsonl",
            "learning_loop_store.jsonl",
            "long_context_timeline.jsonl",
            "response_training_corpus.jsonl",
        ]:
            path = data_dir / filename
            stores[filename] = {
                "exists": path.exists(),
                "lines": self._line_count(path),
            }
        return stores

    def _ml_models(self) -> dict[str, Any]:
        models_dir = self.backend_root / "app" / "ml" / "models"
        model_files = sorted(path.name for path in models_dir.glob("*.joblib")) if models_dir.exists() else []
        return {
            "models_dir_exists": models_dir.exists(),
            "count": len(model_files),
            "files": model_files,
        }

    def _health_score(self) -> dict[str, Any]:
        critical = self._critical_files()
        model_info = self._ml_models()
        present = sum(1 for exists in critical.values() if exists)
        score = present / max(len(critical), 1)
        if model_info["count"] >= 20:
            score += 0.15
        return {
            "score": round(min(1.0, score), 3),
            "status": "strong" if score >= 0.85 else "partial",
        }

    def _line_count(self, path: Path) -> int:
        try:
            return len(path.read_text(encoding="utf-8").splitlines())
        except OSError:
            return 0


tool_diagnostic_service = ToolDiagnosticService()
