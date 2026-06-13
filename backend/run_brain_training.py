import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.services.ai_mentor_service import ai_mentor_service
from app.services.curriculum_engine_service import curriculum_engine_service
from app.services.fine_tune_dataset_service import fine_tune_dataset_service
from app.services.mind.global_workspace_service import global_workspace_service
from app.services.self_training_service import self_training_service
from app.services.verifier_service import verifier_service
from app.services.world_model_service import world_model_service


def main() -> None:
    parser = argparse.ArgumentParser(description="Run brain architecture v2 adaptive training.")
    parser.add_argument("--cycles", type=int, default=12)
    parser.add_argument("--report", default="app/data/generated/brain_training_report.md")
    args = parser.parse_args()

    world_model = world_model_service.build_world_model()
    curriculum = curriculum_engine_service.build_plan(world_model, cycles=args.cycles)
    report_lines = [
        "# Brain Training V2 Report",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## World Model Focus",
        "",
        f"`{json.dumps(world_model.get('next_best_focus', {}), ensure_ascii=False)}`",
        "",
        "## Cycles",
        "",
    ]

    print("\nBRAIN TRAINING V2 STARTING")
    print(f"focus={world_model.get('next_best_focus')}")

    for task in curriculum["schedule"]:
        result = self_training_service.run_cycle(task["domain"], task["difficulty"])
        record = result["record"]
        verification = verifier_service.verify_training_record(record)
        mentor = ai_mentor_service.critique_training_record(record, verification)
        mind_workspace = global_workspace_service.integrate(
            {
                "message": record["problem"]["prompt"],
                "brain_state": {
                    "route": "code_tutor" if task["domain"] in {"cpp", "algorithms"} else "scientific_tutor",
                    "need": "debug_or_explain",
                    "emotion": "focused",
                    "memory_allowed": True,
                    "brain_meta": {"confidence": verification["confidence"], "risk_flags": []},
                },
                "memory_context": {"profile_summary": {}},
                "emotional_context": {"emotional_summary": {"dominant_mood": "neutral"}},
                "knowledge_context": [],
                "reasoning_plan": {"strategy": "self_training"},
                "synthesis": {},
                "reflection": {"should_expand_answer": False, "layers": {"best_next_move": mentor["next_drill"]}},
                "response_meta": {"strategy": "self_training_solution"},
                "learning_context": {},
                "curiosity": {},
                "world_model": world_model,
            }
        )

        print("\n" + "=" * 72)
        print(
            f"cycle={task['cycle']} domain={task['domain']} difficulty={record['difficulty']} "
            f"stage={task.get('stage')} source={record['problem'].get('source', 'bank')}"
        )
        print(f"problem={record['problem']['prompt']}")
        print(f"solution={record['solution']['explanation']}")
        print(f"verified={verification['verified']} confidence={verification['confidence']} issues={verification['issues']}")
        print(f"mind_policy={mind_workspace['final_policy']}")
        print(f"mentor={mentor['critique']} next={mentor['next_drill']}")

        report_lines.extend(
            [
                f"### Cycle {task['cycle']} - {task['domain']} difficulty {record['difficulty']}",
                "",
                f"**Stage:** {task.get('stage')}",
                "",
                f"**Problem source:** {record['problem'].get('source', 'bank')}",
                "",
                f"**Objective:** {task['objective']}",
                "",
                f"**Problem:** {record['problem']['prompt']}",
                "",
                f"**Solution:** {record['solution']['explanation']}",
                "",
                f"**Verification:** `{json.dumps(verification, ensure_ascii=False)}`",
                "",
                f"**Mentor:** {mentor['critique']}",
                "",
                f"**Mind policy:** `{json.dumps(mind_workspace['final_policy'], ensure_ascii=False)}`",
                "",
                f"**Next drill:** {mentor['next_drill']}",
                "",
            ]
        )

    export = fine_tune_dataset_service.export_datasets()
    final_world_model = world_model_service.build_world_model()
    report_lines.extend(
        [
            "## Final World Model",
            "",
            f"`{json.dumps(final_world_model.get('next_best_focus', {}), ensure_ascii=False)}`",
            "",
            "## Training Export",
            "",
            f"`{json.dumps(export, ensure_ascii=False)}`",
            "",
        ]
    )

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\nReport written: {report_path}")


if __name__ == "__main__":
    main()
