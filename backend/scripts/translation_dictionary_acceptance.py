from __future__ import annotations

import json
import os
from pathlib import Path
import time

import httpx

USERNAME = os.getenv("LOCAL_SMOKE_USERNAME", "chat_test")
PASSWORD = os.getenv("LOCAL_SMOKE_PASSWORD", "Chat123456")
BASE_URL = os.getenv("LOCAL_SMOKE_BASE_URL", "http://127.0.0.1:8080/api/v1")


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def login(client: httpx.Client) -> str:
    last_error = ""
    for attempt in range(5):
        response = client.post(
            f"{BASE_URL}/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        last_error = f"{response.status_code} {response.text[:400]}"
        if response.status_code != 429:
            break
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"login failed: {last_error}")


def main() -> None:
    package_preview_path = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "dictionaries"
        / "packages"
        / "oxford-oaldpe-starter.json.gz"
    )
    if package_preview_path.exists():
        package_preview_path.unlink()

    with httpx.Client(timeout=60.0) as client:
        token = login(client)
        headers = {"Authorization": f"Bearer {token}"}

        lookup = client.get(
            f"{BASE_URL}/vocabulary/lookup",
            params={"word": "test"},
            headers=headers,
        )
        ensure(lookup.status_code == 200, f"lookup failed: {lookup.status_code} {lookup.text[:400]}")
        lookup_payload = lookup.json()
        ensure(lookup_payload["source"] == "oaldpe", f"expected Oxford source, got: {lookup_payload}")
        ensure(len(lookup_payload.get("definitions", [])) > 0, "lookup did not return definitions")

        packages = client.get(
            f"{BASE_URL}/vocabulary/dictionary/packages",
            headers=headers,
        )
        ensure(packages.status_code == 200, f"packages failed: {packages.status_code} {packages.text[:400]}")
        package_list = packages.json()
        ensure(len(package_list) > 0, "dictionary packages list is empty")
        package_info = package_list[0]

        download = client.get(package_info["download_url"], headers=headers)
        ensure(download.status_code == 200, f"package download failed: {download.status_code}")
        ensure(len(download.content) > 0, "downloaded dictionary package is empty")

        translation = client.post(
            f"{BASE_URL}/translation/translate",
            headers=headers,
            json={
                "text": "test",
                "source_language": "en",
                "target_language": "zh-CN",
                "style": "natural",
            },
        )
        ensure(
            translation.status_code == 200 and translation.json().get("success") is True,
            f"translation failed: {translation.status_code} {translation.text[:400]}",
        )
        translation_payload = translation.json()

        add_word = client.post(
            f"{BASE_URL}/vocabulary/wordbook",
            headers=headers,
            json={
                "word": lookup_payload["word"],
                "definition": "; ".join(lookup_payload.get("definitions", [])),
                "phonetic": lookup_payload.get("phonetic"),
                "part_of_speech": lookup_payload.get("pos"),
                "context_sentence": translation_payload.get("translation"),
                "importance": 3,
            },
        )
        ensure(add_word.status_code == 200, f"add wordbook failed: {add_word.status_code} {add_word.text[:400]}")
        wordbook_payload = add_word.json()

        stats = client.get(f"{BASE_URL}/vocabulary/wordbook/stats", headers=headers)
        ensure(stats.status_code == 200, f"stats failed: {stats.status_code} {stats.text[:400]}")
        stats_payload = stats.json()
        ensure(stats_payload["total_words"] >= 1, f"unexpected stats: {stats_payload}")

    print(
        json.dumps(
            {
                "status": "ALL_OK",
                "lookup_source": lookup_payload["source"],
                "package_id": package_info["id"],
                "package_size": len(download.content),
                "translation_provider": translation_payload["meta"].get("provider"),
                "wordbook_word": wordbook_payload["word"],
                "total_words": stats_payload["total_words"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
