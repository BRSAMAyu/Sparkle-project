#!/usr/bin/env python3
"""Sparkle 跨端 Journey Simulator Harness（B-03 基线）CLI。

用法：
  python3 run_journey.py --journey GJ01 --backend web \
      --app-url http://127.0.0.1:8437/ \
      [--evidence-root ../../../../v3-output/B-03/evidence]

  python3 run_journey.py --journey GJ01 --backend api
  python3 run_journey.py --list

失败语义：任一步骤 FAIL / DB 断言 FAIL / 环境不可用 => 退出码 1；
绝不允许"没找到目标/没找到模拟器=PASS"（任务卡验收第 2 条）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.loader import list_journeys, load_journey  # noqa: E402
from harness.runner import run_journey  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EVIDENCE_ROOT = REPO_ROOT / "v3-output" / "B-03" / "evidence"


def main() -> int:
    parser = argparse.ArgumentParser(description="Sparkle journey harness")
    parser.add_argument("--journey", help="journey id，如 GJ01")
    parser.add_argument("--backend", choices=["web", "api", "android", "macos"], default="api")
    parser.add_argument("--evidence-root", default=str(DEFAULT_EVIDENCE_ROOT))
    parser.add_argument("--gateway", default="http://localhost:8080")
    parser.add_argument("--app-url", default="http://127.0.0.1:8437/", help="web backend: Flutter Web 入口 URL")
    parser.add_argument("--headless", default="true", help="web backend: 无头模式")
    parser.add_argument("--cdp-port", default="0", help="web backend: 固定 CDP 调试端口（0=自动）")
    parser.add_argument("--avd", default="Medium_Phone_API_36.1", help="android backend: AVD 名")
    parser.add_argument("--serial", default="", help="android backend: 已连设备 serial（跳过 boot）")
    parser.add_argument("--apk", default="", help="android backend: APK 路径")
    parser.add_argument("--macos-test-file", default="integration_test/macos_journey_test.dart")
    parser.add_argument("--list", action="store_true", help="列出可用 journey 后退出")
    args = parser.parse_args()

    if args.list:
        for jid in list_journeys():
            spec = load_journey(jid)
            backends = {k: len(v) for k, v in spec.backends.items()}
            print(f"{spec.id}: {spec.title}\n  ref={spec.golden_ref}\n  backends={backends}")
        return 0

    if not args.journey:
        parser.error("需要 --journey 或 --list")

    driver_config = {"gateway": args.gateway}
    if args.backend == "web":
        driver_config.update(
            {
                "app_url": args.app_url,
                "headless": args.headless.lower() != "false",
                "cdp_port": int(args.cdp_port),
            }
        )
    elif args.backend == "android":
        driver_config.update(
            {"avd": args.avd, "apk": args.apk, "serial": args.serial or None}
        )
    elif args.backend == "macos":
        driver_config.update({"test_file": args.macos_test_file})

    manifest = run_journey(
        journey_id=args.journey,
        backend=args.backend,
        evidence_root=Path(args.evidence_root),
        driver_config=driver_config,
        repo_dir=REPO_ROOT,
    )
    return 0 if manifest.ok else 1


if __name__ == "__main__":
    sys.exit(main())
