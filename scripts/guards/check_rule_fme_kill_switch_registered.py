#!/usr/bin/env python3
"""Rule guard: FME kill switches must be registered iff they have real readers.

Background — V3-FIX-345 (wt655): the original contract ("a kill switch is
registered iff there is both a KillSwitchBinding entry and a settings
attribute") mandated registration without requiring any reader. That let a
zero-reader switch (`task_card_protocol_v2`) pose as live governance — the
TaskCardProtocol render chain (GET /tasks/{id}/card-protocol) never consults
the switch, so flipping it changed nothing (FIX-341 "fake switch" pattern).
The dead binding has been removed.

Current contract (inverted, fail-closed):
  1. Every entry in FmeKillSwitchService.FEATURE_BINDINGS must
     - point at a settings attribute declared with a tri-state default, and
     - have at least one production reader: a `get_feature_mode("<feature>")`
       call in backend/app OUTSIDE the kill-switch service itself.
  2. The retired zero-reader feature must not come back (explicit deny-list).

Exits 0 when every registered FME switch is real, non-zero otherwise.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICE_PATH = REPO_ROOT / "backend" / "app" / "services" / "fme_kill_switch_service.py"
SETTINGS_PATH = REPO_ROOT / "backend" / "app" / "config" / "settings.py"
APP_ROOT = REPO_ROOT / "backend" / "app"

RETIRED_FEATURES = {
    "task_card_protocol_v2": "zero production reader (V3-FIX-345 撤面)；重建须先把 "
    "card-protocol 渲染链接上 get_feature_mode 并更新本守卫",
}


def fail(msg: str) -> None:
    print(f"[RG-FME] FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    if not SERVICE_PATH.is_file():
        fail(f"missing kill switch service file: {SERVICE_PATH}")
    if not SETTINGS_PATH.is_file():
        fail(f"missing settings file: {SETTINGS_PATH}")

    service_src = SERVICE_PATH.read_text(encoding="utf-8")
    settings_src = SETTINGS_PATH.read_text(encoding="utf-8")

    bindings = {
        m.group(1): m.group(2)
        for m in re.finditer(r'"([a-z0-9_]+)":\s*KillSwitchBinding\(([^)]*)\)', service_src)
    }
    if not bindings:
        fail("no KillSwitchBinding entries found in FmeKillSwitchService.FEATURE_BINDINGS")

    for feature in RETIRED_FEATURES:
        if feature in bindings:
            fail(f"retired zero-reader feature {feature!r} re-registered: {RETIRED_FEATURES[feature]}")

    # 生产读者扫描面：服务自身之外的全部 backend/app Python 源
    reader_files = [
        p
        for p in APP_ROOT.rglob("*.py")
        if "__pycache__" not in p.parts and p.resolve() != SERVICE_PATH.resolve()
    ]

    for feature, body in bindings.items():
        # 绑定必须指向 settings 属性，且该属性以 tri-state 默认值声明。
        attr_match = re.search(r'settings_attr="([A-Za-z0-9_]+)"', body)
        if not attr_match:
            fail(f"binding for feature {feature!r} lacks settings_attr")
        settings_attr = attr_match.group(1)
        if not re.search(
            rf"\b{re.escape(settings_attr)}\s*:\s*str\s*=\s*\"(off|shadow|live)\"",
            settings_src,
        ):
            fail(
                f"settings attribute {settings_attr!r} missing or has invalid "
                "default (must be one of off/shadow/live)"
            )
        # 注册即须真实：存在服务外生产读者 get_feature_mode("<feature>")。
        reader_re = re.compile(rf'get_feature_mode\(\s*[\'"]{re.escape(feature)}[\'"]')
        if not any(reader_re.search(p.read_text(encoding="utf-8")) for p in reader_files):
            fail(
                f"feature {feature!r} registered but has no production reader "
                "(zero-reader switch = fake switch, V3-FIX-345)"
            )

    print(
        f"[RG-FME] OK — {len(bindings)} FME kill switch(es) registered with "
        "valid defaults and real production readers"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
