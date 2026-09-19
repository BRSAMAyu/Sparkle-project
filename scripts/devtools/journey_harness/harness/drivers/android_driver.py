"""Android backend driver（基线壳）：boot AVD → 装 APK → 启动 App → 截图取证。

基线范围（任务卡 B-03 Work#3 "GJ01 最小壳可启动并保存 evidence"）：
- 可重复启动：boot 指定 AVD（默认 Medium_Phone_API_36.1），安装/启动 APK；
- 证据：每步 screencap 截图 + logcat refs + 设备/构建信息；
- 完整 UI journey 步进（find/tap/type）为后续任务：Flutter 语义树在 Android 端
  按需构建（需无障碍服务激活），adb uiautomator 拿不到 Flutter 节点，
  基线如实标记 `ui_steps: unsupported`，不得用坐标盲点冒充通过。

失败语义：boot 失败/安装失败/启动失败一律 StepFailure → 退出非零；
绝不允许"没找到模拟器=PASS"。
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

from .base import BaseDriver, StepFailure

ADB_CANDIDATES = [
    str(Path.home() / "Library/Android/sdk/platform-tools/adb"),
    "/usr/local/bin/adb",
    "/opt/homebrew/bin/adb",
]


def _adb_path() -> str:
    for c in ADB_CANDIDATES:
        if Path(c).exists():
            return c
    import shutil

    found = shutil.which("adb")
    if found:
        return found
    raise StepFailure("未找到 adb（Android SDK platform-tools），android backend 无法启动")


class AndroidDriver(BaseDriver):
    name = "android"

    def __init__(self, evidence, config: dict[str, Any]) -> None:
        super().__init__(evidence, config)
        self.avd: str = str(self.config.get("avd", "Medium_Phone_API_36.1"))
        # 与 mobile/android/app/build.gradle.kts 的 applicationId 默认值一致
        # （APPLICATION_ID 未设置时为 com.example.sparkle）。
        self.package: str = str(self.config.get("package", "com.example.sparkle"))
        self.activity: str = str(self.config.get("activity", ".MainActivity"))
        self.apk: str = str(self.config.get("apk", ""))
        self.emulator_proc: subprocess.Popen | None = None
        self._shot_seq = 0

    # ---------- 基础 ----------
    def adb(self, *args: str, timeout: float = 60.0, check: bool = True) -> str:
        out = subprocess.run([_adb_path(), *args], capture_output=True, timeout=timeout)
        # logcat 里混有非 UTF-8 字节（native 日志/编码杂音），宽松解码保证据完整
        text = (out.stdout or b"").decode("utf-8", errors="replace")
        err = (out.stderr or b"").decode("utf-8", errors="replace")
        if check and out.returncode != 0:
            raise StepFailure(f"adb {' '.join(args[:3])}... 失败 rc={out.returncode}: {err[:300]}")
        return text.strip()

    def start(self) -> None:
        serial = self.config.get("serial")
        if serial:
            self.serial = str(serial)
            if not self._device_online():
                raise StepFailure(f"指定设备 {serial} 不在线")
            return
        emulator_bin = Path.home() / "Library/Android/sdk/emulator/emulator"
        if not emulator_bin.exists():
            raise StepFailure(f"未找到 emulator: {emulator_bin}")
        listing = subprocess.run(
            [str(emulator_bin), "-list-avds"], capture_output=True, text=True, timeout=30
        ).stdout.split()
        if self.avd not in listing:
            raise StepFailure(
                f"AVD {self.avd} 不存在；可用 AVDs={listing}（不支持时请在 journey platforms 里标记并说明原因）"
            )
        self.emulator_proc = subprocess.Popen(
            [
                str(emulator_bin),
                "-avd",
                self.avd,
                "-no-window",
                "-no-audio",
                "-no-boot-anim",
                "-gpu",
                "swiftshader_indirect",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 300
        while time.time() < deadline:
            devices = self.adb("devices", check=False)
            serials = [
                line.split()[0] for line in devices.splitlines()[1:] if line.strip().endswith("device")
            ]
            if serials:
                self.serial = serials[0]
                break
            time.sleep(3)
        else:
            raise StepFailure(f"模拟器 boot 超时（300s），AVD={self.avd}")
        # 等 sys.boot_completed
        deadline = time.time() + 240
        while time.time() < deadline:
            done = self.adb("-s", self.serial, "shell", "getprop", "sys.boot_completed", check=False)
            if done == "1":
                break
            time.sleep(3)
        else:
            raise StepFailure("模拟器 sys.boot_completed 等待超时")

    def _device_online(self) -> bool:
        devices = self.adb("devices", check=False)
        return any(
            line.startswith(str(self.serial)) and line.strip().endswith("device")
            for line in devices.splitlines()[1:]
        )

    def finish(self) -> None:
        # HEAVY 纪律：收工必须关模拟器
        if self.emulator_proc is not None:
            try:
                self.adb("-s", self.serial, "emu", "kill", check=False)
            except Exception:
                pass
            try:
                self.emulator_proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.emulator_proc.kill()
            self.emulator_proc = None

    # ---------- step handlers ----------
    def do_install_apk(self, apk: str = "") -> tuple[bool, str, list[str]]:
        path = apk or self.apk
        if not path or not Path(path).exists():
            raise StepFailure(f"APK 不存在: {path!r}（先 flutter build apk --debug，或在 config 指定 apk 路径）")
        self.adb("-s", self.serial, "install", "-r", path, timeout=300)
        # applicationId/launcher activity 不许猜：gradle.properties 的
        # APPLICATION_ID（com.sparkle.app）常与驱动默认值（com.example.sparkle）
        # 不一致；从 APK 本体读 badging 是唯一事实源。
        pkg, act = self._apk_identity(path)
        if pkg:
            self.package = pkg
        if act:
            self.activity = act
        return True, f"安装 {path}（package={self.package}, launchable={self.activity}）", []

    @staticmethod
    def _apk_identity(apk_path: str) -> tuple[str, str]:
        """从 APK badging 解析 (applicationId, launchable-activity)。失败返回 ('','')。"""
        sdk_bt = Path.home() / "Library/Android/sdk/build-tools"
        aapt2 = ""
        for bt in sorted(sdk_bt.glob("*"), reverse=True):
            cand = bt / "aapt2"
            if cand.exists():
                aapt2 = str(cand)
                break
        if not aapt2:
            return "", ""
        try:
            out = subprocess.run(
                [aapt2, "dump", "badging", apk_path], capture_output=True, text=True, timeout=60
            ).stdout
        except Exception:
            return "", ""
        pkg = act = ""
        for line in out.splitlines():
            if line.startswith("package:") and not pkg:
                for tok in line.split():
                    if tok.startswith("name="):
                        pkg = tok[5:].strip("'\"")
            elif line.startswith("launchable-activity:") and not act:
                for tok in line.split():
                    if tok.startswith("name="):
                        act = tok[5:].strip("'\"")
        return pkg, act

    def do_launch_app(self, screenshot: str = "launch") -> tuple[bool, str, list[str]]:
        # 解析 APK 真实 launcher activity（Flutter 工程 activity 类名常与
        # applicationId 不同包，如 com.sparkle.app.MainActivity，不能猜 .MainActivity）。
        resolved = self.adb(
            "-s", self.serial, "shell", "cmd", "package", "resolve-activity", "--brief",
            "-c", "android.intent.category.LAUNCHER", self.package, check=False, timeout=30,
        ).strip().splitlines()
        activity = self.activity
        if resolved:
            candidate = resolved[-1].strip()
            if "/" in candidate:
                activity = candidate
        self.adb(
            "-s", self.serial, "shell", "am", "start", "-n",
            f"{self.package}/{activity.lstrip('/')}" if "/" not in activity else activity,
            timeout=60,
        )
        time.sleep(8)  # 首帧 + 首屏网络
        # debug 构建首帧很慢：死等固定秒数常截到黑屏。轮询窗口焦点落到本 App
        # （UI 真正 attach），最多再等 45s，再留 4s 渲染稳定后截图。
        focus_deadline = time.time() + 45
        focused = False
        while time.time() < focus_deadline:
            focus = self.adb("-s", self.serial, "shell", "dumpsys", "window", check=False)
            if "mCurrentFocus" in focus and self.package in focus:
                focused = True
                break
            time.sleep(3)
        time.sleep(4)
        # 启动失败的诚实判定：检查进程在前台
        front = self.adb("-s", self.serial, "shell", "dumpsys", "activity", "activities", check=False)
        ok = self.package in front
        shot = self.screenshot(screenshot)
        if not ok:
            raise StepFailure(f"启动后 {self.package} 未出现在前台 activity 栈（见截图 {shot}）")
        return True, (
            f"App 已启动并在前台（package={self.package}, activity={activity}, "
            f"window_focus={focused}）"
        ), [shot]

    def do_screenshot(self, name: str) -> tuple[bool, str, list[str]]:
        return True, f"截图 {self.screenshot(name)}", []

    def do_logcat_snapshot(self, name: str = "logcat") -> tuple[bool, str, list[str]]:
        text = self.adb("-s", self.serial, "logcat", "-d", check=False, timeout=60)
        path = self.evidence.save_text(name + ".log", text)
        return True, f"logcat 快照 {len(text)} 字符", [str(path)]

    def do_assert_logcat_absent(self, patterns: list[str] | None = None) -> tuple[bool, str, list[str]]:
        """启动崩溃诚实判定：进程在前台 ≠ App 正常。

        2026-09-19 实测教训：App 启动即崩（IsarError 错误屏）时前台判定仍 PASS。
        journey 显式声明的 pattern 出现在 logcat 即 FAIL（默认盯启动 FATAL 标记）。
        """
        checked = list(patterns or ["FATAL ERROR DURING STARTUP"])
        text = self.adb("-s", self.serial, "logcat", "-d", check=False, timeout=60)
        hits = [p for p in checked if p in text]
        if hits:
            raise StepFailure(f"logcat 命中启动失败特征 {hits!r}（App 渲染了错误屏，前台判定不可信）")
        return True, f"logcat 无启动失败特征（检查了 {len(checked)} 个 pattern）", []

    def do_ui_steps_unsupported(self, reason: str = "") -> tuple[bool, str, list[str]]:
        """显式声明：本 backend 当前不支持步进 UI 操作（诚实标记，不冒充）。"""
        raise StepFailure(
            f"android backend 基线不支持 UI 步进（Flutter 语义树需无障碍激活，uiautomator 不可见）。{reason}"
        )

    def screenshot(self, name: str) -> str:
        self._shot_seq += 1
        safe = f"{self._shot_seq:02d}-{name}".replace("/", "_")
        # 必须用 raw bytes 捕获：走 self.adb()（text 模式）会损坏 PNG 二进制
        out = subprocess.run(
            [_adb_path(), "-s", self.serial, "exec-out", "screencap", "-p"],
            capture_output=True, timeout=60,
        )
        if out.returncode != 0 or not out.stdout:
            raise StepFailure(f"screencap 失败 rc={out.returncode}: {(out.stderr or b'')[:200]!r}")
        path = self.evidence.save_screenshot(f"{safe}.png", out.stdout)
        return str(path)
