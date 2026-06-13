from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference.turkish_brain_router import turkish_brain_router
from app.services.mind.global_workspace_service import global_workspace_service


def main() -> None:
    failures = []

    privacy_state = turkish_brain_router.predict_brain_state("bunu hafızaya alma kaydetme")
    privacy_workspace = global_workspace_service.integrate(
        {
            "message": "bunu hafızaya alma kaydetme",
            "brain_state": privacy_state,
            "memory_context": {"saved_memories": [{"id": "bad"}], "profile_summary": {}},
            "emotional_context": {"emotional_summary": {"dominant_mood": "neutral"}},
            "knowledge_context": [],
            "reflection": {},
            "response_meta": {"strategy": "respect_boundary"},
            "curiosity": {"should_ask": True},
            "world_model": {},
        }
    )
    if privacy_workspace["attention"]["top_signal"]["type"] != "privacy":
        failures.append(("privacy_attention", privacy_workspace["attention"]))
    if not privacy_workspace["contradictions"]["has_contradiction"]:
        failures.append(("privacy_contradiction", privacy_workspace["contradictions"]))
    if privacy_workspace["final_policy"]["action"] != "repair_or_abort":
        failures.append(("privacy_final_policy", privacy_workspace["final_policy"]))

    emotional_state = turkish_brain_router.predict_brain_state("kötüyüm çözüm istemiyorum sadece dinle")
    emotional_workspace = global_workspace_service.integrate(
        {
            "message": "kötüyüm çözüm istemiyorum sadece dinle",
            "brain_state": emotional_state,
            "memory_context": {"profile_summary": {}},
            "emotional_context": {"emotional_summary": {"dominant_mood": "low", "support_preference": "listen_first"}},
            "knowledge_context": [],
            "reflection": {"should_expand_answer": False, "layers": {"best_next_move": "Önce dinle"}},
            "response_meta": {"strategy": "listen_first"},
            "curiosity": {},
            "world_model": {"active_goals": ["Kişisel AI robot projesini büyütmek"], "next_best_focus": {"domain": "math"}},
        }
    )
    if emotional_workspace["goal_stack"]["active_goal"]["horizon"] != "immediate":
        failures.append(("goal_stack", emotional_workspace["goal_stack"]))
    if not emotional_workspace["causal_graph"]["edges"]:
        failures.append(("causal_edges", emotional_workspace["causal_graph"]))
    if emotional_workspace["metacognition"]["confidence"] <= 0:
        failures.append(("metacognition_confidence", emotional_workspace["metacognition"]))
    if not emotional_workspace["memory_consolidation"]["user_model_summary"]:
        failures.append(("memory_consolidation", emotional_workspace["memory_consolidation"]))
    if not emotional_workspace["self_explanation"]["compact"]:
        failures.append(("self_explanation", emotional_workspace["self_explanation"]))

    client = TestClient(app)
    response = client.post("/chat", json={"message": "C++ pointer hatasını kısa anlat"})
    if response.status_code != 200:
        failures.append(("chat_status", response.status_code))
    else:
        data = response.json()
        mind = data.get("mind_workspace", {})
        for key in (
            "attention",
            "contradictions",
            "causal_graph",
            "goal_stack",
            "metacognition",
            "memory_consolidation",
            "self_explanation",
            "final_policy",
        ):
            if key not in mind:
                failures.append((f"chat_missing_{key}", mind.keys()))

    if failures:
        for name, details in failures:
            print(f"FAIL {name}: {details}")
        raise SystemExit(1)

    print("mind_architecture_eval_failed=0")


if __name__ == "__main__":
    main()
