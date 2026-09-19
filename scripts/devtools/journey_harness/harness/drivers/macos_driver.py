"""macOS backend driver：包装既有 mobile/integration_test/macos_journey_test.dart。

复用优先：macOS 真实 UI journey（登录→访客→dashboard→星图→聊天流式→中断→
设置→登出）已有权威实现 macos_journey_test.dart（finder 级驱动 + 引擎帧截图），
本 driver 不重建第二套，只负责：
  1. 校验 flutter/目标设备可用（不可用 => StepFailure，非零退出）；
  2. 以 `flutter test integration_test/macos_journey_test.dart -d macos` 运行；
  3. 解析 JOURNEY_DONE/SHOT_RESULT 输出、留存运行日志与截图目录引用；
  4. flutter test 失败/超时一律失败（不允许"没跑起来=PASS"）。
"""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from .base import BaseDriver, StepFailure


class MacosDriver(BaseDriver):
    name = "macos"

    def __init__(self, evidence, config: dict[str, Any]) -> None:
        super().__init__(evidence, config)
        self.mobile_dir = Path(
            self.config.get("mobile_dir")
            or Path(__file__).resolve().parents[5] / "mobile"
        )
        self.test_file = str(
            self.config.get("test_file", "integration_test/macos_journey_test.dart")
        )
        # 默认把引擎帧截图注入本 run 的 evidence 目录（worktree 内，随 run 归档）。
        self.screenshot_dest = self.config.get("screenshot_dest") or str(
            Path(self.evidence.run_dir) / "screenshots"
        )
        self.timeout_min = int(self.config.get("timeout_min", 25))
        self.process: subprocess.Popen | None = None

    def start(self) -> None:
        if not (self.mobile_dir / "pubspec.yaml").exists():
            raise StepFailure(f"mobile 目录不存在: {self.mobile_dir}")
        flutter = shutil.which("flutter")
        if not flutter:
            raise StepFailure("未找到 flutter 工具链，macos backend 无法启动")
        devices = subprocess.run(
            [flutter, "devices", "--machine"], cwd=self.mobile_dir,
            capture_output=True, text=True, timeout=120,
        )
        devices_stdout = devices.stdout or ""
        if '"platform": "darwin"' not in devices_stdout.replace("macos", "darwin") and "macOS" not in devices_stdout:
            raise StepFailure("flutter devices 中未见 macOS 桌面目标（不支持时须在 journey 标记原因）")

    def finish(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()

    def do_run_journey_test(self, screenshot: str = "after_journey") -> tuple[bool, str, list[str]]:
        """运行既有 macos_journey_test.dart 并判定结果。"""
        flutter = shutil.which("flutter")
        env_extra = []
        if self.screenshot_dest:
            env_extra = ["--dart-define", f"JOURNEY_SHOT_DEST={self.screenshot_dest}"]
        log_path = self.mobile_dir / "build" / "journey_macos_last_run.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [flutter, "test", self.test_file, "-d", "macos", *env_extra]
        t0 = time.time()
        with log_path.open("w", encoding="utf-8") as log_fh:
            proc = subprocess.run(
                cmd, cwd=self.mobile_dir, stdout=log_fh, stderr=subprocess.STDOUT,
                timeout=self.timeout_min * 60,
            )
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        self.evidence.log_api("flutter_test", {"cmd": " ".join(cmd), "elapsed_s": round(time.time() - t0, 1)})
        saved = self.evidence.save_text("macos_journey_run.log", log_text[-400_000:])

        done = re.search(r"JOURNEY_DONE failures=(\d+)", log_text)
        shots = re.findall(r"SHOT_RESULT (\S+) ok", log_text)
        if proc.returncode != 0:
            raise StepFailure(
                f"flutter test 退出码 {proc.returncode}（非零=失败）。日志={saved}；JOURNEY_DONE={done.group(0) if done else '未见'}"
            )
        if not done:
            raise StepFailure(f"输出未见 JOURNEY_DONE 标记（测试未完成即退出 0，视为失败）。日志={saved}")
        failures = int(done.group(1))
        if failures > 0:
            raise StepFailure(f"journey 软失败 {failures} 项。日志={saved}")
        return True, f"macos journey 通过，截图 {len(shots)} 张，日志={saved}", [str(saved)]
