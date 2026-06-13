from typing import Any


class CurriculumEngineService:
    DOMAINS = ("cpp", "python", "java", "math", "physics", "algorithms")

    def build_plan(self, world_model: dict[str, Any], cycles: int = 12) -> dict[str, Any]:
        self_training = world_model.get("self_training", {})
        focus = world_model.get("next_best_focus", {})
        schedule = []

        for index in range(cycles):
            domain = self._select_domain(self_training, preferred=str(focus.get("domain", "")), offset=index)
            progress = self_training.get(domain, {}) if isinstance(self_training, dict) else {}
            difficulty = self._select_difficulty(progress, index)
            schedule.append(
                {
                    "cycle": index + 1,
                    "domain": domain,
                    "difficulty": difficulty,
                    "stage": self._stage(difficulty),
                    "objective": self._objective(domain, difficulty),
                    "reason": self._reason(progress),
                }
            )

        return {
            "version": "curriculum_v1",
            "focus": focus,
            "cycles": cycles,
            "schedule": schedule,
        }

    def next_task(self, world_model: dict[str, Any]) -> dict[str, Any]:
        plan = self.build_plan(world_model, cycles=1)
        return plan["schedule"][0]

    def _select_domain(self, self_training: dict[str, Any], preferred: str, offset: int) -> str:
        if preferred in self.DOMAINS and offset == 0:
            return preferred

        scored = []
        for domain in self.DOMAINS:
            progress = self_training.get(domain, {}) if isinstance(self_training, dict) else {}
            total = int(progress.get("total", 0))
            bank_count = int(progress.get("bank_count", 0))
            success_rate = float(progress.get("success_rate", 0.0))
            score = (bank_count - min(total, bank_count)) + (1.0 - success_rate) * 5
            scored.append((score, domain))
        scored.sort(reverse=True)
        if scored:
            return scored[offset % len(scored)][1]
        return "cpp"

    def _select_difficulty(self, progress: dict[str, Any], offset: int) -> int:
        base = int(progress.get("next_difficulty", 1))
        total = int(progress.get("total", 0))
        success_rate = float(progress.get("success_rate", 0.0))
        cycle_ramp = 1 + min(4, offset // 3)
        if offset >= 11:
            cycle_ramp = 5
        ramp = max(cycle_ramp, 1 + min(4, total // 3))
        if success_rate >= 0.9 and total >= 2:
            ramp += 1
        return max(1, min(5, max(base, ramp)))

    def _objective(self, domain: str, difficulty: int) -> str:
        stage = self._stage(difficulty)
        if domain == "cpp":
            return f"C++ kavram izleme ve semantik doğrulama, zorluk {difficulty}, aşama {stage}"
        if domain == "python":
            return f"Python algoritma ve dil semantiği, zorluk {difficulty}, aşama {stage}"
        if domain == "java":
            return f"Java OOP, collection ve algoritma aktarımı, zorluk {difficulty}, aşama {stage}"
        if domain == "math":
            return f"Matematik işlem, kanıt ve olimpiyat hazırlığı, zorluk {difficulty}, aşama {stage}"
        if domain == "physics":
            return f"Fizik formül, birim ve olimpiyat sezgisi, zorluk {difficulty}, aşama {stage}"
        return f"Algoritma mantığı, kanıt ve karmaşıklık sezgisi, zorluk {difficulty}, aşama {stage}"

    def _stage(self, difficulty: int) -> str:
        if difficulty <= 1:
            return "genel_bilgi"
        if difficulty == 2:
            return "temel_beceri"
        if difficulty == 3:
            return "ileri_aktarım"
        if difficulty == 4:
            return "olimpiyat_hazırlık"
        return "olimpiyat_challenge"

    def _reason(self, progress: dict[str, Any]) -> str:
        if int(progress.get("total", 0)) == 0:
            return "domain_not_trained_yet"
        if float(progress.get("success_rate", 0.0)) < 0.8:
            return "success_rate_needs_repair"
        if int(progress.get("total", 0)) < int(progress.get("bank_count", 0)):
            return "coverage_gap"
        return "maintenance_and_harder_transfer"


curriculum_engine_service = CurriculumEngineService()
