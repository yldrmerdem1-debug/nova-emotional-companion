import argparse
from datetime import datetime, timezone
from pathlib import Path

from app.services.fine_tune_dataset_service import fine_tune_dataset_service
from app.services.self_training_service import self_training_service
from app.services.training_readiness_service import training_readiness_service


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline self-training cycles.")
    parser.add_argument("--cycles", type=int, default=10, help="Number of cycles per domain.")
    parser.add_argument("--domains", nargs="+", default=["cpp", "math"], help="Domains to train.")
    parser.add_argument("--report", default="app/data/generated/self_training_report.md", help="Markdown report path.")
    parser.add_argument("--require-ready", action="store_true", help="Stop if the domain is not ready for self-training.")
    args = parser.parse_args()

    readiness = training_readiness_service.evaluate(args.domains)
    report_lines = [
        "# Self Training Report",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Readiness Gate",
        "",
        f"`{readiness}`",
        "",
    ]
    print("\nREADINESS GATE")
    print(readiness)
    if args.require_ready and not readiness.get("ready_for_self_training"):
        report_lines.extend(
            [
                "Self-training durduruldu: hazırlık seviyesi yeterli değil.",
                "",
                "Eksikleri tamamlayınca aynı komutu yeniden çalıştır.",
                "",
            ]
        )
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(report_lines), encoding="utf-8")
        print(f"\nSelf-training stopped by readiness gate. Report written: {report_path}")
        return

    for domain in args.domains:
        print(f"\n[{domain}] self-training starting: cycles={args.cycles}")
        report_lines.extend([f"## Domain: {domain}", ""])
        for index in range(args.cycles):
            result = self_training_service.run_cycle(domain)
            record = result["record"]
            check = record["check"]
            problem = record["problem"]
            solution = record["solution"]

            print("\n" + "=" * 72)
            print(
                f"{index + 1:03d}. domain={domain} difficulty={record['difficulty']} "
                f"passed={check['passed']}"
            )
            print(f"PROBLEM: {problem['prompt']}")
            print(f"SOLUTION: {solution['explanation']}")
            print(f"CHECK: expected={check['expected']} actual={check['actual']} mistake={check['mistake_type']}")

            report_lines.extend(
                [
                    f"### Cycle {index + 1} - difficulty {record['difficulty']}",
                    "",
                    f"**Problem:** {problem['prompt']}",
                    "",
                    f"**Solution:** {solution['explanation']}",
                    "",
                    f"**Check:** passed={check['passed']}, expected={check['expected']}, actual={check['actual']}, mistake={check['mistake_type']}",
                    "",
                ]
            )

        progress = self_training_service.progress(domain)
        print(f"\n[{domain}] progress={progress}")
        report_lines.extend([f"**Progress:** `{progress}`", ""])

    export = fine_tune_dataset_service.export_datasets()
    print("\ntraining export:")
    print(export)
    report_lines.extend(["## Training Export", "", f"`{export}`", ""])

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\nReport written: {report_path}")


if __name__ == "__main__":
    main()
