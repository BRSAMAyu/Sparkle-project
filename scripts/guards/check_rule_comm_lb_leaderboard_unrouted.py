#!/usr/bin/env python3
"""Rule COMM-LB: D-COMM-1 排行榜裁决固化——全站榜不路由，自我锚视图是唯一产品面.

裁决（v3-output/D-COMMUNITY/DESIGN.md §2.2/§3.2 + KNOWN_CODE_DEBT_LEDGER P1 #3
销账说明，2026-09）：
  * 全站综合榜（global/subject/streak/photon 等）保持 D17 默认隐藏——「大池 +
    异质水平 + 静态综合分」命中排行榜心理学的全部反面模式（打击中尾生）；
  * 唯一允许的产品面是「自我 7 日锚视图」（只跟自己历史比，
    engine GET /api/v1/leaderboards/self-anchor），后续 D-COMM-4 小队双视图
    榜上线时按同卡裁决扩面。

本守卫固化两条不变量（当前均为真，破坏即失败）：
  1. mobile/lib/app/routes.dart 不挂 LeaderboardScreen（全站榜 UI 无入口；
     `mobile/lib/features/leaderboard/` 仍是未路由死代码，属独立债务）；
  2. gateway leaderboards 代理组保持 wildcard-only（registerREST "/*path"）：
     任何在 leaderboards 组上显式注册具体榜面路由的行都是「把某张榜 promoted
     成产品路由」的动作，必须先改裁决再接线。

Escape hatch（两处皆适用）：行内注 `rule-comm-lb: ignore <reason>`。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MOBILE_ROUTES_PATH = REPO_ROOT / "mobile/lib/app/routes.dart"
PROXY_ROUTES_PATH = REPO_ROOT / "backend/gateway/internal/handler/proxy_routes.go"

LEADERBOARD_UI_RE = re.compile(r"LeaderboardScreen|leaderboard", re.IGNORECASE)
LEADERBOARD_GROUP_EXPLICIT_RE = re.compile(
    r'\bleaderboards\.(GET|POST|PUT|PATCH|DELETE|Any)\("'
)
IGNORE_RE = re.compile(r"rule-comm-lb:\s*ignore\s+.+", re.IGNORECASE)


def _scan_mobile_routes() -> list[str]:
    failures: list[str] = []
    if not MOBILE_ROUTES_PATH.exists():
        failures.append(f"required file missing: {MOBILE_ROUTES_PATH.relative_to(REPO_ROOT)}")
        return failures
    for lineno, raw in enumerate(MOBILE_ROUTES_PATH.read_text(encoding="utf-8").splitlines(), 1):
        if IGNORE_RE.search(raw):
            continue
        if LEADERBOARD_UI_RE.search(raw):
            failures.append(
                f"{MOBILE_ROUTES_PATH.relative_to(REPO_ROOT)}:{lineno}: 全站榜 UI 挂路由 "
                f"(D17 隐藏裁决被破坏; D-COMM-1/DESIGN §3.2——自我锚视图走独立 widget, "
                f"改造裁决前先更新本守卫并注 `rule-comm-lb: ignore <reason>`)"
            )
    return failures


def _scan_gateway() -> list[str]:
    failures: list[str] = []
    if not PROXY_ROUTES_PATH.exists():
        failures.append(f"required file missing: {PROXY_ROUTES_PATH.relative_to(REPO_ROOT)}")
        return failures
    text = PROXY_ROUTES_PATH.read_text(encoding="utf-8")
    if 'registerREST(leaderboards, "/*path")' not in text:
        failures.append(
            f"{PROXY_ROUTES_PATH.relative_to(REPO_ROOT)}: leaderboards wildcard "
            f'proxy (`registerREST(leaderboards, "/*path")`) missing — the '
            f"self-anchor surface became unreachable (gamification-eval P1-2 注册先例)"
        )
    for lineno, raw in enumerate(text.splitlines(), 1):
        if IGNORE_RE.search(raw):
            continue
        if LEADERBOARD_GROUP_EXPLICIT_RE.search(raw):
            failures.append(
                f"{PROXY_ROUTES_PATH.relative_to(REPO_ROOT)}:{lineno}: explicit "
                f"leaderboards route line — wildcard-only 是 D-COMM-1 裁决不变量 "
                f"(显式行=把具体榜面 promoted 成产品路由; 若确属自我锚面扩先例, "
                f"注 `rule-comm-lb: ignore <reason>` 并同步 DESIGN/台账)"
            )
    return failures


def main() -> int:
    failures = _scan_mobile_routes() + _scan_gateway()
    if failures:
        print("RULE COMM-LB FAILED: D-COMM-1 排行榜路由裁决被破坏")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(
        "RULE COMM-LB OK: 全站榜保持 D17 隐藏 (mobile 无 LeaderboardScreen 路由, "
        "gateway leaderboards wildcard-only), 自我锚视图是唯一产品面"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
