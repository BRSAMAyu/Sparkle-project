import json
from dataclasses import dataclass

import requests
from app.config import settings


BASE_URL = "http://127.0.0.1:8000/api/v1"
USERNAME = "chat_test"
PASSWORD = "Chat123456"


@dataclass
class AcceptanceState:
    token: str
    user_id: str


def _request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    expected_status: int = 200,
    **kwargs,
):
    headers = kwargs.pop("headers", {})
    if token:
        headers = {"Authorization": f"Bearer {token}", **headers}
    response = requests.request(
        method,
        f"{BASE_URL}{path}",
        headers=headers,
        timeout=60,
        **kwargs,
    )
    if response.status_code != expected_status:
        raise RuntimeError(
            f"{method} {path} expected {expected_status}, got {response.status_code}: {response.text[:500]}"
        )
    return response


def _login() -> AcceptanceState:
    response = _request(
        "POST",
        "/auth/login",
        json={"username": USERNAME, "password": PASSWORD},
    )
    payload = response.json()
    return AcceptanceState(
        token=payload["access_token"],
        user_id=payload["user"]["id"] if "user" in payload else "",
    )


def main() -> None:
    state = _login()

    stats = _request("GET", "/achievements/stats", token=state.token).json()
    achievements = _request(
        "GET",
        "/achievements?include_hidden=true&include_inactive=true&locale=zh",
        token=state.token,
    ).json()
    close_to_unlock = _request(
        "GET",
        "/achievements/close-to-unlock?locale=zh",
        token=state.token,
    ).json()
    templates = _request(
        "GET",
        "/achievements/share-templates?locale=zh",
        token=state.token,
    ).json()
    share_card = _request(
        "POST",
        "/achievements/streak_7/share?locale=zh",
        token=state.token,
        json={
            "template_id": "cosmic",
            "privacy": {
                "show_avatar": False,
                "show_unlock_date": True,
                "show_progress_stats": True,
                "show_first_unlocker_badge": True,
            },
        },
    ).json()
    titles = _request("GET", "/achievements/titles", token=state.token).json()
    skins = _request("GET", "/achievements/skins", token=state.token).json()

    balance = _request("GET", "/photons/balance", token=state.token).json()
    transactions = _request(
        "GET",
        "/photons/transactions?limit=5&offset=0",
        token=state.token,
    ).json()
    summary = _request(
        "GET",
        "/photons/transactions/summary?days=30",
        token=state.token,
    ).json()

    defaults = _request("GET", "/visual-elements/defaults?locale=zh").json()
    config = _request(
        "GET",
        "/visual-elements/config?locale=zh",
        token=state.token,
    ).json()
    all_visuals = _request(
        "GET",
        "/visual-elements?locale=zh",
        token=state.token,
    ).json()
    unlocked_visuals = _request(
        "GET",
        "/visual-elements/unlocked?locale=zh",
        token=state.token,
    ).json()
    locked_unlock = _request(
        "POST",
        "/visual-elements/unlock-by-achievement?achievement_id=streak_30&locale=zh",
        token=state.token,
        expected_status=403,
    ).json()
    internal_unlock = _request(
        "POST",
        "/visual-elements/unlock?locale=zh",
        token=state.token,
        headers={"X-Internal-Token": settings.INTERNAL_API_KEY},
        json={
            "element_id": "bg_aurora",
            "source": "achievement",
            "source_id": "streak_30",
        },
    ).json()
    equip_visual = _request(
        "POST",
        "/visual-elements/bg_aurora/equip?locale=zh",
        token=state.token,
    ).json()
    updated_config = _request(
        "GET",
        "/visual-elements/config?locale=zh",
        token=state.token,
    ).json()

    unlocked_achievements = [
        item["achievement"]["id"]
        for item in achievements["data"]
        if item["is_unlocked"]
    ]

    assert stats["total_achievements"] >= 10
    assert "streak_7" in unlocked_achievements
    assert close_to_unlock["count"] >= 1
    assert len(templates["templates"]) >= 4
    assert share_card["template_id"] == "cosmic"
    assert share_card["achievement"]["id"] == "streak_7"
    assert titles["equipped_title"] == "title_sprinter"
    assert any(item["is_equipped"] for item in skins["data"])
    assert balance["data"]["balance"] >= 50
    assert transactions["meta"]["total_count"] >= 1
    assert summary["data"]["total_income"] >= 50
    assert defaults["total"] >= 3
    assert "equipped_background" in config
    assert all_visuals["total"] >= defaults["total"]
    assert unlocked_visuals["total"] >= 0
    assert locked_unlock["detail"] == "Achievement not unlocked"
    assert internal_unlock["success"] is True
    assert internal_unlock["element"]["id"] == "bg_aurora"
    assert equip_visual["success"] is True
    assert updated_config["equipped_background"]["id"] == "bg_aurora"

    result = {
        "achievement_total": stats["total_achievements"],
        "achievement_unlocked": stats["unlocked_count"],
        "share_templates": [item["id"] for item in templates["templates"]],
        "photon_balance": balance["data"]["balance"],
        "photon_transaction_count": transactions["meta"]["total_count"],
        "visual_defaults": defaults["total"],
        "visual_total": all_visuals["total"],
        "equipped_background": updated_config["equipped_background"]["id"],
        "unlocked_achievements": unlocked_achievements,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("ALL_OK")


if __name__ == "__main__":
    main()
