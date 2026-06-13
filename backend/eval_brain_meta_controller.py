from app.ml.inference.turkish_brain_router import turkish_brain_router


CASES = [
    {
        "message": "C++ pointer hatasını hafızaya alma kaydetme",
        "context": {},
        "expected": {
            "route": "privacy_boundary",
            "memory_allowed": False,
            "need": "do_not_store",
            "face": "serious",
            "risk": "memory_violation",
            "decision": "privacy_terms_override_all",
        },
    },
    {
        "message": "Kötüyüm çözüm istemiyorum sadece dinle",
        "context": {},
        "expected": {
            "route": "emotional_support",
            "need": "listen",
            "tone": "soft",
            "face": "soft_concerned",
            "risk": "unsolicited_advice",
            "decision": "explicit_listening_request_overrides_solution",
        },
    },
    {
        "message": "Sinir oldum C++ compile hata verdi",
        "context": {},
        "expected": {
            "route": "code_tutor",
            "need": "debug_or_explain",
            "tone": "calm_supportive",
            "face": "serious",
            "risk": "high_emotion",
            "decision": "code_task_kept_but_tone_softened",
        },
    },
    {
        "message": "Bunu uzatma direkt çöz",
        "context": {"profile_summary": {"reply_style": "short_direct"}},
        "expected": {
            "style": "short_direct",
            "tone": "plain_direct",
            "decision": "profile_short_direct_style",
        },
    },
    {
        "message": "Fizik formülünü bilimsel açıkla",
        "context": {},
        "expected": {
            "route": "scientific_tutor",
            "need": "explain_scientifically",
            "tone": "scientific_clear",
            "face": "focused",
            "decision": "science_signal_route_lock",
        },
    },
]


def main() -> None:
    failures = []
    for case in CASES:
        state = turkish_brain_router.predict_brain_state(case["message"], context=case["context"])
        meta = state.get("brain_meta", {})
        expected = case["expected"]

        for field in ("route", "need", "tone", "style", "memory_allowed"):
            if field in expected and state.get(field) != expected[field]:
                failures.append((case["message"], field, state.get(field), expected[field]))

        if expected.get("face") and state.get("robot_state", {}).get("face") != expected["face"]:
            failures.append((case["message"], "face", state.get("robot_state", {}).get("face"), expected["face"]))

        if expected.get("risk") and expected["risk"] not in meta.get("risk_flags", []):
            failures.append((case["message"], "risk", meta.get("risk_flags", []), expected["risk"]))

        if expected.get("decision") and expected["decision"] not in meta.get("decisions", []):
            failures.append((case["message"], "decision", meta.get("decisions", []), expected["decision"]))

        if not isinstance(meta.get("confidence"), float):
            failures.append((case["message"], "confidence", meta.get("confidence"), "float"))

        route_scores = meta.get("route_scores", {})
        if expected.get("route") and expected["route"] not in route_scores:
            failures.append((case["message"], "route_scores", route_scores, expected["route"]))

    if failures:
        for failure in failures:
            print(f"FAIL message={failure[0]!r} field={failure[1]} actual={failure[2]!r} expected={failure[3]!r}")
        raise SystemExit(1)

    print(f"brain_meta_eval_passed={len(CASES)}")


if __name__ == "__main__":
    main()
