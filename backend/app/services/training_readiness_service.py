import json
from pathlib import Path
from typing import Any


class TrainingReadinessService:
    def __init__(self) -> None:
        self.data_dir = Path(__file__).resolve().parents[1] / "data"
        self.curriculum_path = self.data_dir / "domain_curriculum_map.json"
        self.problem_bank_paths = [
            self.data_dir / "self_training_problem_bank.json",
            self.data_dir / "self_training_problem_bank_extra.json",
        ]
        self.knowledge_dir = self.data_dir / "knowledge_base"

    def evaluate(self, domains: list[str] | None = None) -> dict[str, Any]:
        curriculum = self._load_curriculum()
        requested_domains = domains or list(curriculum.keys())
        domain_reports = []
        ready_domains = 0

        for domain in requested_domains:
            domain = domain.strip().casefold()
            config = curriculum.get(domain, {})
            if not config:
                domain_reports.append(self._unknown_domain_report(domain))
                continue

            problems = self._problems_for_domain(domain)
            knowledge_items = self._knowledge_for_domain(domain)
            report = self._domain_report(domain, config, problems, knowledge_items)
            if report["ready"]:
                ready_domains += 1
            domain_reports.append(report)

        total = max(len(domain_reports), 1)
        readiness_score = round(sum(report["score"] for report in domain_reports) / total, 3)
        return {
            "ready_for_self_training": all(report["ready"] for report in domain_reports) and readiness_score >= 0.78,
            "readiness_score": readiness_score,
            "ready_domains": ready_domains,
            "total_domains": len(domain_reports),
            "domains": domain_reports,
            "next_action": self._next_action(domain_reports),
        }

    def _domain_report(
        self,
        domain: str,
        config: dict[str, Any],
        problems: list[dict[str, Any]],
        knowledge_items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        required_count = int(config.get("minimum_bank_count", 8))
        required_knowledge = int(config.get("minimum_knowledge_count", 6))
        required_difficulties = {int(item) for item in config.get("minimum_difficulties", [1, 2, 3])}
        required_topics = set(config.get("core_topics", []))

        covered_difficulties = {int(problem.get("difficulty", 1)) for problem in problems}
        covered_topics = self._covered_topics(problems, knowledge_items)
        missing_topics = sorted(required_topics - covered_topics)
        missing_difficulties = sorted(required_difficulties - covered_difficulties)

        bank_score = min(1.0, len(problems) / max(required_count, 1))
        knowledge_score = min(1.0, len(knowledge_items) / max(required_knowledge, 1))
        difficulty_score = 1.0 - (len(missing_difficulties) / max(len(required_difficulties), 1))
        topic_score = 1.0 - (len(missing_topics) / max(len(required_topics), 1))
        score = round((bank_score * 0.3) + (knowledge_score * 0.25) + (difficulty_score * 0.2) + (topic_score * 0.25), 3)

        blockers = []
        if bank_score < 1.0:
            blockers.append(f"problem_bank_short:{len(problems)}/{required_count}")
        if knowledge_score < 1.0:
            blockers.append(f"knowledge_short:{len(knowledge_items)}/{required_knowledge}")
        if missing_difficulties:
            blockers.append("missing_difficulties:" + ",".join(str(item) for item in missing_difficulties))
        if len(missing_topics) > max(2, len(required_topics) // 3):
            blockers.append("topic_coverage_low")

        return {
            "domain": domain,
            "label": config.get("label", domain),
            "ready": score >= 0.72 and not any(blocker.startswith("missing_difficulties") for blocker in blockers),
            "score": score,
            "problem_count": len(problems),
            "knowledge_count": len(knowledge_items),
            "covered_difficulties": sorted(covered_difficulties),
            "missing_difficulties": missing_difficulties,
            "covered_topics": sorted(covered_topics),
            "missing_topics": missing_topics,
            "blockers": blockers,
            "recommended_work": self._recommended_work(domain, missing_topics, missing_difficulties, blockers),
        }

    def _covered_topics(self, problems: list[dict[str, Any]], knowledge_items: list[dict[str, Any]]) -> set[str]:
        topics: set[str] = set()
        for problem in problems:
            topics.update(str(concept).casefold() for concept in problem.get("concepts", []) if isinstance(concept, str))
            topics.add(str(problem.get("type", "")).casefold())
        for item in knowledge_items:
            topics.update(str(keyword).casefold() for keyword in item.get("keywords", []) if isinstance(keyword, str))
            topics.add(str(item.get("level", "")).casefold())
        return {topic for topic in topics if topic}

    def _recommended_work(
        self,
        domain: str,
        missing_topics: list[str],
        missing_difficulties: list[int],
        blockers: list[str],
    ) -> list[str]:
        recommendations = []
        if missing_topics:
            recommendations.append(f"{domain}: eksik konulara bilgi kartı ve problem ekle: {', '.join(missing_topics[:5])}")
        if missing_difficulties:
            recommendations.append(f"{domain}: zorluk seviyeleri eksik: {', '.join(str(item) for item in missing_difficulties)}")
        if any(blocker.startswith("problem_bank_short") for blocker in blockers):
            recommendations.append(f"{domain}: problem bankasını genişlet")
        if any(blocker.startswith("knowledge_short") for blocker in blockers):
            recommendations.append(f"{domain}: bilgi tabanına doğrulanmış konu özeti ekle")
        return recommendations or [f"{domain}: hazırlık seviyesi self-training için yeterli"]

    def _next_action(self, reports: list[dict[str, Any]]) -> str:
        not_ready = [report for report in reports if not report.get("ready")]
        if not not_ready:
            return "self_training_can_start"
        weakest = min(not_ready, key=lambda report: report.get("score", 0.0))
        return f"strengthen_{weakest.get('domain')}_before_self_training"

    def _unknown_domain_report(self, domain: str) -> dict[str, Any]:
        return {
            "domain": domain,
            "ready": False,
            "score": 0.0,
            "problem_count": 0,
            "knowledge_count": 0,
            "blockers": ["unknown_domain"],
            "recommended_work": [f"{domain}: curriculum haritasına eklenmeli"],
        }

    def _load_curriculum(self) -> dict[str, Any]:
        try:
            loaded = json.loads(self.curriculum_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        domains = loaded.get("domains", {}) if isinstance(loaded, dict) else {}
        return domains if isinstance(domains, dict) else {}

    def _problems_for_domain(self, domain: str) -> list[dict[str, Any]]:
        problems = []
        for path in self.problem_bank_paths:
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            loaded_problems = loaded.get("problems", []) if isinstance(loaded, dict) else []
            if not isinstance(loaded_problems, list):
                continue
            for problem in loaded_problems:
                if isinstance(problem, dict) and problem.get("domain") == domain:
                    problems.append(problem)
        return problems

    def _knowledge_for_domain(self, domain: str) -> list[dict[str, Any]]:
        items = []
        for path in sorted(self.knowledge_dir.glob("*.jsonl")):
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for line in lines:
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict) and item.get("domain") == domain:
                    items.append(item)
        return items


training_readiness_service = TrainingReadinessService()
