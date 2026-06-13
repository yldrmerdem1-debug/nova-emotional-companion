from app.ml.inference.turkish_brain_router import turkish_brain_router
from app.services.response_generation_service import response_generation_service


BASE_CASES = [
    ("nasılsın", ["İyiyim", "kral"]),
    ("iyi misin", ["İyiyim", "sağ ol"]),
    ("selam kral", ["Selam", "kral"]),
    ("soru soracam", ["Sor", "dinliyorum"]),
    ("kanka bugün kötüyüm çözüm istemiyorum", ["çözüm modunu kapattım"]),
    ("sadece dinle akıl verme", ["dinliyorum"]),
    ("aga valla çok sinir oldum", ["Siniri aldım"]),
    ("uzatma direkt söyle", ["Net söylüyorum"]),
    ("C++ hata verdi önce neye bakayım", ["ilk hata"]),
    ("pointer array patladı", ["pointer"]),
    ("bilimsel anlat fizik formül", ["formül", "sadeleştirelim"]),
    ("bu aile meselesini hafızaya alma", ["hafızaya almıyorum"]),
    ("bana daha casual konuş resmi olma", ["doğal", "rahat"]),
]

GENERATED_CASE_GROUPS = [
    (
        ["nasılsın", "naber", "napıyorsun", "kanka nasılsın", "reis naber"],
        ["İyiyim", "buradayım", "Selam"],
    ),
    (
        [
            "kanka bugün kötüyüm çözüm istemiyorum",
            "sadece dinle akıl verme",
            "moralim bozuk sadece dinle",
            "canım sıkkın çözüm istemiyorum",
            "yargılama sadece dinle",
        ],
        ["dinliyorum", "çözüm modunu kapattım", "duyayım"],
    ),
    (
        [
            "aga valla çok sinir oldum",
            "harbi sinirliyim",
            "lan bıktım artık",
            "deliricem bu işten",
            "abi sinir oldum",
        ],
        ["Siniri aldım", "sakin", "netleştirelim"],
    ),
    (
        [
            "uzatma direkt söyle",
            "net konuş kral",
            "kısa kes",
            "lafı dolandırma",
            "direkt söyle ne yapayım",
        ],
        ["Net söylüyorum", "kısa", "direkt"],
    ),
    (
        [
            "C++ hata verdi önce neye bakayım",
            "compile error aldım",
            "debug yapalım hata var",
            "pointer array patladı",
            "python kod hata verdi",
        ],
        ["hata", "pointer", "debug", "satır"],
    ),
    (
        [
            "bilimsel anlat fizik formül",
            "matematik kanıt lazım",
            "hipotez nasıl kurulur",
            "akademik anlat",
            "formül mantığını anlat",
        ],
        ["formül", "Bilimsel", "sade", "kanıt", "kavram"],
    ),
    (
        [
            "bu aile meselesini hafızaya alma",
            "bunu kaydetme",
            "kalıcı tutma",
            "kayıt yok bunu",
            "hatırlama bunu",
        ],
        ["hafızaya almıyorum", "saklamadan"],
    ),
    (
        [
            "bana daha casual konuş resmi olma",
            "kanka deme kral de",
            "şakalı konuş",
            "sade konuş",
            "argo ama güvenli konuş",
        ],
        ["doğal", "rahat", "resmiyeti", "şakayla", "sade"],
    ),
]

NO_GO_PHRASES = [
    "AI service is not configured",
    "I am having trouble",
    "None",
    "null",
]


def main() -> None:
    total = 0
    failed = []
    brain_state_cache = {}
    cases = BASE_CASES + [
        (message, expected_parts)
        for messages, expected_parts in GENERATED_CASE_GROUPS
        for message in messages
    ]

    for index in range(250):
        for message, expected_parts in cases:
            total += 1
            if message not in brain_state_cache:
                brain_state_cache[message] = turkish_brain_router.predict_brain_state(message)
            brain_state = brain_state_cache[message]
            response = response_generation_service.generate_reply(message, brain_state)
            reply = response["reply"]

            if any(bad in reply for bad in NO_GO_PHRASES):
                failed.append((message, reply, "bad phrase"))
                continue

            if not any(part.casefold() in reply.casefold() for part in expected_parts):
                failed.append((message, reply, f"missing one of {expected_parts}"))

    print(f"response_eval_total={total}")
    print(f"response_eval_failed={len(failed)}")
    for message, reply, reason in failed[:20]:
        print("---")
        print(f"message={message}")
        print(f"reply={reply}")
        print(f"reason={reason}")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
