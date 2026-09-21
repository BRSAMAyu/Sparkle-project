#!/usr/bin/env python3
"""visual_baseline CLI（B-04 视觉基线 harness）。

子命令：
    plan       打印 9 surfaces canonical states 定义表（后续 UI 卡按表复现）
    manifest   扫描截图目录生成 manifest.json（含 sha256，PNG 本身不入 git）
    verify     复验截图目录与 manifest 一致性（缺失/多余/篡改，失败非零退出）
    coverage   对照 canonical states 注册表输出覆盖缺口
    diff       对比两张截图（轻量指纹，不要求像素一致）或两份 manifest

示例：
    python3 visual_baseline.py plan
    python3 visual_baseline.py manifest v3-output/B-04/screenshots \\
        --build-sha $(git rev-parse HEAD) --platform android --viewport 412x916@2.6 \\
        --model "Medium_Phone_API_36.1" --gateway-url http://localhost:8080 \\
        --engine-url http://localhost:8000 -o v3-output/B-04/manifest.json
    python3 visual_baseline.py verify v3-output/B-04/screenshots --manifest v3-output/B-04/manifest.json
    python3 visual_baseline.py coverage v3-output/B-04/screenshots
    python3 visual_baseline.py diff shots/a.png shots/b.png
    python3 visual_baseline.py diff-manifest old.json new.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:  # 包内执行（python -m visual_baseline.visual_baseline）
    from .diffing import compare, diff_manifests
    from .manifest import build_manifest, load_manifest, verify_screens, write_manifest
    from .states import CANONICAL_STATES, iter_state_rows
except ImportError:  # 直接脚本执行（python visual_baseline.py ...）
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from visual_baseline.diffing import compare, diff_manifests
    from visual_baseline.manifest import (
        build_manifest,
        load_manifest,
        verify_screens,
        write_manifest,
    )
    from visual_baseline.states import CANONICAL_STATES, iter_state_rows


def cmd_plan(_args: argparse.Namespace) -> int:
    rows = iter_state_rows()
    print(f"canonical states 注册表：{len(CANONICAL_STATES)} 条（9 surfaces）\n")
    header = f"{'surface':<12}{'state':<22}{'persona':<12}entry"
    print(header)
    print("-" * len(header.expandtabs()))
    for surface, state, persona, _definition, entry in rows:
        print(f"{surface:<12}{state:<22}{persona:<12}{entry}")
    print("\n状态定义全文见 states.py（canonical states 单一事实源）。")
    return 0


def cmd_manifest(args: argparse.Namespace) -> int:
    manifest = build_manifest(
        args.screens_dir,
        build_sha=args.build_sha,
        platform=args.platform,
        viewport=args.viewport,
        model=args.model,
        gateway_url=args.gateway_url,
        engine_url=args.engine_url,
    )
    out = write_manifest(manifest, args.out)
    print(f"manifest 写入 {out}：{len(manifest['entries'])} 条目")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    report = verify_screens(args.screens_dir, manifest)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["ok"]:
        print("verify FAIL：截图目录与 manifest 不一致", file=sys.stderr)
        return 1
    print("verify OK")
    return 0


def cmd_coverage(args: argparse.Namespace) -> int:
    screens = Path(args.screens_dir)
    captured: set[tuple[str, str]] = set()
    if screens.is_dir():
        try:
            from .naming import parse_filename
        except ImportError:
            from visual_baseline.naming import parse_filename

        for png in screens.rglob("*.png"):
            try:
                f = parse_filename(png.name)
            except ValueError:
                continue
            captured.add((f["surface"], f["state"]))
    missing = [
        (cs.surface, cs.state_id, cs.persona)
        for cs in CANONICAL_STATES
        if (cs.surface, cs.state_id) not in captured
    ]
    covered = len(CANONICAL_STATES) - len(missing)
    print(f"coverage：{covered}/{len(CANONICAL_STATES)} canonical states 已采集")
    for surface, state, persona in missing:
        print(f"  MISSING: {surface}__{state}（persona={persona}）")
    return 0 if not missing else 1


def cmd_diff(args: argparse.Namespace) -> int:
    result = compare(args.a, args.b, similar_threshold=args.threshold)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_diff_manifest(args: argparse.Namespace) -> int:
    report = diff_manifests(load_manifest(args.a), load_manifest(args.b))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="visual_baseline", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("plan", help="打印 canonical states 定义表").set_defaults(func=cmd_plan)

    m = sub.add_parser("manifest", help="生成 manifest.json")
    m.add_argument("screens_dir")
    m.add_argument("--build-sha", required=True, help="完整 git SHA")
    m.add_argument("--platform", required=True, choices=sorted({"android", "web", "ios"}))
    m.add_argument("--viewport", required=True, help="如 412x916@2.6")
    m.add_argument("--model", default="")
    m.add_argument("--gateway-url", default="")
    m.add_argument("--engine-url", default="")
    m.add_argument("-o", "--out", required=True)
    m.set_defaults(func=cmd_manifest)

    v = sub.add_parser("verify", help="复验截图目录与 manifest 一致性")
    v.add_argument("screens_dir")
    v.add_argument("--manifest", required=True)
    v.set_defaults(func=cmd_verify)

    c = sub.add_parser("coverage", help="canonical states 覆盖检查")
    c.add_argument("screens_dir")
    c.set_defaults(func=cmd_coverage)

    d = sub.add_parser("diff", help="对比两张截图")
    d.add_argument("a")
    d.add_argument("b")
    d.add_argument("--threshold", type=float, default=0.08)
    d.set_defaults(func=cmd_diff)

    dm = sub.add_parser("diff-manifest", help="对比两份 manifest")
    dm.add_argument("a")
    dm.add_argument("b")
    dm.set_defaults(func=cmd_diff_manifest)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
