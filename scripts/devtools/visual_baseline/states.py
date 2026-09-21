"""B-04 canonical states 注册表：9 surfaces × 主要状态。

单一事实源：
- harness `coverage`/`plan` 子命令按此校验覆盖；
- REPORT.md 的 state 定义表由本表导出；
- 后续 UI 卡按本表复现状态后与 baseline 做 diff。

字段约定：
- surface: 9 canonical surfaces 之一（见 naming.SURFACES）
- state_id: 该 surface 的 canonical 状态标识（命名段，小写+单下划线）
- persona: demo_data（演示账号，只读）| new_user（新注册号）| guest
- definition: 状态的人类可读定义（采什么、应看到什么）
- entry: 复现入口（后续卡照做即可到达同一状态）
"""

from __future__ import annotations

from dataclasses import dataclass

from .naming import SURFACES


@dataclass(frozen=True)
class CanonicalState:
    surface: str
    state_id: str
    persona: str
    definition: str
    entry: str


CANONICAL_STATES: tuple[CanonicalState, ...] = (
    CanonicalState(
        surface="onboarding",
        state_id="persona_start",
        persona="new_user",
        definition=(
            "新注册账号首登进入 persona onboarding 第一步（身份/学习场景选择），"
            "无业务数据；重点看首引导的层次与文案可读性"
        ),
        entry="注册新账号 → 登录后自动跳 /onboarding/persona",
    ),
    CanonicalState(
        surface="home",
        state_id="main",
        persona="demo_data",
        definition=(
            "演示账号 Dashboard 今日视图：今日任务/目标星标入口/14 天趋势入口可见，"
            "数据在库非空态"
        ),
        entry="演示账号登录 → 底部 Tab 1（home）",
    ),
    CanonicalState(
        surface="chat",
        state_id="history_citations",
        persona="demo_data",
        definition=(
            "打开演示账号既有历史会话（R1-R5 对话史），含 AI 回复气泡与"
            "引用/证据块（R9 类引用卡片）；观察消息层次与引用块对比度"
        ),
        entry="chat Tab → 会话历史列表 → 打开演示会话，滚至含引用块的回复",
    ),
    CanonicalState(
        surface="goal",
        state_id="library_main",
        persona="demo_data",
        definition=(
            "目标库/目标详情主视图：演示目标（含关联任务星）在库，非空态；"
            "观察目标卡信息密度与进度表达"
        ),
        entry="home → 目标入口（/goals）",
    ),
    CanonicalState(
        surface="task",
        state_id="library_main",
        persona="demo_data",
        definition=(
            "任务库主视图：演示任务在库，今日/非今日分组可见；观察任务行"
            "可点击性与状态徽标"
        ),
        entry="home → 任务入口（/tasks）",
    ),
    CanonicalState(
        surface="memory",
        state_id="panel_main",
        persona="demo_data",
        definition=(
            "记忆面板主视图：演示账号既有记忆条目（材料 AB 节点树相关）可见，"
            "非空态；观察记忆卡片的密度与层次"
        ),
        entry="home/profile → 记忆入口（/memory）",
    ),
    CanonicalState(
        surface="galaxy",
        state_id="tree_expanded",
        persona="demo_data",
        definition=(
            "星系视图：演示节点树展开态（材料 AB 节点），节点标签可读；"
            "galaxy 为独立视觉锤（允许 dark cosmic），审查节点对比度与装饰预算"
        ),
        entry="galaxy Tab → 等待节点树渲染后展开演示节点",
    ),
    CanonicalState(
        surface="profile",
        state_id="main",
        persona="demo_data",
        definition=(
            "profile 页主视图：用户身份卡+功能入口列表（含设置入口）；"
            "观察入口行一致性与图标语义"
        ),
        entry="底部 Tab 5（profile）",
    ),
    CanonicalState(
        surface="settings",
        state_id="main",
        persona="demo_data",
        definition=(
            "设置页主视图（/profile/settings）：设置分组列表；观察分组标题"
            "层级与开关/箭头 affodance"
        ),
        entry="profile → 设置（/profile/settings）",
    ),
)


def canonical_state_for(surface: str, state_id: str) -> CanonicalState | None:
    for cs in CANONICAL_STATES:
        if cs.surface == surface and cs.state_id == state_id:
            return cs
    return None


def iter_state_rows() -> list[tuple[str, str, str, str, str]]:
    """供 REPORT/plan 输出的 (surface, state, persona, definition, entry) 行。"""
    return [
        (cs.surface, cs.state_id, cs.persona, cs.definition, cs.entry)
        for cs in CANONICAL_STATES
    ]


def assert_registry_consistent() -> None:
    """注册表自检：surface 必须属于 9 canonical surfaces。"""
    for cs in CANONICAL_STATES:
        if cs.surface not in SURFACES:
            raise ValueError(f"registry surface {cs.surface!r} not in canonical surfaces")
