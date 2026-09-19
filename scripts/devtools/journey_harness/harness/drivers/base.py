"""driver 抽象基类。

所有 backend driver 实现同一组 step handler 约定：
  - `start(args)`：启动/连接目标（浏览器、模拟器、HTTP/WS 栈）
  - `execute(action, args) -> (ok, detail, artifacts)`：执行一步
  - `finish()`：收尾（关浏览器/杀模拟器——HEAVY 资源卡：收工必须清理）

红线（v3/05_metrics_eval/USER_SIMULATION.md）：simulator 通过真实 UI 操作，
不得因知道内部 route/API 就绕过体验层；找不到入口 = 产品缺陷，如实记 FAIL。
api backend 是唯一的非 UI 通道，仅用于 UI 通道尚未接通的平台/环境，输出里
必须标注 `non-ui lane`，不得冒充 UI 实测。
"""

from __future__ import annotations

from typing import Any


class StepFailure(Exception):
    """步骤失败（断言不满足或交互异常）。"""


class BaseDriver:
    name = "base"

    def __init__(self, evidence, config: dict[str, Any]) -> None:
        self.evidence = evidence
        self.config = dict(config)
        # 运行期上下文（journey 步骤间共享，如 note_account 记录的注册账号，
        # 供 runner 渲染 journey 级 DB 断言里的 {{accounts.default.username}}）
        self.state: dict[str, Any] = {}

    # 生命周期
    def start(self) -> None:
        raise NotImplementedError

    def finish(self) -> None:
        pass

    # 步骤执行：driver 子类实现 do_<action>；未知 action => 失败
    def execute(self, action: str, args: dict[str, Any]) -> tuple[bool, str, list[str]]:
        handler = getattr(self, f"do_{action}", None)
        if handler is None or not callable(handler):
            raise StepFailure(
                f"driver={self.name} 不支持 action={action!r}（journey 定义与 driver 能力不匹配）"
            )
        return handler(**args)

    # 通用断言辅助
    @staticmethod
    def check_assert(assert_spec: dict[str, Any] | None, detail: str) -> str:
        """步骤级结构化断言的钩子；默认由各 driver 在 do_* 内调用。"""
        return detail
