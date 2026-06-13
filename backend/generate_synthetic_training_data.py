import json
from itertools import product
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parent / "app" / "data" / "generated"

PREFIXES = ["", "kral ", "kanka ", "aga ", "abi ", "reis "]
SOFT_SUFFIXES = ["", " biraz açayım", " cidden", " ne yapalım", " yardım et", " bir bak"]
DIRECT_SUFFIXES = ["", " hemen", " kısa olsun", " net olsun", " fazla uzatma"]
PRIVACY_SUFFIXES = ["", " lütfen", " sakın kaydetme", " bu özel", " bunu gizli tut"]


SCENARIOS = [
    {
        "name": "listen_only",
        "messages": [
            "kanka bugün kötüyüm çözüm istemiyorum sadece dinle",
            "moralim bozuk akıl verme sadece yanımda ol",
            "canım sıkkın kral çözüm modu kapalı olsun",
            "bugün anlatmak istiyorum yargılama lütfen",
        ],
        "brain": {
            "route": "emotional_support",
            "emotion": "sad",
            "need": "listen",
            "tone": "soft",
            "style": "warm_elder_brother",
            "memory_allowed": True,
        },
        "reply": "Tamam kanka, çözüm modunu kapattım. Yargılamadan dinliyorum, anlat.",
        "notes": "Kullanıcı çözüm istemiyor; önce duygusal güven ve dinleme.",
    },
    {
        "name": "anger_deescalation",
        "messages": [
            "aga valla çok sinir oldum",
            "lan deliricem bu işten",
            "harbi bıktım artık",
            "abi kafayı yedim bu meseleye",
        ],
        "brain": {
            "route": "emotional_support",
            "emotion": "frustrated",
            "need": "vent",
            "tone": "anger_direct",
            "style": "mild_slang_safe",
            "memory_allowed": True,
        },
        "reply": "Siniri aldım kral. Ben sakin kalıyorum; önce neyin patladığını netleştirelim.",
        "notes": "Argo/sinir var; robot argo ile saldırmaz, sakinleştirir.",
    },
    {
        "name": "direct_no_fluff",
        "messages": [
            "uzatma direkt söyle",
            "net konuş kral ne yapayım",
            "lafı dolandırma kısa kes",
            "boş yapma direkt çözüm ver",
        ],
        "brain": {
            "route": "style_adaptation",
            "emotion": "focused",
            "need": "direct_solution",
            "tone": "serious_direct",
            "style": "direct_casual",
            "memory_allowed": True,
        },
        "reply": "Net söylüyorum kral: önce problemi tek cümleye indir, sonra ilk adımı seç.",
        "notes": "Kullanıcı kısa/net istiyor; uzun açıklama yok.",
    },
    {
        "name": "code_debug",
        "messages": [
            "C++ hata verdi önce neye bakayım",
            "compile error aldım kral",
            "pointer array patladı",
            "python kod hata verdi debug yapalım",
        ],
        "brain": {
            "route": "code_tutor",
            "emotion": "focused",
            "need": "debug_first_error",
            "tone": "calm_confident",
            "style": "student_friendly_direct",
            "memory_allowed": True,
        },
        "reply": "Önce ilk hata satırına bak kral. Hata mesajını ve ilgili 10 satırı at, birlikte ayıklayalım.",
        "notes": "Kodda ilk hata ve somut context isteme.",
    },
    {
        "name": "privacy_boundary",
        "messages": [
            "bu aile meselesini hafızaya alma",
            "bunu kaydetme kral",
            "kalıcı tutma bu konuyu",
            "kayıt yok bunu hatırlama",
        ],
        "brain": {
            "route": "privacy_boundary",
            "emotion": "neutral",
            "need": "do_not_store",
            "tone": "plain_direct",
            "style": "plain_direct",
            "memory_allowed": False,
        },
        "reply": "Tamam kral, bu konuyu hafızaya almıyorum. İçeriği saklamadan devam edebiliriz.",
        "notes": "Privacy isteği mutlak öncelik; memory kapalı.",
    },
    {
        "name": "style_preference",
        "messages": [
            "bana daha casual konuş resmi olma",
            "kanka deme kral de",
            "sade konuş fazla akademik olma",
            "şakalı konuş ama abartma",
        ],
        "brain": {
            "route": "style_adaptation",
            "emotion": "focused",
            "need": "style_adaptation",
            "tone": "natural_casual",
            "style": "casual_controlled",
            "memory_allowed": True,
        },
        "reply": "Tamam kral, daha doğal ve rahat konuşacağım. Resmiyeti azaltıyorum.",
        "notes": "Bu kişisel stil tercihi olarak öğrenilebilir.",
    },
]


PERSON_LEARNING_CASES = [
    {
        "user_message": "bana kral de kanka deme",
        "memory_candidate": {
            "type": "communication_preference",
            "key": "preferred_address",
            "value": "kral",
            "avoid": ["kanka"],
            "confidence": 0.95,
        },
        "ideal_reply": "Tamam kral, bundan sonra sana kral diye hitap ederim.",
        "should_store": True,
    },
    {
        "user_message": "resmi konuşmayı sevmiyorum kısa ve net ol",
        "memory_candidate": {
            "type": "communication_preference",
            "key": "reply_style",
            "value": "short_direct_casual",
            "confidence": 0.95,
        },
        "ideal_reply": "Anladım kral. Kısa, net ve rahat konuşacağım.",
        "should_store": True,
    },
    {
        "user_message": "aile konularımı kaydetme",
        "memory_candidate": {
            "type": "privacy_boundary",
            "key": "family_topics",
            "value": "do_not_store",
            "confidence": 1.0,
        },
        "ideal_reply": "Tamam, aile konularını hafızaya almıyorum.",
        "should_store": True,
    },
    {
        "user_message": "C++ öğreniyorum pointerlarda zorlanıyorum",
        "memory_candidate": {
            "type": "learning_profile",
            "key": "cpp_pointer_difficulty",
            "value": "needs_beginner_friendly_pointer_explanations",
            "confidence": 0.9,
        },
        "ideal_reply": "Not aldım kral: pointer konusunu daha sade ve örnekli anlatacağım.",
        "should_store": True,
    },
    {
        "user_message": "bugün kötüyüm ama bunu hafızaya alma",
        "memory_candidate": None,
        "ideal_reply": "Tamam kral, bunu kaydetmiyorum. İstersen sadece dinlerim.",
        "should_store": False,
    },
]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_response_rows() -> list[dict[str, Any]]:
    rows = []
    for scenario in SCENARIOS:
        for message in expand_messages(scenario["messages"], scenario["name"]):
            rows.append(
                {
                    "task_type": "response_generation",
                    "user_message": message,
                    "brain_state": scenario["brain"],
                    "ideal_reply": scenario["reply"],
                    "bad_reply_examples": bad_replies_for(scenario["name"]),
                    "notes": scenario["notes"],
                    "source": "synthetic_v1",
                }
            )
    return rows


def build_brain_eval_rows() -> list[dict[str, Any]]:
    rows = []
    for scenario in SCENARIOS:
        for message in expand_messages(scenario["messages"], scenario["name"]):
            rows.append(
                {
                    "task_type": "brain_state_eval",
                    "user_message": message,
                    "expected": scenario["brain"],
                    "source": "synthetic_v1",
                }
            )
    return rows


def build_person_learning_rows() -> list[dict[str, Any]]:
    rows = []
    for case in PERSON_LEARNING_CASES:
        for message in expand_person_message(case["user_message"]):
            rows.append(
                {
                    "task_type": "person_learning",
                    "user_message": message,
                    "memory_candidate": case["memory_candidate"],
                    "ideal_reply": case["ideal_reply"],
                    "should_store": case["should_store"],
                    "source": "synthetic_v1",
                }
            )
    return rows


def expand_messages(messages: list[str], scenario_name: str) -> list[str]:
    suffixes = PRIVACY_SUFFIXES if scenario_name == "privacy_boundary" else SOFT_SUFFIXES
    if scenario_name == "direct_no_fluff":
        suffixes = DIRECT_SUFFIXES

    expanded = set(messages)
    for prefix, message, suffix in product(PREFIXES, messages, suffixes):
        expanded.add(f"{prefix}{message}{suffix}".strip())
    return sorted(expanded)


def expand_person_message(message: str) -> list[str]:
    expanded = set()
    for prefix, suffix in product(PREFIXES, ["", " bundan sonra", " aklında tut", " benim tercihim bu"]):
        expanded.add(f"{prefix}{message}{suffix}".strip())
    return sorted(expanded)


def bad_replies_for(name: str) -> list[str]:
    common = ["Anladım.", "Devam edelim.", "Pozitif düşün."]
    specific = {
        "listen_only": ["Hemen çözüm üretelim.", "Bence şöyle yapmalısın."],
        "anger_deescalation": ["Sen de sakin ol artık.", "Bu kadar sinirlenme."],
        "direct_no_fluff": ["Öncelikle bu konunun tarihsel arka planı var."],
        "code_debug": ["Kodun tamamını ezberle.", "Rastgele satırları değiştir."],
        "privacy_boundary": ["Tamam, bunu hafızaya kaydediyorum."],
        "style_preference": ["Resmi bir üslupla yanıt vereceğim."],
    }
    return [*common, *specific.get(name, [])]


def main() -> None:
    response_rows = build_response_rows()
    brain_rows = build_brain_eval_rows()
    person_rows = build_person_learning_rows()

    write_jsonl(DATA_DIR / "response_training_synthetic.jsonl", response_rows)
    write_jsonl(DATA_DIR / "brain_eval_synthetic.jsonl", brain_rows)
    write_jsonl(DATA_DIR / "person_learning_synthetic.jsonl", person_rows)

    print(f"response_training_synthetic={len(response_rows)}")
    print(f"brain_eval_synthetic={len(brain_rows)}")
    print(f"person_learning_synthetic={len(person_rows)}")
    print(f"output_dir={DATA_DIR}")


if __name__ == "__main__":
    main()
