from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference.turkish_brain_router import turkish_brain_router
from app.services.curiosity_engine_service import curiosity_engine_service
from app.services.deep_memory_service import deep_memory_service
from app.services.emotional_memory_service import emotional_memory_service
from app.services.learning_loop_service import learning_loop_service
from app.services.reflection_engine_service import reflection_engine_service


def main() -> None:
    failures = []
    original_deep_path = deep_memory_service.store_path
    original_emotional_path = emotional_memory_service.store_path
    original_learning_path = learning_loop_service.store_path

    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        deep_memory_service.store_path = temp_path / "deep_memory.jsonl"
        emotional_memory_service.store_path = temp_path / "emotional_memory.jsonl"
        learning_loop_service.store_path = temp_path / "learning_loop.jsonl"

        privacy_state = turkish_brain_router.predict_brain_state("bunu hafızaya alma kaydetme")
        learning = learning_loop_service.process_exchange(
            "bunu hafızaya alma kaydetme",
            "Tamam, kaydetmiyorum.",
            privacy_state,
            {},
            [],
            {},
        )
        if learning["learning_summary"]["status"] != "skipped_privacy_boundary":
            failures.append(("privacy_learning_skip", learning))

        emotional_state = turkish_brain_router.predict_brain_state("Bugün kötüyüm çözüm istemiyorum sadece dinle")
        emotional = emotional_memory_service.process_message(
            "Bugün kötüyüm çözüm istemiyorum sadece dinle",
            emotional_state,
        )
        summary = emotional["emotional_summary"]
        if summary.get("support_preference") != "listen_first":
            failures.append(("emotional_support_preference", summary))
        if summary.get("dominant_mood") not in {"low", "sad"}:
            failures.append(("emotional_dominant_mood", summary))

        curiosity = curiosity_engine_service.generate_question(
            "Bugün kötüyüm çözüm istemiyorum sadece dinle",
            emotional_state,
            {"profile_summary": {}},
            emotional,
            {"learning_summary": {}},
        )
        if not curiosity.get("should_ask"):
            failures.append(("curiosity_should_ask", curiosity))

        reflection = reflection_engine_service.reflect(
            "Bilinç ve özgür irade üzerine derin düşün",
            turkish_brain_router.predict_brain_state("Bilinç ve özgür irade üzerine derin düşün"),
            {"profile_summary": {}},
            emotional,
            [],
            {"goal": "Derin düşün", "steps": ["Varsayımları ayır"]},
        )
        if reflection.get("reflection_type") not in {"philosophical", "deep_reasoning"}:
            failures.append(("reflection_type", reflection))
        if not reflection.get("should_expand_answer"):
            failures.append(("reflection_expand", reflection))

        client = TestClient(app)
        response = client.post("/chat", json={"message": "Felsefe olarak bilinç nedir derin düşün"})
        if response.status_code != 200:
            failures.append(("chat_status", response.status_code))
        else:
            data = response.json()
            for key in ("emotional_context", "learning_context", "curiosity", "reflection"):
                if key not in data:
                    failures.append((f"chat_missing_{key}", data.keys()))
            if data.get("reflection", {}).get("should_expand_answer") is not True:
                failures.append(("chat_reflection_expand", data.get("reflection")))

    deep_memory_service.store_path = original_deep_path
    emotional_memory_service.store_path = original_emotional_path
    learning_loop_service.store_path = original_learning_path

    if failures:
        for name, details in failures:
            print(f"FAIL {name}: {details}")
        raise SystemExit(1)

    print("learning_layers_eval_failed=0")


if __name__ == "__main__":
    main()
