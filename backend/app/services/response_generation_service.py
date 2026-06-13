import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.local_llm_service import local_llm_service
from app.services.openai_service import openai_service
from app.services.vocabulary_style_service import vocabulary_style_service


@dataclass(frozen=True)
class ResponsePlan:
    intent: str
    strategy: str
    reply: str
    confidence: float
    source: str


class ResponseGenerationService:
    def __init__(self) -> None:
        self.style_corpus = self._load_style_corpus()

    def generate_reply(
        self,
        message: str,
        brain_state: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = context or {}
        plan = self._local_plan(message, brain_state, context)
        plan = self._apply_memory_personalization(plan, context)
        if self._should_skip_local_llm(plan, brain_state):
            local_llm_result = {
                "reply": None,
                "meta": {
                    "enabled": bool(settings.local_llm_provider.strip()),
                    "provider": settings.local_llm_provider.strip() or None,
                    "status": "skipped_fast_local_reply",
                },
            }
        else:
            local_llm_result = local_llm_service.generate_reply(message, brain_state, context, plan.reply)
            local_llm_reply = local_llm_result.get("reply")
            if isinstance(local_llm_reply, str) and local_llm_reply.strip():
                plan = ResponsePlan(
                    intent=plan.intent,
                    strategy=f"{plan.strategy}+local_llm",
                    reply=local_llm_reply.strip(),
                    confidence=max(plan.confidence, 0.88),
                    source="local_llm",
                )
        llm_reply = self._try_llm_reply(message, brain_state, plan, context)
        if llm_reply:
            plan = ResponsePlan(
                intent=plan.intent,
                strategy=plan.strategy,
                reply=llm_reply,
                confidence=max(plan.confidence, 0.82),
                source="llm_guided",
            )

        if plan.intent in {"greeting", "question_intent", "check_in", "care_check", "thanks", "positive_status"}:
            vocabulary_result = {
                "reply": plan.reply,
                "vocabulary_meta": {"applied": False, "reason": "micro_conversation"},
            }
        else:
            vocabulary_result = vocabulary_style_service.enrich_reply(plan.reply, brain_state, context)
        enriched_reply = vocabulary_result.get("reply")
        if isinstance(enriched_reply, str) and enriched_reply != plan.reply:
            plan = ResponsePlan(
                intent=plan.intent,
                strategy=f"{plan.strategy}+vocabulary_enriched",
                reply=enriched_reply,
                confidence=plan.confidence,
                source=plan.source,
            )
        cleaned_reply = self._calm_tone_cleanup(plan.reply)
        if cleaned_reply != plan.reply:
            plan = ResponsePlan(
                intent=plan.intent,
                strategy=f"{plan.strategy}+calm_tone_cleanup",
                reply=cleaned_reply,
                confidence=plan.confidence,
                source=plan.source,
            )

        return {
            "reply": plan.reply,
            "response_meta": {
                "intent": plan.intent,
                "strategy": plan.strategy,
                "confidence": plan.confidence,
                "source": plan.source,
                "local_llm": local_llm_result.get("meta"),
                "vocabulary": vocabulary_result.get("vocabulary_meta"),
                "reasoning_plan": context.get("reasoning_plan"),
                "knowledge_used": self._knowledge_ids(context.get("knowledge")),
                "synthesis": self._public_synthesis_meta(context.get("synthesis")),
                "long_context": self._public_long_context_meta(context.get("long_context")),
            },
        }

    def _should_skip_local_llm(self, plan: ResponsePlan, brain_state: dict[str, Any]) -> bool:
        if brain_state.get("route") == "privacy_boundary":
            return True
        if plan.confidence < 0.9:
            return False
        return plan.intent in {
            "anger_deescalation",
            "care_check",
            "check_in",
            "direct_no_fluff",
            "greeting",
            "learned_correction",
            "learned_good_reply",
            "positive_status",
            "question_intent",
            "style_adaptation",
            "thanks",
        }

    def _calm_tone_cleanup(self, reply: str) -> str:
        cleaned = reply
        replacements = {
            "kral, ": "",
            "Kral, ": "",
            " kral,": "",
            " Kral,": "",
            " kral.": ".",
            " Kral.": ".",
            " kral": "",
            " Kral": "",
        }
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        while "  " in cleaned:
            cleaned = cleaned.replace("  ", " ")
        return cleaned.strip()

    def _local_plan(
        self,
        message: str,
        brain_state: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ResponsePlan:
        context = context or {}
        normalized = self._normalize(message)
        route = str(brain_state.get("route", "general_chat"))
        emotion = str(brain_state.get("emotion", "neutral"))
        need = str(brain_state.get("need", "clarification"))
        support_mode = str(context.get("support_mode", "listen"))

        if route == "privacy_boundary" and self._explicit_privacy_request(normalized):
            return self._plan(
                "privacy_boundary",
                "respect_boundary",
                "Tamam, bu konuyu hafızaya almıyorum. İçeriği saklamadan devam edebiliriz.",
                1.0,
            )

        feedback_reply = self._feedback_reply(normalized)
        if feedback_reply:
            return feedback_reply

        memory_reply = self._memory_query_reply(normalized, context)
        if memory_reply:
            return memory_reply

        override_reply = self._high_priority_text_override(normalized)
        if override_reply:
            return override_reply

        if route == "privacy_boundary":
            return self._plan(
                "privacy_boundary",
                "respect_boundary",
                "Tamam, bu konuyu hafızaya almıyorum. İçeriği saklamadan devam edebiliriz.",
                1.0,
            )

        micro_reply = self._micro_conversation_reply(normalized)
        if micro_reply:
            return micro_reply

        if route == "emotional_support" or need == "listen" or (
            support_mode in {"listen", "think", "brief"} and route not in {"code_tutor", "scientific_tutor"}
        ):
            return self._emotional_support_reply(normalized, support_mode)

        corpus_reply = self._corpus_reply(normalized)
        if corpus_reply:
            return corpus_reply

        deep_reply = self._deep_reflection_reply(context)
        if deep_reply:
            return deep_reply

        synthesis_reply = self._synthesis_reply(context)
        if synthesis_reply:
            return synthesis_reply

        if route == "code_tutor":
            return self._code_reply(normalized)

        if route == "scientific_tutor":
            return self._scientific_reply(normalized)

        if route == "style_adaptation":
            return self._plan(
                "style_adaptation",
                "adapt_style",
                "Tamam, daha doğal, kısa ve rahat konuşacağım. Gereksiz hitapları azaltıyorum.",
                0.95,
            )

        if emotion == "frustrated" or need == "direct_solution":
            return self._plan(
                "direct_solution",
                "clarify_then_first_step",
                "Tamam, uzatmıyorum. Önce problemi tek cümleyle netleştirelim, sonra ilk uygulanabilir adımı seçelim.",
                0.88,
            )

        return self._general_reply(normalized)

    def _memory_query_reply(self, normalized: str, context: dict[str, Any]) -> ResponsePlan | None:
        if not self._contains_any(normalized, {"beni tanıyor musun", "beni taniyor musun", "ne hatırlıyorsun", "ne hatirliyorsun", "benim hakkımda ne biliyorsun"}):
            return None

        deep_memory = context.get("deep_memory", {})
        if not isinstance(deep_memory, dict):
            return None
        profile = deep_memory.get("profile_summary", {})
        if not isinstance(profile, dict):
            return None

        facts = []
        if profile.get("preferred_address"):
            facts.append(f"sana '{profile['preferred_address']}' diye hitap etmemi seviyorsun")
        if profile.get("reply_style"):
            facts.append(f"cevap stilin {profile['reply_style']}")
        learning = profile.get("learning_profile") or []
        if learning:
            first_learning = learning[-1]
            if isinstance(first_learning, dict):
                facts.append(f"{first_learning.get('key')} konusunda çalışıyorsun")
        tiny_details = profile.get("tiny_details") or []
        if tiny_details:
            facts.append("küçük notlarını da saklıyorum")

        if not facts:
            reply = "Seni konuşa konuşa tanıyorum. Şu an netleşmiş güçlü bir kişisel hafıza az, ama her düzeltmenle büyüyor."
        else:
            reply = "Evet, seni konuşa konuşa tanıyorum. Şu an hatırladıklarım: " + "; ".join(facts[:4]) + "."
        return self._plan("memory_reflection", "summarize_user_profile", reply, 0.93, source="deep_memory")

    def _high_priority_text_override(self, normalized: str) -> ResponsePlan | None:
        if self._contains_any(normalized, {"uzatma", "direkt söyle", "net konuş", "kısa kes", "lafı dolandırma"}):
            return self._plan(
                "direct_no_fluff",
                "serious_direct",
                "Net söylüyorum: önce problemi tek cümleye indir, sonra ilk adımı seç.",
                0.96,
                source="text_override",
            )
        if self._contains_any(normalized, {"sinir oldum", "sinirliyim", "bıktım", "biktim", "deliricem"}):
            return self._plan(
                "anger_deescalation",
                "anger_direct",
                "Siniri aldım. Ben sakin kalıyorum; önce neyin patladığını netleştirelim.",
                0.94,
                source="text_override",
            )
        return None

    def _micro_conversation_reply(self, normalized: str) -> ResponsePlan | None:
        if self._contains_any(normalized, {"soru soracam", "soru soracağım", "soru sorucam", "bir soru soracağım", "bir şey soracağım", "bir sey soracagim"}):
            return self._plan(
                "question_intent",
                "invite_question",
                "Sor, dinliyorum.",
                0.98,
            )
        if self._contains_any(normalized, {"nasılsın", "nasilsin", "naber", "napıyorsun", "napıyosun"}):
            return self._plan(
                "check_in",
                "warm_reciprocal",
                "İyiyim, buradayım. Sen nasılsın, bugün mod nasıl?",
                0.98,
            )
        if self._contains_any(normalized, {"iyi misin", "iyi misini"}):
            return self._plan(
                "care_check",
                "warm_reassurance",
                "İyiyim, sağ ol. Senin taraf nasıl, kafanı kurcalayan bir şey var mı?",
                0.98,
            )
        if self._contains_any(normalized, {"selam", "merhaba", "hey"}) or normalized in {"sa", "s.a", "s a"}:
            return self._plan(
                "greeting",
                "open_loop",
                "Selam. Buradayım, bugün neye bakalım?",
                0.97,
            )
        if normalized in {"iyi", "iyiyim", "fena değil", "fena degil"}:
            return self._plan(
                "positive_status",
                "gentle_continue",
                "Sevindim. Böyle devam edelim, istersen bir şeye beraber bakalım.",
                0.94,
            )
        if self._contains_any(normalized, {"teşekkür", "tesekkur", "sağ ol", "sag ol", "eyvallah"}):
            return self._plan(
                "thanks",
                "acknowledge",
                "Her zaman. Buradayım.",
                0.95,
            )
        return None

    def _corpus_reply(self, normalized: str) -> ResponsePlan | None:
        styles = self.style_corpus.get("styles", [])
        if not isinstance(styles, list):
            return None

        for style in styles:
            if not isinstance(style, dict):
                continue
            patterns = style.get("patterns", [])
            templates = style.get("templates", [])
            if not isinstance(patterns, list) or not isinstance(templates, list):
                continue
            if not any(isinstance(pattern, str) and pattern in normalized for pattern in patterns):
                continue

            reply = self._select_template([template for template in templates if isinstance(template, str)])
            if reply is None:
                continue
            return self._plan(
                str(style.get("id", "style_corpus")),
                str(style.get("tone", "natural_casual")),
                reply,
                0.91,
                source="style_corpus",
            )
        return None

    def _emotional_support_reply(self, normalized: str, support_mode: str = "listen") -> ResponsePlan:
        if support_mode == "brief":
            if self._contains_any(normalized, {"kötüyüm", "kotuyum", "moralim bozuk", "canım sıkkın", "canim sikkin"}):
                reply = "Duydum. Zor gelmiş olabilir; burada kısa ve sakin kalıyorum."
            else:
                reply = "Anladım. Kısa kalıyorum; buradayım."
            return self._plan("emotional_support", "brief_presence", reply, 0.94)

        if self._contains_any(normalized, {"çözüm istemiyorum", "cozum istemiyorum", "sadece dinle", "yargılama", "yargilama"}):
            reply = "Tamam, çözüm modunu kapattım. Yargılamadan dinliyorum; anlatmak istersen buradayım."
            return self._plan("emotional_support", "listen_first", reply, 0.95)

        if support_mode == "think":
            if self._contains_any(normalized, {"kötüyüm", "kotuyum", "moralim bozuk", "canım sıkkın", "canim sikkin"}):
                reply = "Bunun ağır geldiğini duyuyorum. İstersen önce neyin en çok yorduğunu ayıralım, sonra tek küçük adım seçelim."
            else:
                reply = "Anladım. Önce duygunu netleştirelim, sonra istersen birlikte küçük bir sonraki adım bulalım."
            return self._plan("emotional_support", "reflect_then_small_step", reply, 0.93)

        if self._contains_any(normalized, {"kötüyüm", "kotuyum", "moralim bozuk", "canım sıkkın", "canim sikkin"}):
            reply = "Bunu yaşaman yorucu gelmiş olabilir. Hemen çözmeye çalışmadan seni duyuyorum; istersen biraz daha anlat."
        else:
            reply = "Buradayım. İstersen sadece dinlerim; istersen daha sonra birlikte küçük bir adım düşünürüz."
        return self._plan("emotional_support", "listen_first", reply, 0.92)

    def _code_reply(self, normalized: str) -> ResponsePlan:
        if self._contains_any(normalized, {"hata", "compile", "derleme", "debug"}):
            reply = (
                "Önce ilk hata satırına bak. C++’ta ilk hata çoğu zaman sonraki hataları zincirleme üretir. "
                "Hata mesajını ve ilgili 10 satırı at, birlikte ayıklayalım."
            )
        elif self._contains_any(normalized, {"pointer", "array"}):
            reply = (
                "Burada kritik nokta bellek sınırı: pointer nereye bakıyor, array index’i sınır dışına çıkıyor mu "
                "önce onu kontrol edelim."
            )
        else:
            reply = "Kod tarafında önce hedefi netleştirelim: hata mı var, mantığı mı anlamak istiyorsun?"
        return self._plan("code_tutor", "debug_first_error", reply, 0.9)

    def _scientific_reply(self, normalized: str) -> ResponsePlan:
        if self._contains_any(normalized, {"formül", "kanıt", "kanit"}):
            reply = "Tamam. Önce formülün ne söylediğini sadeleştirelim, sonra hangi varsayımdan çıktığını adım adım kanıtlayalım."
        else:
            reply = "Tamam. Bilimsel ama anlaşılır gidelim: önce kavramı sade tanımlarız, sonra mantığını kurarız."
        return self._plan("scientific_tutor", "concept_then_reasoning", reply, 0.9)

    def _general_reply(self, normalized: str) -> ResponsePlan:
        if "?" in normalized:
            reply = "Güzel soru. Kısa cevapla başlayayım, sonra istersen derinleştiririz."
        elif len(normalized.split()) <= 2:
            reply = "Anladım. Biraz daha açarsan tam yerinden cevap vereyim."
        else:
            reply = "Anladım. Devam edelim; bunu birlikte netleştirebiliriz."
        return self._plan("general_chat", "helpful_next_step", reply, 0.74)

    def _deep_reflection_reply(self, context: dict[str, Any]) -> ResponsePlan | None:
        reflection = context.get("reflection")
        synthesis = context.get("synthesis")
        knowledge = context.get("knowledge", [])
        if not isinstance(reflection, dict) or not reflection.get("should_expand_answer"):
            return None
        if not isinstance(synthesis, dict):
            return None

        layers = reflection.get("layers", {})
        if not isinstance(layers, dict):
            layers = {}
        answer_points = synthesis.get("answer_points", [])
        if not isinstance(answer_points, list):
            answer_points = []

        knowledge_line = ""
        if isinstance(knowledge, list) and knowledge:
            summaries = [str(item.get("summary")) for item in knowledge[:2] if isinstance(item, dict) and item.get("summary")]
            if summaries:
                knowledge_line = " Lokal bilgiden çıkan ana dayanak: " + " ".join(summaries)

        philosophical_frame = reflection.get("philosophical_frame")
        angle_line = ""
        if isinstance(philosophical_frame, dict):
            angles = philosophical_frame.get("angles", [])
            if isinstance(angles, list) and angles:
                angle_line = " Bunu şu açılardan düşünebiliriz: " + ", ".join(str(angle) for angle in angles[:4]) + "."

        first_point = str(answer_points[0]) if answer_points else "Önce varsayımları ayırıp sonra sonuçları tartmak gerekir."
        reply = (
            "Derin bakalım. "
            f"Yüzeydeki istek: {layers.get('surface_intent', 'yardım almak')}. "
            f"Alt ihtiyaç: {layers.get('possible_hidden_need', 'netlik ve ilerleme')}. "
            f"En iyi hamle: {layers.get('best_next_move', first_point)}."
            f"{knowledge_line}{angle_line} "
            "Ben burada tek cevap vermek yerine anlamı, riski ve sonraki adımı beraber tartacağım."
        )
        return self._plan(
            "deep_reflection",
            str(synthesis.get("strategy", "reflect_then_answer")),
            reply,
            float(synthesis.get("confidence", 0.84)) if isinstance(synthesis.get("confidence"), (int, float)) else 0.84,
            source="reflection_engine",
        )

    def _synthesis_reply(self, context: dict[str, Any]) -> ResponsePlan | None:
        synthesis = context.get("synthesis")
        if not isinstance(synthesis, dict):
            return None

        draft = synthesis.get("draft")
        if not isinstance(draft, str) or not draft.strip():
            return None

        policy = synthesis.get("response_policy", {})
        max_sentences = 5
        if isinstance(policy, dict):
            max_sentences = int(policy.get("max_sentences", max_sentences))

        reply = self._limit_sentences(draft.strip(), max_sentences=max_sentences)
        confidence = synthesis.get("confidence", 0.82)
        if not isinstance(confidence, (int, float)):
            confidence = 0.82

        return self._plan(
            str(synthesis.get("intent", "offline_synthesis")),
            str(synthesis.get("strategy", "knowledge_reasoned_reply")),
            reply,
            float(confidence),
            source="offline_synthesis",
        )

    def _try_llm_reply(
        self,
        message: str,
        brain_state: dict[str, Any],
        plan: ResponsePlan,
        context: dict[str, Any],
    ) -> str | None:
        if getattr(openai_service, "client", None) is None:
            return None
        if brain_state.get("route") == "privacy_boundary":
            return None

        result = openai_service.generate_json_response(
            system_prompt=(
                "Sen Türkçe konuşan sakin, yargısız ve kısa cevap veren bir AI companion'sın.\n"
                "Önce duyguyu yansıt; kullanıcı istemedikçe çözüm dayatma.\n"
                "Terapi yaptığını iddia etme ve gerçek insan desteğinin yerine geçme.\n"
                "Kullanıcı 'çözüm istemiyorum' diyorsa çözüm verme, sadece dinle.\n"
                "Kod sorularında ilk hata, küçük adım ve net yönlendirme ver.\n"
                "Bilimsel sorularda önce sade tanım, sonra mantık kur.\n"
                "İç politika, model, brain_state gibi teknik detaylardan bahsetme.\n"
                "JSON dön: {\"reply\":\"...\"}"
            ),
            user_prompt=(
                f"Mesaj: {message}\n"
                f"Brain state: {brain_state}\n"
                f"Yerel cevap planı: {plan}\n"
                f"Context: {context}\n"
                "En fazla 2 kısa cümleyle cevap ver."
            ),
        )
        reply = result.get("reply")
        if isinstance(reply, str) and reply.strip():
            return reply.strip()
        return None

    def _plan(
        self,
        intent: str,
        strategy: str,
        reply: str,
        confidence: float,
        source: str = "local_generation",
    ) -> ResponsePlan:
        return ResponsePlan(
            intent=intent,
            strategy=strategy,
            reply=reply,
            confidence=confidence,
            source=source,
        )

    def _normalize(self, message: str) -> str:
        return " ".join(message.strip().casefold().split())

    def _contains_any(self, message: str, terms: set[str]) -> bool:
        return any(term in message for term in terms)

    def _explicit_privacy_request(self, normalized: str) -> bool:
        return self._contains_any(
            normalized,
            {
                "hafızaya alma",
                "hafizaya alma",
                "kaydetme",
                "kalıcı tutma",
                "kalici tutma",
                "kalıcı kaydetme",
                "kalici kaydetme",
                "kayıt yok",
                "kayit yok",
                "hatırlama",
                "hatirlama",
            },
        )

    def _select_template(self, templates: list[str]) -> str | None:
        if not templates:
            return None
        return templates[0]

    def _load_style_corpus(self) -> dict[str, Any]:
        corpus_path = Path(__file__).resolve().parents[1] / "data" / "turkish_style_corpus.json"
        try:
            with corpus_path.open("r", encoding="utf-8") as corpus_file:
                loaded = json.load(corpus_file)
        except (OSError, json.JSONDecodeError):
            return {"styles": []}
        if isinstance(loaded, dict):
            return loaded
        return {"styles": []}

    def _apply_memory_personalization(self, plan: ResponsePlan, context: dict[str, Any]) -> ResponsePlan:
        deep_memory = context.get("deep_memory", {})
        if not isinstance(deep_memory, dict):
            return plan
        profile = deep_memory.get("profile_summary", {})
        if not isinstance(profile, dict):
            return plan

        preferred_address = profile.get("preferred_address")
        avoid_address = profile.get("avoid_address") or []
        reply = plan.reply
        if isinstance(preferred_address, str) and preferred_address.strip():
            for avoided in avoid_address:
                if isinstance(avoided, str) and avoided.strip():
                    reply = reply.replace(avoided.strip(), preferred_address.strip())
            if "kral" in reply and preferred_address != "kral":
                reply = reply.replace("kral", preferred_address)

        reply_style = profile.get("reply_style")
        if reply_style == "short_direct" and plan.intent != "memory_reflection" and len(reply) > 140:
            reply = reply.split(".")[0].strip() + "."

        if reply == plan.reply:
            return plan
        return ResponsePlan(
            intent=plan.intent,
            strategy=f"{plan.strategy}+memory_personalized",
            reply=reply,
            confidence=plan.confidence,
            source=plan.source,
        )

    def _feedback_reply(self, normalized: str) -> ResponsePlan | None:
        for record in self._load_feedback_records():
            if self._normalize(str(record.get("user_message", ""))) != normalized:
                continue

            rating = str(record.get("rating", ""))
            if rating == "bad":
                ideal_reply = record.get("ideal_reply")
                if isinstance(ideal_reply, str) and ideal_reply.strip():
                    return self._plan(
                        "learned_correction",
                        "use_human_ideal_reply",
                        ideal_reply.strip(),
                        0.99,
                        source="feedback_corpus",
                    )
            if rating == "good":
                robot_reply = record.get("robot_reply")
                if isinstance(robot_reply, str) and robot_reply.strip():
                    return self._plan(
                        "learned_good_reply",
                        "reuse_approved_reply",
                        robot_reply.strip(),
                        0.93,
                        source="feedback_corpus",
                    )
        return None

    def _load_feedback_records(self) -> list[dict[str, Any]]:
        corpus_path = Path(__file__).resolve().parents[1] / "data" / "response_training_corpus.jsonl"
        try:
            lines = corpus_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []

        records: list[dict[str, Any]] = []
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                records.append(record)
        return records

    def _knowledge_ids(self, knowledge: Any) -> list[str]:
        if not isinstance(knowledge, list):
            return []
        return [str(item.get("id")) for item in knowledge if isinstance(item, dict) and item.get("id")]

    def _public_synthesis_meta(self, synthesis: Any) -> dict[str, Any] | None:
        if not isinstance(synthesis, dict):
            return None
        return {
            "intent": synthesis.get("intent"),
            "strategy": synthesis.get("strategy"),
            "knowledge_used": synthesis.get("knowledge_used", []),
            "memory_used": synthesis.get("memory_used", []),
            "confidence": synthesis.get("confidence"),
        }

    def _public_long_context_meta(self, long_context: Any) -> dict[str, Any] | None:
        if not isinstance(long_context, dict):
            return None
        summary = long_context.get("summary")
        if not isinstance(summary, dict):
            return None
        return {
            "conversation_count": summary.get("conversation_count"),
            "dominant_topics": summary.get("dominant_topics", [])[:3],
            "memory_strength": summary.get("memory_strength"),
        }

    def _limit_sentences(self, text: str, max_sentences: int) -> str:
        if max_sentences <= 0:
            return text

        sentence_parts = []
        current = []
        for character in text:
            current.append(character)
            if character in {".", "?", "!"}:
                sentence_parts.append("".join(current).strip())
                current = []
                if len(sentence_parts) >= max_sentences:
                    break
        if not sentence_parts:
            return text
        return " ".join(sentence_parts)


response_generation_service = ResponseGenerationService()
