"""U-09 三端（Android / Web / macOS）截图矩阵：可执行清单与 diff report 模板。

定位（不重建真源）：
- canonical states 注册表与命名规范仍是 B-04 的 ``states.py`` / ``naming.py``；
  本模块只做「三端采集计划」的**派生视图**：state × platform × viewport
  逐行展开，输出可勾选采集清单与 A/B diff report 模板。
- headless（无浏览器/模拟器）契约测试在 mobile
  ``test/widget/u09_platform_render_contract_test.dart``；本模块服务
  真机批次段（主会话执行，证据进 HUMAN_INBOX）。

viewport 口径（v3/04_ux/MULTIPLATFORM.md）：
- Android：1080×2400 @3（canonical 采集端，DPR 3 → 逻辑 360×800）；
- Web：1280×720（桌面宽）+ 360×720（mobile-like 宽），DPR 1；
- macOS：800×600（小窗）+ 1280×800（正常窗），DPR 2。
"""

from __future__ import annotations

from dataclasses import dataclass

from .naming import NamingError, screenshot_name
from .states import CANONICAL_STATES

# U-09 卡口径的三端（B-04 全集另含 ios：本机不可采，登记不采）。
U09_PLATFORMS: tuple[str, ...] = ("android", "web", "macos")

# 每端采集 viewport（naming.viewport 段语法：宽x高@缩放）。
U09_VIEWPORTS: dict[str, tuple[str, ...]] = {
    "android": ("1080x2400@3.0",),
    "web": ("1280x720@1.0", "360x720@1.0"),
    "macos": ("800x600@2.0", "1280x800@2.0"),
}

# MULTIPLATFORM.md 底线（逐面通用断言点）。
_BASE_ASSERTIONS = (
    "核心层级结构一致；核心文案一致；"
    "状态语义（空/加载/长等待/错误/离线/部分数据）一致且有下一步"
)

# 逐面补充断言点（B-04 states.py definition 字段的对齐细化）。
_SURFACE_ASSERTIONS: dict[str, str] = {
    "onboarding": "首引导步骤指示与主 CTA 位置/文案",
    "home": "今日任务卡、目标/星标入口、14 天趋势入口在位",
    "chat": "消息气泡层次、引用/证据块、输入条+发送键可达",
    "goal": "目标卡信息密度与进度表达一致",
    "task": "任务行可点击性与状态徽标一致",
    "memory": "记忆卡片密度与层次一致",
    "galaxy": "节点标签可读、深色宇宙对比度（galaxy 允许 dark cosmic 独占）",
    "profile": "身份卡+入口行一致性与图标语义",
    "settings": "分组标题层级与开关/箭头 affordance",
}


@dataclass(frozen=True)
class MatrixRow:
    """一条采集行 = surface×state×persona×platform×viewport。"""

    surface: str
    state_id: str
    persona: str
    entry: str
    platform: str
    viewport: str
    assertions: str

    def filename(self, build_sha8: str) -> str:
        """canonical 文件名；sha8 为占位符时输出同构模板（延迟到采集时定型）。"""
        try:
            return screenshot_name(
                self.surface,
                self.state_id,
                self.persona,
                self.platform,
                self.viewport,
                build_sha8,
            )
        except NamingError:
            return (
                f"{self.surface}__{self.state_id}__{self.persona}"
                f"__{self.platform}__{self.viewport}__<SHA8>.png"
            )


def iter_matrix_rows() -> list[MatrixRow]:
    """canonical states × U-09 三端 × 各端 viewport 的全矩阵行。"""
    rows: list[MatrixRow] = []
    for cs in CANONICAL_STATES:
        assertions = "; ".join(
            [_BASE_ASSERTIONS, _SURFACE_ASSERTIONS.get(cs.surface, "")]
        ).rstrip("; ").rstrip()
        for platform in U09_PLATFORMS:
            for viewport in U09_VIEWPORTS[platform]:
                rows.append(
                    MatrixRow(
                        surface=cs.surface,
                        state_id=cs.state_id,
                        persona=cs.persona,
                        entry=cs.entry,
                        platform=platform,
                        viewport=viewport,
                        assertions=assertions,
                    )
                )
    return rows


def render_matrix_markdown(build_sha8: str = "<BUILD_SHA8>") -> str:
    """输出可执行采集清单（markdown checkbox，行数=矩阵行数）。"""
    rows = iter_matrix_rows()
    lines: list[str] = [
        "# U-09 三端截图矩阵（可执行清单）",
        "",
        f"- 构建 SHA8：`{build_sha8}`（用 `git rev-parse --short=8 HEAD` 取）",
        "- 端与 viewport 口径：v3/04_ux/MULTIPLATFORM.md；"
        "命名：B-04 naming.py（surface__state__persona__platform__viewport__sha8.png）",
        "- 采集前置：真实后端（gateway/engine）与真实账号（demo_data/new_user），"
        "不用 mock 冒充；galaxy 允许 dark cosmic。",
        "",
        "| # | surface | state | persona | platform | viewport | 采集入口 |",
        "|---|---------|-------|---------|----------|----------|----------|",
    ]
    for idx, row in enumerate(rows, start=1):
        lines.append(
            f"| {idx} | {row.surface} | {row.state_id} | {row.persona} "
            f"| {row.platform} | {row.viewport} | {row.entry} |"
        )
    lines += ["", "## 采集清单（逐张勾选；断言点见 diff report）", ""]
    for row in rows:
        lines.append(
            f"- [ ] `{row.filename(build_sha8)}`"
        )
    lines += [
        "",
        "## 通用断言点（每张图都要核对）",
        "",
        _BASE_ASSERTIONS,
        "",
    ]
    return "\n".join(lines)


def diff_report_template() -> str:
    """A/B diff report 模板（真机批次后逐 state×platform 填写）。"""
    return """# U-09 三端 Diff Report（真机批次填写）

- 构建 SHA：`<BUILD_SHA>`（base `<BASE_SHA>` → final `<FINAL_SHA>`）
- 采集环境：gateway `<GATEWAY_URL>` / engine `<ENGINE_URL>`
- 执行人/日期：`<EXECUTOR>` / `<DATE>`
- 断言底线（MULTIPLATFORM.md）：核心层级/文案/状态语义必须一致；
  允许平台 native 差异（逐条 reason 见下）。

## 逐状态比对

对每张截图对（Android vs Web vs macOS）填写：

```
| SURFACE | STATE | PLATFORM | 结论(一致/A-B issue) | 证据文件 |
|---------|-------|----------|----------------------|----------|
| <SURFACE> | <STATE> | <PLATFORM> | <一致 or issue#> | <png 名> |
```

### A/B visual issue 记录（有则逐条）

```
issue-<N>: platform=<PLATFORM> surface=<SURFACE> state=<STATE>
现象：<一句话>
层级/文案/状态语义哪一类：<层级|文案|状态语义|布局 overflow|交互语义>
截图：<android png> vs <macos/web png>
```

## 允许差异（预登记，逐条 reason；新增差异必须补 reason 后方可放行）

| 差异点 | 涉及平台 | reason |
|--------|----------|--------|
| 导航转场（iOS=Cupertino/其余=FadeForwards） | 全端 | 平台导航手势约定，不砍平台能力 |
| 触觉/音频后端 | 桌面/web 降级 | 移动硬件能力，桌面/web 无硬件约定 |
| API 默认主机（android=10.0.2.2） | android | 模拟器宿主回环别名，dart-define 可一致 |
| token 存储后端（web=localStorage） | web | secure storage web 并发写丢失实证（W-1/W-2），竞赛口径可接受 |
| IME 动作按钮视觉 | android/iOS | 系统渲染；行为契约（send 语义）已由契约测试钉住 |

## 提交物

- [ ] screenshot 全集（命名合规，`visual_baseline.py verify` 通过）
- [ ] manifest.json（--build-sha/--platform/--viewport 逐端）
- [ ] 本 report 填写完成，A/B issue 有 ledger 归属
"""
