import json
import urllib.error
import urllib.request


API_BASE_URL = "http://localhost:8000/api"
USER_ID = "11111111-1111-1111-1111-111111111111"


def post_chat(payload: dict) -> dict:
    request = urllib.request.Request(
        f"{API_BASE_URL}/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(path: str) -> dict | list:
    with urllib.request.urlopen(f"{API_BASE_URL}{path}") as response:
        return json.loads(response.read().decode("utf-8"))


def print_json(title: str, data: dict | list) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def main() -> None:
    try:
        private_response = post_chat(
            {
                "user_id": USER_ID,
                "message": "Kral ben çok büyük bir AI robot yapmak istiyorum, sıradan şeylerden nefret ediyorum.",
                "context_mode": "private",
                "present_people": [],
            }
        )
        print_json("1. Private Context Response", private_response)

        person_response = post_chat(
            {
                "user_id": USER_ID,
                "conversation_id": private_response["conversation_id"],
                "message": "Bugün Ali'ye robot fikrini anlattım, bayağı heyecanlandı.",
                "context_mode": "private",
                "present_people": [],
            }
        )
        print_json("2. Mention Person Response", person_response)

        public_response = post_chat(
            {
                "user_id": USER_ID,
                "conversation_id": private_response["conversation_id"],
                "message": "Geçen özel konuştuğumuz şeyi söyle.",
                "context_mode": "friends_present",
                "present_people": ["Ali"],
            }
        )
        print_json("3. Public Context Response", public_response)

        print_json("Debug Memories", get_json(f"/users/{USER_ID}/memories"))
        print_json("Debug People", get_json(f"/users/{USER_ID}/people"))
        print_json("Debug Events", get_json(f"/users/{USER_ID}/events"))
    except urllib.error.URLError as error:
        print(f"Request failed. Is the backend running? {error}")


if __name__ == "__main__":
    main()
