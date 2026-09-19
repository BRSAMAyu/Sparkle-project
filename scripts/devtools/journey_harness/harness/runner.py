"""journey runner：按 backend 执行 journey，任何失败非零退出。"""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .drivers.android_driver import AndroidDriver
from .drivers.api_driver import ApiDriver
from .drivers.base import BaseDriver, StepFailure
from .drivers.macos_driver import MacosDriver
from .drivers.web_driver import WebDriver
from .evidence import EvidenceCollector, utcnow_iso
from .loader import load_journey
from .models import RunManifest, StepResult

DRIVERS: dict[str, type[BaseDriver]] = {
    "web": WebDriver,
    "api": ApiDriver,
    "android": AndroidDriver,
    "macos": MacosDriver,
}

NON_UI_BACKENDS = {"api"}


def git_sha(repo_dir: Path, allow_dirty_suffix: bool = True) -> str:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_dir, capture_output=True, text=True, timeout=15
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo_dir, capture_output=True, text=True, timeout=15
        ).stdout.strip()
        if allow_dirty_suffix and dirty:
            dirty_count = len(dirty.splitlines())
            sha += f"-dirty({dirty_count} files, not committed by design)"
        return sha
    except Exception as exc:
        return f"unknown({exc})"


def run_journey(
    journey_id: str,
    backend: str,
    evidence_root: Path,
    driver_config: dict[str, Any] | None = None,
    repo_dir: Path | None = None,
) -> RunManifest:
    if backend not in DRIVERS:
        raise SystemExit(f"未知 backend {backend!r}；可选：{sorted(DRIVERS)}")
    repo_dir = repo_dir or Path(__file__).resolve().parents[3]
    journey = load_journey(journey_id)
    steps = journey.steps_for(backend)

    run_id = f"{journey.id.lower()}_{backend}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:4]}"
    evidence = EvidenceCollector(evidence_root, run_id)
    manifest = RunManifest(
        journey_id=journey.id,
        backend=backend,
        run_id=run_id,
        started_at=utcnow_iso(),
        base_sha=git_sha(repo_dir, allow_dirty_suffix=False),
        final_sha=git_sha(repo_dir),
        gateway=str((driver_config or {}).get("gateway", "http://localhost:8080")),
        app_build=_collect_app_build(backend, driver_config or {}),
        device=_collect_device(backend, driver_config or {}),
    )
    if backend in NON_UI_BACKENDS:
        manifest.summary = "non-ui lane（API/WS 直驱真实后端，不冒充 UI 实测）"

    driver = DRIVERS[backend](evidence, driver_config or {})
    print(f"== journey {journey.id} [{backend}] run={run_id} ==\n  {journey.title}")
    failed = False
    # start 失败（浏览器/模拟器/Flutter 工具链不可用等）也必须落盘 FAIL 证据并
    # 非零退出——绝不允许"环境没找到"被当成 PASS，也不允许失败不留 run 记录。
    try:
        driver.start()
    except StepFailure as exc:
        failed = True
        manifest.steps.append(
            StepResult(name="driver_start", action="start", ok=False,
                       detail=f"StepFailure: {exc}", duration_ms=0)
        )
        print(f"  FAIL | driver_start | {exc}")
    except Exception as exc:  # 未预期异常同样记 FAIL
        failed = True
        manifest.steps.append(
            StepResult(name="driver_start", action="start", ok=False,
                       detail=f"UnexpectedError: {type(exc).__name__}: {exc}", duration_ms=0)
        )
        print(f"  FAIL | driver_start | {exc}")
    # start 成功后补写实况设备信息（如 boot 后才可知的 emulator-XXXX serial），
    # manifest 的 device 字段必须反映真实运行目标而不是配置兜底值。
    if not failed:
        serial = getattr(driver, "serial", None)
        if backend == "android" and serial:
            manifest.device = (
                f"AVD:{(driver_config or {}).get('avd', 'Medium_Phone_API_36.1')} serial={serial}"
            )
    try:
        for step in ([] if failed else steps):
            t0 = time.time()
            try:
                ok, detail, artifacts = driver.execute(step.action, _render_args(dict(step.args), run_id))
                detail = driver.check_assert(step.assert_, detail)
            except StepFailure as exc:
                ok, detail, artifacts = False, f"StepFailure: {exc}", []
            except Exception as exc:  # 未预期异常也必须记 FAIL，不允许吞掉
                ok, detail, artifacts = False, f"UnexpectedError: {type(exc).__name__}: {exc}", []
            result = StepResult(
                name=step.name,
                action=step.action,
                ok=ok,
                detail=detail,
                duration_ms=int((time.time() - t0) * 1000),
                artifacts=[str(a) for a in artifacts],
            )
            manifest.steps.append(result)
            print(f"  {'PASS' if ok else 'FAIL'} | {step.name} | {detail}")
            # 失败时留一张现场截图（支持截图的 backend）
            if not ok and hasattr(driver, "screenshot"):
                try:
                    shot = driver.screenshot(f"FAIL_{_slug(step.name)}")  # type: ignore[attr-defined]
                    result.artifacts.append(str(shot))
                except Exception:
                    pass
            if not ok:
                failed = True
                break

        # journey 级 DB 断言（只读；可用 "backends": [...] 限定适用通道——
        # 不同平台的同一 journey 落库语义可以不同，如 macOS 访客 journey 不产生 email 注册行）
        if not failed:
            for i, spec in enumerate(journey.db_asserts):
                scoped = spec.get("backends")
                if scoped and backend not in scoped:
                    continue
                sql = str(spec.get("sql", ""))
                label = str(spec.get("label", f"db_assert#{i}"))
                value = ""
                try:
                    if not sql.strip().lower().startswith("select"):
                        raise StepFailure(f"db_assert 只允许 SELECT: {label}")
                    sql_rendered = _render_sql(sql, driver_state=getattr(driver, "state", {}))
                    value = evidence.db_scalar(sql_rendered)
                except Exception as exc:  # DB 探针异常也必须记 FAIL 并落盘，不允许炸掉整个 run 的证据
                    value = f"<error: {type(exc).__name__}: {exc}>"
                    expect = "<error>"
                    ok = False
                    result = StepResult(
                        name=label, action="db_assert", ok=False,
                        detail=f"db_assert 异常: {exc}", duration_ms=0,
                    )
                    manifest.steps.append(result)
                    print(f"  FAIL | {label} | {exc}")
                    failed = True
                    break
                expect = str(spec.get("expect", "nonzero"))
                ok = (value not in ("", "0")) if expect == "nonzero" else (value == expect)
                result = StepResult(
                    name=label,
                    action="db_assert",
                    ok=ok,
                    detail=f"expect={expect} got={value!r}",
                    duration_ms=0,
                )
                manifest.steps.append(result)
                print(f"  {'PASS' if ok else 'FAIL'} | {label} | got={value!r}")
                if not ok:
                    failed = True
                    break
    finally:
        driver.finish()

    manifest.finished_at = utcnow_iso()
    manifest.ok = not failed
    manifest.summary = manifest.summary or ("all steps passed" if not failed else "FAILED (see steps.json)")
    evidence.write_steps(manifest.steps)
    evidence.write_manifest(manifest)
    # journey 元信息快照（可复现）
    evidence.save_text(
        "journey_definition.json",
        json.dumps(
            {
                "id": journey.id,
                "title": journey.title,
                "golden_ref": journey.golden_ref,
                "description": journey.description,
                "platforms": journey.platforms,
                "backend": backend,
                "steps": journey.backends[backend] and [
                    {"name": s.name, "action": s.action, "args": s.args} for s in steps
                ],
                "definition_file": str(journey.path),
            },
            ensure_ascii=False,
            indent=2,
        ),
    )
    print(f"== run {run_id}: {'PASS' if manifest.ok else 'FAIL'} ==")
    print(f"   evidence: {evidence.run_dir}")
    return manifest


def _render_args(args: dict[str, Any], run_id: str) -> dict[str, Any]:
    """把步骤参数里的 %RUN%（run 唯一后缀）替换为本次 run 标识。"""
    token = "".join(c for c in run_id if c.isalnum())[-12:]

    def walk(value: Any) -> Any:
        if isinstance(value, str):
            return value.replace("%RUN%", token).replace("%RUN_ID%", run_id)
        if isinstance(value, list):
            return [walk(v) for v in value]
        if isinstance(value, dict):
            return {k: walk(v) for k, v in value.items()}
        return value

    return walk(args)


def _render_sql(sql: str, driver_state: dict[str, Any]) -> str:
    """把 SQL 中的 {{accounts.default.user_id}} 之类占位符替换为运行期上下文。"""
    out = sql
    import re

    for match in re.findall(r"\{\{([^}]+)\}\}", sql):
        cur: Any = driver_state
        for part in match.strip().split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                cur = None
                break
        out = out.replace("{{" + match + "}}", str(cur))
    return out


def _collect_app_build(backend: str, config: dict[str, Any]) -> dict[str, Any]:
    build: dict[str, Any] = {}
    mobile_dir = Path(__file__).resolve().parents[4] / "mobile"
    pubspec = mobile_dir / "pubspec.yaml"
    if pubspec.exists():
        for line in pubspec.read_text(encoding="utf-8").splitlines()[:8]:
            if line.startswith(("version:", "name:")):
                build[line.split(":")[0]] = line.split(":", 1)[1].strip()
    if backend == "web":
        web_build = mobile_dir / "build" / "web"
        build["web_built_at"] = (
            datetime.fromtimestamp(web_build.stat().st_mtime).isoformat(timespec="seconds")
            if web_build.exists() else "missing (serve externally)"
        )
        build["flutter_mode"] = "release (flutter build web)"
        if config.get("app_url"):
            build["served_url"] = str(config["app_url"])
    elif backend == "android":
        build["apk"] = str(config.get("apk", ""))
    elif backend == "macos":
        build["test_file"] = str(config.get("test_file", "integration_test/macos_journey_test.dart"))
    return build


def _collect_device(backend: str, config: dict[str, Any]) -> str:
    if backend == "web":
        chrome = config.get("chrome_path") or "Google Chrome"
        return f"{Path(chrome).name if str(chrome).startswith('/') else chrome} headless={config.get('headless', True)} viewport={config.get('viewport_width', 1280)}x{config.get('viewport_height', 800)}"
    if backend == "android":
        return f"AVD:{config.get('avd', 'Medium_Phone_API_36.1')} serial={config.get('serial', 'auto')}"
    if backend == "macos":
        return "macOS desktop (flutter test -d macos)"
    if backend == "api":
        return f"gateway:{config.get('gateway', 'http://localhost:8080')}"
    return backend


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text[:30]) or "step"
