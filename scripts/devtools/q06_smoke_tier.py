#!/usr/bin/env python3
"""Q-06 smoke: guest auth + tier 分层探针（free/deep/pro 各1条）打到 :50061.

用途：验证 wt406 bench 引擎可达、认证通过、tier 路由真分层（wt380/wt392 修复链）。
非交付物：探针脚本，报告引用其输出。
"""
from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

ENGINE_BACKEND = Path("/Users/brsama/code/GitHub/Sparkle-sysrev/wt406-q06-perf/backend")
GRPC_TARGET = "127.0.0.1:50061"
HTTP_BASE = "http://127.0.0.1:8000/api/v1"

sys.path.insert(0, str(ENGINE_BACKEND))
gen_dir = ENGINE_BACKEND / "app" / "gen" / "agent" / "v1"
sys.path.insert(0, str(gen_dir))
import agent_service_pb2 as pb2  # noqa: E402
import agent_service_pb2_grpc as pb2_grpc  # noqa: E402

import grpc  # noqa: E402
import httpx  # noqa: E402


def guest_auth(guest_id: str) -> tuple[str, str]:
    r = httpx.post(f"{HTTP_BASE}/auth/guest", params={"guest_id": guest_id}, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["access_token"], data["user"]["id"]


def probe(stub, token: str, user_id: str, label: str, text: str, *, is_pro: bool | None,
          extra: dict | None = None, chat_mode: str = "standard") -> dict:
    req = pb2.ChatRequest(
        user_id=user_id, message=text, session_id="", request_id=f"wt406-smoke-{label}-{uuid.uuid4().hex[:6]}",
        chat_mode=chat_mode,
    )
    if is_pro is not None:
        req.user_profile.is_pro = is_pro
    for k, v in (extra or {}).items():
        req.extra_context[k] = v
    meta = [("authorization", f"Bearer {token}"), ("user-id", user_id)]
    t0 = time.perf_counter()
    first_event = first_delta = None
    text_out = ""
    tiers: list[str] = []
    err = None
    try:
        for fr in stub.StreamChat(req, metadata=meta, timeout=120):
            t = time.perf_counter() - t0
            kind = fr.WhichOneof("content")
            md = {k: v for k, v in fr.metadata.items()} if fr.metadata else {}
            if first_event is None and (md or kind):
                first_event = t
            if "route" in md or "first_touch_tier" in md:
                tiers.append(md.get("first_touch_tier") or md.get("route", ""))
            if kind == "delta":
                if first_delta is None:
                    first_delta = t
                text_out += fr.delta
            elif kind == "full_text":
                text_out = fr.full_text
            elif kind == "error":
                err = {"code": str(fr.error.code), "message": fr.error.message[:200]}
    except Exception as exc:  # noqa: BLE001
        err = {"code": type(exc).__name__, "message": str(exc)[:200]}
    return {
        "label": label, "t_first_event": round(first_event, 3) if first_event else None,
        "ttft": round(first_delta, 3) if first_delta else None,
        "total": round(time.perf_counter() - t0, 3), "chars": len(text_out), "err": err,
        "tier_md": [t for t in tiers if t][:3], "head": text_out[:60].replace("\n", " "),
    }


def main() -> None:
    token_f, uid_f = guest_auth("wt406_q06_bench_free")
    print(f"auth free ok: {uid_f}")
    channel = grpc.insecure_channel(GRPC_TARGET)
    stub = pb2_grpc.AgentServiceStub(channel)
    rows = []
    # 1 free fast
    rows.append(probe(stub, token_f, uid_f, "free-fast", "你好", is_pro=None))
    # 2 free deep（期望仍走生成链，tier 不变）
    rows.append(probe(stub, token_f, uid_f, "free-deep", "用认知负荷理论解释为什么边看视频边记笔记效率低",
                      is_pro=None, extra={"reasoning_mode": "deep"}))
    # 3 pro 车道（gateway 忠实形态：user_profile.is_pro=true + deep）
    rows.append(probe(stub, token_f, uid_f, "pro-deep", "比较主动回忆与重复阅读的适用场景和证据强度",
                      is_pro=True, extra={"reasoning_mode": "deep"}))
    # 4 提权探针：free 账号伪造 user_tier=pro + user_profile.is_pro=False → 期望 wt392 门封堵
    rows.append(probe(stub, token_f, uid_f, "free-claims-pro", "什么是间隔效应",
                      is_pro=False, extra={"user_tier": "pro", "reasoning_mode": "deep"}))
    channel.close()
    print(json.dumps(rows, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
