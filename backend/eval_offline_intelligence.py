from app.ml.inference.turkish_brain_router import turkish_brain_router
from app.services.knowledge_base_service import knowledge_base_service
from app.services.reasoning_planner_service import reasoning_planner_service
from app.services.response_generation_service import response_generation_service
from app.services.solution_synthesizer_service import solution_synthesizer_service


CASES = [
    {
        "message": "C++ compile hatası alıyorum pointer array karıştı",
        "expected_route": "code_tutor",
        "expected_strategy": "debug_first_error",
        "expected_knowledge": "cpp",
    },
    {
        "message": "Fizik formülünü bilimsel ama sade anlat",
        "expected_route": "scientific_tutor",
        "expected_strategy": "concept_then_reasoning",
        "expected_knowledge": "physics",
    },
    {
        "message": "Bunu hafızaya alma kaydetme",
        "expected_route": "privacy_boundary",
        "expected_strategy": "respect_privacy",
        "expected_knowledge": "privacy",
    },
    {
        "message": "Kötüyüm çözüm istemiyorum sadece dinle",
        "expected_route": "emotional_support",
        "expected_strategy": "listen_validate_then_invite",
        "expected_knowledge": "emotional_support",
    },
]


def main() -> None:
    failures = []

    for case in CASES:
        message = case["message"]
        brain_state = turkish_brain_router.predict_brain_state(message)
        knowledge = knowledge_base_service.retrieve(message, brain_state)
        reasoning_plan = reasoning_planner_service.build_plan(message, brain_state, knowledge=knowledge)
        synthesis = solution_synthesizer_service.synthesize(message, brain_state, {}, knowledge, reasoning_plan)
        response = response_generation_service.generate_reply(
            message,
            brain_state,
            context={
                "deep_memory": {},
                "knowledge": knowledge,
                "reasoning_plan": reasoning_plan,
                "synthesis": synthesis,
            },
        )

        domains = {item.get("domain") for item in knowledge}
        if brain_state.get("route") != case["expected_route"]:
            failures.append((message, "route", brain_state.get("route"), case["expected_route"]))
        if reasoning_plan.get("strategy") != case["expected_strategy"]:
            failures.append((message, "strategy", reasoning_plan.get("strategy"), case["expected_strategy"]))
        if case["expected_knowledge"] not in domains:
            failures.append((message, "knowledge", sorted(domains), case["expected_knowledge"]))
        if not response.get("reply"):
            failures.append((message, "reply", response, "non-empty reply"))
        if not response.get("response_meta", {}).get("reasoning_plan"):
            failures.append((message, "meta", response.get("response_meta"), "reasoning_plan"))

    if failures:
        for failure in failures:
            print(f"FAIL message={failure[0]!r} field={failure[1]} actual={failure[2]!r} expected={failure[3]!r}")
        raise SystemExit(1)

    print(f"offline intelligence eval passed: {len(CASES)} cases")


if __name__ == "__main__":
    main()
