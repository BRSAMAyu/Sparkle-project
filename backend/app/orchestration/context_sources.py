"""C-02 · State / Memory / Knowledge / Events 四分 source adapter 层。

目标（v3/02_core_systems/USER_WORLD_MODEL.md「四类对象不可混」）：
Context Builder 侧给每一段注入内容标注来源类别，阻止 profile / RAG / history /
memory 混成一段无来源 prose；同名字段不再被后写静默覆盖。

与既有地基的关系：
- **C-01（decision_context.v1）**：``SOURCE_CATEGORY_BY_ITEM_TYPE`` 把冻结的
  ``DECISION_ITEM_TYPES`` 封闭投影到四类；不改 C-01 冻结面（ref URI 5 scheme、
  why_included 词表、dataclass 字段集原样）。
- **B-06（D-CTX 裁决）**：ContextPack 是唯一上下文契约。本模块是 ContextPack 的
  *来源分类面*（pack 侧 manifest/metadata + telemetry），以及 ContextBuilderMixin
  平行装配路径的*来源标注面*（orchestrator 侧 manifest + 覆盖检测）——stage 适配器
  由此降级为带来源标签的数据源，这是 D-CTX 冻结的迁移路径第一步。
- **M-03（memory 预筛，已合入 main @ 1ea854c9）**：真模块
  ``app/services/memory_retrieval_prefilter`` 在树内；本模块的委托入口是
  ``prefilter_memory_candidates_for_llm_context``（刻意与 M-03 的 async
  ``apply_memory_prefilter`` **不同名**，避免双义名接错版本），经 M-03 的
  ``build_retrieval_context`` 载入 ``user_memory_settings`` permissions（用户
  隐私设置不得绕过），委托异常向上抛（无静默透传——接口漂移必须可见）。
  M-03 拥有的三个候选拉取接线点（context_pack.build / context_manager /
  stage34）本卡不碰；pack 侧 manifest 消费 M-03 落的
  ``metadata["memory_prefilter"]`` 作为 provenance（真实集成路径）。
- **D-01（event_registry）**：Events 适配器只从封闭词表取事件名
  （``decision.recorded`` 为 decision_records 读投影的注册名）。

manifest 形状契约（R2-F1 返修）：pack 面与 orchestrator 面产出**同一 key 集**的
manifest（``MANIFEST_TOP_LEVEL_KEYS`` / ``MANIFEST_SECTION_KEYS`` 冻结，序列化唯一
权威是 ``assemble_manifest`` / ``normalize_section``）；面间不适用的值为 ``None``
（如 orchestrator 面无 ``item_category_counts``、pack 面无 ``late_stage_writers``），
key 恒在。tests/unit/test_context_source_contract.py 钉死两面的 key 集。

类别判定依据（storage-of-truth + USER_WORLD_MODEL 权威，逐 key 见 KEY_CATEGORY_MAP）：
- state    —— 业务真值投影：UserStateV1 信号、plan/goal/task/schedule/focus、
              working memory、profile/llm_profile（C-01 ``user_state://``/``profile://``
              /``plan://`` 同域）。Goal 属 Current State（USER_WORLD_MODEL §1），
              虽存储在 MemoryGoal 表——类别按语义对象，不按表名。
- memory   —— 未来可复用的用户相关信息：episodic（EXPERIENCE）、preference 记录
              （CONFIRMED_PREFERENCE）、跨会话记忆、行为模式洞察（OBSERVATION/
              HYPOTHESIS）、学习缺口推断（SeedExtractor 假设）。
- knowledge—— 用户上传/外部内容：galaxy 知识节点、种子库 few-shot 示例、文档切片
              （文档检索正文由 ContextBudgetManager 预算面计量，本层计量 payload 内
              knowledge 域条目）。
- events   —— 不可变/追加式历史及其派生摘要：decision_records、工具使用记录、
              校准回执（memory corrected 事件）、returning_context（任务完成事件
              的 outcome summary）、**会话历史**（message sent 事件；经
              ContextPruner 压缩，仅最近必要消息 + summary，不替代 state——state
              通道永不消费会话历史，见 StateSourceAdapter）。
- control  —— 显式非世界模型桶：kill-switch 模式、请求参数（use_document_context
  等）。不混入四类，避免污染封闭词表。

seed/demo 标记口径与 registration_source 对齐（guest_cleanup/guest_seed_service/
simulation_runner 现状）：registration_source ∈ {seed, system, guest} 为用户级标记；
memory 记录 source_type == "startup_seed" 为条目级标记；种子库 few-shot 内容本身
恒为 seed 内容。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable, Iterable, Mapping, Sequence

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.event_registry import EVENT_SCHEMA_VERSION, is_registered_event_name
from app.services.memory_retrieval_prefilter import (
    MEMORY_PREFILTER_VERSION,
    PURPOSE_LLM_CONTEXT,
    build_retrieval_context,
    prefilter_candidates,
)

# ---------------------------------------------------------------------------
# 封闭词表
# ---------------------------------------------------------------------------

SOURCE_SCHEMA_VERSION = "context_sources.v1"

#: 四类来源类别（USER_WORLD_MODEL「四类对象不可混」）。扩展需 bump schema version。
SOURCE_CATEGORIES: tuple[str, ...] = ("state", "memory", "knowledge", "events")

#: 显式非来源桶（控制面/请求参数），不计入四类。
CONTROL_BUCKET = "control"

#: C-01 冻结 item type → 四类 source category 的全映射（封闭、全覆盖）。
#: goal/plan/user_state_signal → state：USER_WORLD_MODEL §1 把 Goal/Milestone/Action/
#: Schedule 归 Current State（存储在 memory 表不改变语义类别）。
SOURCE_CATEGORY_BY_ITEM_TYPE: Mapping[str, str] = {
    "user_state_signal": "state",
    "plan": "state",
    "goal": "state",
    "preference": "memory",
    "episodic_memory": "memory",
    "document_chunk": "knowledge",
    # events 类条目不进 C-01 冻结 items（扩展需 C-01 契约 bump + 双 reviewer）；
    #: events 走本层 manifest（见 EventSourceAdapter）。
}

#: 用户级 seed/demo 判定口径（与 registration_source 写方一致）。
SEED_REGISTRATION_SOURCES: frozenset[str] = frozenset({"seed", "system", "guest"})

#: 条目级 seed 标记：guest_seed_service 落的记忆 source_type。
SEED_MEMORY_SOURCE_TYPE = "startup_seed"

#: ContextBuilderMixin 装配 payload 的 key → 类别映射（orchestrator 侧分类面）。
#: 逐 key 判据见模块 docstring；新增 payload key 必须在此登记，否则落 unclassified
#: 并告警（防再次无来源混装）。整表被 test_context_source_contract 的 golden 断言
#: 钉死（R2-F9）：改任何条目必须同步改测试。
#:
#: 命名陷阱澄清（R2-F9）：payload 的 ``"preferences"``（复数）是 profile_context
#: 产的画像偏好 dict → **state**（C-01 ``profile://`` 域）；pack 面 DecisionItem 的
#: type ``"preference"``（单数）是 memory 记录 → **memory**。两个词形似面异，
#: 消费方按（面, 词形）取义，不得跨面混用。
KEY_CATEGORY_MAP: Mapping[str, str] = {
    # state：业务真值投影
    "user_context": "state",
    "analytics_summary": "state",
    "preferences": "state",  # payload 面来自 profile_context（C-01 profile:// 域）；memory 记录版在 pack 面（见上方命名陷阱澄清）
    "preference_version": "state",
    "llm_profile": "state",
    "experiment_cohort": "state",
    "profile": "state",
    "profile_context": "state",
    "next_actions": "state",
    "active_plans": "state",
    "active_goals": "state",  # stage34 写入；语义类别 Current State
    "focus_stats": "state",
    "task_status_summary": "state",
    "calendar_context": "state",
    "working_memory_snapshot": "state",  # UserStateV1 字段投影
    "cognitive_context": "state",  # 聚合视图（stage34/39 会向其内层注入 memory/knowledge 子键）
    "self_model": "state",
    "scaffolding_fsm_snapshot": "state",
    "aurora_everyday_presence": "state",
    "plan_context": "state",
    "understanding_depth": "state",  # 系统侧理解度评分（运行时度量）
    # memory
    "episodic_memories": "memory",
    "past_session_memory": "memory",
    "last_session_mood": "memory",
    "cognitive_insights": "memory",  # 行为模式 = OBSERVATION/HYPOTHESIS（USER_WORLD_MODEL §2）
    "learning_gaps_summary": "memory",  # SeedExtractor 推断（HYPOTHESIS）
    "preferred_tools": "memory",  # 由使用历史习得的工具偏好
    # knowledge
    "seed_library": "knowledge",
    "galaxy_snapshot": "knowledge",
    "knowledge_context": "knowledge",
    "document_context": "knowledge",
    # events
    "recent_corrections": "events",  # 校准回执（memory corrected 事件）
    "recent_tool_usage": "events",
    "returning_context": "events",  # 任务完成/交互事件的 outcome summary
    # control：请求参数 / kill-switch 模式 / 规划循环挂载（非世界模型）
    "use_document_context": CONTROL_BUCKET,
    "document_filter": CONTROL_BUCKET,
    "selected_document_ids": CONTROL_BUCKET,
    "effective_file_ids": CONTROL_BUCKET,
    "conversation_settings": CONTROL_BUCKET,
    "aurora_stage34_modes": CONTROL_BUCKET,
    "aurora_stage39_modes": CONTROL_BUCKET,
    "aurora_planning_sidecar": CONTROL_BUCKET,  # orchestrator._attach_aurora_planning_sidecar 的后写挂载（R2-F5）
}

#: 已知会被 stage 适配器在 base 装配之后追加/改写的 payload key（静态事实，来自
#: _attach_stage34_memory_context / _attach_stage39_context 的写序）。manifest 以
#: late_stage_writers 暴露（provenance 标注，不是冲突断言）。整表被 golden 断言
#: 钉死（R2-F8）；stage 写序变化时必须同步改这里与测试。
LATE_STAGE_WRITERS: Mapping[str, tuple[str, ...]] = {
    "active_goals": ("stage34_memory",),
    "episodic_memories": ("stage34_memory",),
    "last_session_mood": ("stage34_memory",),
    "recent_corrections": ("stage34_memory",),
    "cognitive_context": ("stage34_memory", "stage39_scaffolding"),
    "galaxy_snapshot": ("stage39_scaffolding",),
    "scaffolding_fsm_snapshot": ("stage39_scaffolding",),
}

#: _merge_user_contexts 中 grpc_context 可覆盖 local 的 key（写序事实）。
GRPC_MERGE_KEYS: tuple[str, ...] = ("next_actions", "active_plans", "focus_stats", "recent_progress")

#: 恒为 seed 内容的 knowledge key（种子库 few-shot 示例）。
ALWAYS_SEED_KEYS: frozenset[str] = frozenset({"seed_library"})


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _default_estimate_tokens(text: str) -> int:
    """与 app.core.context_pack.estimate_tokens 同型降级（无 tiktoken 时 len//4）。

    生产调用方注入 context_pack.estimate_tokens 共享 tiktoken 编码器；本默认实现
    保证模块独立可测、无环依赖（context_pack 反向 import 本模块）。
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def _serialize(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def item_source_category(item_type: str) -> str:
    """C-01 冻结 item type → 四类类别（封闭投影，未知 type 抛 KeyError）。"""
    return SOURCE_CATEGORY_BY_ITEM_TYPE[item_type]


def user_is_seed_or_demo(registration_source: str | None) -> bool:
    """用户级 seed/demo 判定（与 registration_source 写方口径对齐）。"""
    return str(registration_source or "").strip().lower() in SEED_REGISTRATION_SOURCES


def memory_record_is_seed(record: Any) -> bool:
    """条目级 seed 判定：guest_seed_service 落的记忆 source_type=startup_seed。"""
    source_type = str(getattr(record, "source_type", "") or "").strip().lower()
    if source_type == SEED_MEMORY_SOURCE_TYPE:
        return True
    raw = record if isinstance(record, dict) else None
    if raw is not None:
        return str(raw.get("source_type") or "").strip().lower() == SEED_MEMORY_SOURCE_TYPE
    return False


def event_name_for_decision_record(record: Any) -> str:
    """decision_records 行 → D-01 注册事件名（读投影的注册名 decision.recorded）。

    词表外的名字对读投影不存在（行数据不产生新事件名）；若 registry 撤销该名，
    本函数抛错并在适配器层降级为 degraded 标记，绝不静默换名。
    """
    name = "decision.recorded"
    if not is_registered_event_name(name):
        raise LookupError(f"decision-record read-projection event name {name!r} not in D-01 registry")
    return name


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

#: manifest 分节序列化面的冻结 key 集（R2-F1：pack 面与 orchestrator 面同 key 集；
#: 缺 key/多 key 由 test_context_source_contract 契约测试钉死，任何变更需双 reviewer）。
MANIFEST_SECTION_KEYS: tuple[str, ...] = (
    "category",
    "enabled",
    "adapter",
    "keys",
    "item_count",
    "token_estimate",
    "seed_or_demo",
    "seed_or_demo_items",
    "decision_items",  # pack 面：该类 decision item 数；orchestrator 面 None
    "compaction",  # events 面：会话历史 compaction 边界；其余 None
    "note",
)

#: manifest 顶层序列化面的冻结 key 集（同上冻结）。
MANIFEST_TOP_LEVEL_KEYS: tuple[str, ...] = (
    "schema_version",
    "sections",
    "item_category_counts",  # pack 面：decision items 封闭投影计数；orchestrator 面 None
    "overrides",
    "unclassified",
    "user_is_seed_or_demo",  # orchestrator 面 bool；pack 面 None（不 fetch 用户行）
    "late_stage_writers",  # orchestrator 面；pack 面 {}
    "control_keys",
    "seed_or_demo_items_total",
    "event_schema_version",
)


def normalize_section(
    *,
    category: str,
    enabled: bool,
    adapter: str,
    keys: Sequence[str],
    item_count: int,
    token_estimate: int,
    seed_or_demo: int,
    seed_or_demo_items: Sequence[Mapping[str, Any]],
    decision_items: int | None = None,
    compaction: Mapping[str, Any] | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """分节序列化的**唯一权威**：恒定产出恰好 MANIFEST_SECTION_KEYS 的 key 集。"""
    return {
        "category": category,
        "enabled": enabled,
        "adapter": adapter,
        "keys": list(keys),
        "item_count": int(item_count),
        "token_estimate": int(token_estimate),
        "seed_or_demo": int(seed_or_demo),
        "seed_or_demo_items": [dict(item) for item in seed_or_demo_items],
        "decision_items": decision_items,
        "compaction": dict(compaction) if compaction is not None else None,
        "note": note,
    }


def assemble_manifest(
    *,
    sections: Mapping[str, Mapping[str, Any]],
    overrides: Sequence[SourceOverride | Mapping[str, Any]] = (),
    unclassified: Sequence[str] = (),
    user_is_seed_or_demo: bool | None = None,
    late_stage_writers: Mapping[str, Sequence[str]] | None = None,
    control_keys: Sequence[str] = (),
    item_category_counts: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """顶层序列化的**唯一权威**：恒定产出恰好 MANIFEST_TOP_LEVEL_KEYS 的 key 集。

    两个面（pack / orchestrator）都必须经此函数产出 manifest——形状一致性由构造
    保证，契约测试再钉死。``None``/``{}`` 表示该面不适用（见 MANIFEST_TOP_LEVEL_KEYS 注释）。
    """
    return {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "sections": {category: dict(section) for category, section in sections.items()},
        "item_category_counts": dict(item_category_counts) if item_category_counts is not None else None,
        "overrides": [
            override.to_dict() if isinstance(override, SourceOverride) else dict(override) for override in overrides
        ],
        "unclassified": list(unclassified),
        "user_is_seed_or_demo": user_is_seed_or_demo,
        "late_stage_writers": {key: list(writers) for key, writers in (late_stage_writers or {}).items()},
        "control_keys": list(control_keys),
        "seed_or_demo_items_total": sum(int(section.get("seed_or_demo", 0) or 0) for section in sections.values()),
        "event_schema_version": EVENT_SCHEMA_VERSION,
    }


@dataclass(frozen=True)
class SourcedItem:
    """一个被注入条目的来源描述（manifest 原子）。"""

    category: str
    key: str
    writer: str = ""
    item_count: int = 1
    token_estimate: int = 0
    is_seed_or_demo: bool = False
    ref: str | None = None
    event_name: str | None = None  # events 类：D-01 注册事件名
    schema_version: str = SOURCE_SCHEMA_VERSION


@dataclass(frozen=True)
class SourceOverride:
    """一次被显式登记的同名覆盖（替代"后写静默胜出"）。"""

    key: str
    previous_category: str
    previous_writer: str
    new_category: str
    new_writer: str
    resolution: str = "registered"  # 登记后如何处置（namespaced / last_write_wins_visible / grpc_overrode_local）
    #: 折叠面：同 key 全部参选记录 id（按输入序）——胜者可能是首记录（rank 重排），
    #: 此时 previous_writer == new_writer，无 contenders 则覆盖事实不可见。
    contenders: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "key": self.key,
            "previous_category": self.previous_category,
            "previous_writer": self.previous_writer,
            "new_category": self.new_category,
            "new_writer": self.new_writer,
            "resolution": self.resolution,
        }
        if self.contenders:
            payload["contenders"] = list(self.contenders)
        return payload


@dataclass(frozen=True)
class SourceSection:
    """单类别分节：开关、条目、计量、seed 标记、（events 通道的）compaction 边界。"""

    category: str
    enabled: bool
    adapter: str
    items: tuple[SourcedItem, ...] = ()
    compaction: Mapping[str, Any] | None = None
    note: str | None = None
    decision_items: int | None = None

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(item.key for item in self.items)

    @property
    def item_count(self) -> int:
        return sum(item.item_count for item in self.items)

    @property
    def token_estimate(self) -> int:
        return sum(item.token_estimate for item in self.items)

    @property
    def seed_or_demo_count(self) -> int:
        return sum(1 for item in self.items if item.is_seed_or_demo)

    @property
    def seed_or_demo_items(self) -> tuple[SourcedItem, ...]:
        return tuple(item for item in self.items if item.is_seed_or_demo)

    def to_dict(self) -> dict[str, Any]:
        return normalize_section(
            category=self.category,
            enabled=self.enabled,
            adapter=self.adapter,
            keys=self.keys,
            item_count=self.item_count,
            token_estimate=self.token_estimate,
            seed_or_demo=self.seed_or_demo_count,
            seed_or_demo_items=[{"key": item.key} for item in self.seed_or_demo_items],
            decision_items=self.decision_items,
            compaction=self.compaction,
            note=self.note,
        )


@dataclass(frozen=True)
class SourceManifest:
    sections: Mapping[str, SourceSection]
    overrides: tuple[SourceOverride, ...] = ()
    unclassified: tuple[str, ...] = ()
    user_is_seed_or_demo: bool | None = None
    late_stage_writers: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    control_keys: tuple[str, ...] = ()
    item_category_counts: Mapping[str, int] | None = None

    def to_dict(self) -> dict[str, Any]:
        return assemble_manifest(
            sections={category: section.to_dict() for category, section in self.sections.items()},
            overrides=self.overrides,
            unclassified=self.unclassified,
            user_is_seed_or_demo=self.user_is_seed_or_demo,
            late_stage_writers=self.late_stage_writers,
            control_keys=self.control_keys,
            item_category_counts=self.item_category_counts,
        )


# ---------------------------------------------------------------------------
# SourceRegistry：无静默覆盖保证
# ---------------------------------------------------------------------------


class SourceRegistry:
    """按写入顺序登记 (category, key)；同名 key 的后续写入构成显式覆盖事件。

    - 同 key 跨类别/跨 writer 后写：登记 SourceOverride + loguru warning；
      namespaced key（``category/key``）保证四类同名条目并存可取。
    - manifest 是只读投影；不改变宿主 payload 的最终值（兼容既有消费方），
      改变的是"覆盖可见"。
    """

    def __init__(self, estimate_tokens_fn: Callable[[str], int] | None = None) -> None:
        self._estimate = estimate_tokens_fn or _default_estimate_tokens
        self._items: list[SourcedItem] = []
        self._overrides: list[SourceOverride] = []
        self._seen: dict[str, SourcedItem] = {}

    def namespaced_key(self, category: str, key: str) -> str:
        return f"{category}/{key}"

    def register(
        self,
        category: str,
        key: str,
        *,
        writer: str = "",
        item_count: int = 1,
        payload: Any = None,
        is_seed_or_demo: bool = False,
        ref: str | None = None,
        event_name: str | None = None,
    ) -> SourcedItem:
        token_estimate = self._estimate(_serialize(payload)) if payload is not None else 0
        item = SourcedItem(
            category=category,
            key=key,
            writer=writer,
            item_count=item_count,
            token_estimate=token_estimate,
            is_seed_or_demo=is_seed_or_demo,
            ref=ref,
            event_name=event_name,
        )
        previous = self._seen.get(key)
        if previous is not None:
            override = SourceOverride(
                key=key,
                previous_category=previous.category,
                previous_writer=previous.writer,
                new_category=category,
                new_writer=writer,
                resolution="namespaced",
            )
            self._overrides.append(override)
            logger.warning(
                "context source override: key={key} {prev_category}/{prev_writer} -> {new_category}/{new_writer}; "
                "namespaced as {ns} (both retained)",
                key=key,
                prev_category=previous.category,
                prev_writer=previous.writer,
                new_category=category,
                new_writer=writer,
                ns=self.namespaced_key(category, key),
            )
        self._seen[key] = item
        self._items.append(item)
        return item

    def record_override(self, override: SourceOverride) -> None:
        self._overrides.append(override)

    def manifest(
        self,
        *,
        enabled_map: Mapping[str, bool] | None = None,
        adapters: Mapping[str, str] | None = None,
        user_is_seed: bool | None = None,
    ) -> SourceManifest:
        sections: dict[str, SourceSection] = {}
        for category in SOURCE_CATEGORIES:
            items = tuple(item for item in self._items if item.category == category)
            sections[category] = SourceSection(
                category=category,
                enabled=(enabled_map or {}).get(category, True),
                adapter=(adapters or {}).get(category, "SourceRegistry"),
                items=items,
            )
        return SourceManifest(
            sections=sections,
            overrides=tuple(self._overrides),
            user_is_seed_or_demo=user_is_seed,
        )


# ---------------------------------------------------------------------------
# 覆盖检测辅助（既有静默面的显式化）
# ---------------------------------------------------------------------------


def detect_merge_overrides(
    local_context: Mapping[str, Any],
    merged: Mapping[str, Any],
    keys: Sequence[str],
) -> list[SourceOverride]:
    """grpc 合并面：merged[key] != local[key] 即 grpc 覆盖了本地值（原为静默）。"""
    overrides: list[SourceOverride] = []
    for key in keys:
        if key not in local_context or key not in merged:
            continue
        if local_context[key] != merged[key]:
            overrides.append(
                SourceOverride(
                    key=key,
                    previous_category=KEY_CATEGORY_MAP.get(key, "unclassified"),
                    previous_writer="local_context",
                    new_category=KEY_CATEGORY_MAP.get(key, "unclassified"),
                    new_writer="grpc_context",
                    resolution="grpc_overrode_local",
                )
            )
    for override in overrides:
        logger.warning(
            "context source override: grpc_context replaced local_context key={key} (category={category})",
            key=override.key,
            category=override.previous_category,
        )
    return overrides


def detect_preference_key_overrides(
    records: Sequence[Any],
    final_values: Mapping[str, Any] | None = None,
) -> list[SourceOverride]:
    """pack 非 resolver 分支 {pref_key: pref_value} 折叠面：同 key 多记录显式登记。

    折叠语义保持兼容（同 key 单值输出不变）；改变的是覆盖可见。winner 判定：
    传 ``final_values``（pack 最终 preferences 映射，经 rank/裁剪后）时按**实际
    胜出值**回溯 winner（rank 重排会改变字典推导的胜者——登记必须与事实一致，
    不得假设输入序末者胜）；无法回溯时标 "undetermined"。未传时按输入序末者
    （与非 ranked dict comprehension 的语义一致）。
    """
    by_key: dict[str, list[Any]] = {}
    for record in records:
        key = str(getattr(record, "pref_key", "") or "")
        if key:
            by_key.setdefault(key, []).append(record)
    overrides: list[SourceOverride] = []
    for key, group in by_key.items():
        if len(group) < 2:
            continue
        first, last = group[0], group[-1]
        winner = str(getattr(last, "id", "unknown"))
        if final_values is not None and key in final_values:
            final_value = final_values[key]
            winner_records = [record for record in group if getattr(record, "pref_value", None) == final_value]
            if winner_records:
                winner = str(getattr(winner_records[0], "id", "unknown"))
            else:
                winner = "undetermined"
        overrides.append(
            SourceOverride(
                key=key,
                previous_category="memory",
                previous_writer=str(getattr(first, "id", "unknown")),
                new_category="memory",
                new_writer=winner,
                resolution="last_write_wins_visible",
                contenders=tuple(str(getattr(record, "id", "unknown")) for record in group),
            )
        )
        logger.warning(
            "context source override: preference key={key} collapsed {count} records; "
            "winner={winner} (last-write-wins, now visible)",
            key=key,
            count=len(group),
            winner=winner,
        )
    return overrides


# ---------------------------------------------------------------------------
# Memory 预筛委托（R2-F4：真模块直调，权限继承，不吞错）
# ---------------------------------------------------------------------------


async def prefilter_memory_candidates_for_llm_context(
    db: AsyncSession | None,
    candidates: Iterable[Any],
    *,
    user_id: str,
    plan_id: str | None = None,
    goal_ids: Iterable[str] = (),
    task_ids: Iterable[str] = (),
    domain_keys: Iterable[str] = (),
    task_type: str | None = None,
    session_id: str | None = None,
) -> tuple[list[Any], dict[str, Any]]:
    """C-02 对 M-03 真模块的**唯一**预筛委托入口（R2-F4 返修）。

    与 M-03 自己的 async ``apply_memory_prefilter`` 刻意不同名（防双义名接错版本）。

    语义（对齐 R2-F4 三项要求）：
    - **permissions 不得绕过**：context 经 M-03 ``build_retrieval_context`` 组装，
      ``user_memory_settings``（blocked_pref_keys / allow_episodic 等）随 db 会话
      best-effort 载入——与 M-03 在 context_pack.build 的接线同一权限语义；
    - **不吞错**：委托异常（含接口漂移）向上抛，无 except-Exception 静默透传——
      漂移必须以失败可见，而不是无声变回"预筛从未生效"。settings 读失败由 M-03
      内部按 best-effort 默认处理（与其写侧一致），这不属于委托错误；
    - **差异信号保留**：有砍除时 WARNING 汇总，metric_payload（M-03
      ``PrefilterResult.to_metric_payload``，含 version/dimension/reason 计数）
      原样返回供 manifest/telemetry 消费。

    调用方：M-03 拥有的三个候选拉取接线点（context_pack.build / context_manager /
    stage34）不经本函数；本入口服务 C-02 后续 D-CTX 收敛卡（orchestrator 直读
    memory 候选时）与显式测试（end-to-end 见 test_context_source_contract）。
    """
    ctx = await build_retrieval_context(
        db,
        user_id=user_id,
        purpose=PURPOSE_LLM_CONTEXT,
        plan_id=plan_id,
        goal_ids=goal_ids,
        task_ids=task_ids,
        domain_keys=domain_keys,
        task_type=task_type,
        session_id=session_id,
    )
    result = prefilter_candidates(list(candidates), ctx)
    if result.rejections:
        logger.warning(
            "C-02 memory prefilter (M-03 {version}) rejected {rejected}/{total} candidates: {reasons}",
            version=MEMORY_PREFILTER_VERSION,
            rejected=len(result.rejections),
            total=result.input_count,
            reasons=dict(result.reason_counts),
        )
    return list(result.allowed), result.to_metric_payload()


# ---------------------------------------------------------------------------
# 四类 adapter：独立 enable/disable + 计量
# ---------------------------------------------------------------------------


class _BaseSourceAdapter:
    category: str = "state"
    adapter_name: str = "base"
    settings_flag: str = "ENABLE_CONTEXT_SOURCE_STATE"

    def __init__(
        self,
        enabled: bool | None = None,
        estimate_tokens_fn: Callable[[str], int] | None = None,
    ) -> None:
        self._explicit_enabled = enabled
        self._estimate = estimate_tokens_fn or _default_estimate_tokens

    @property
    def enabled(self) -> bool:
        if self._explicit_enabled is not None:
            return self._explicit_enabled
        return bool(getattr(settings, self.settings_flag, True))

    def _tokens(self, payload: Any) -> int:
        return self._estimate(_serialize(payload))


class StateSourceAdapter(_BaseSourceAdapter):
    """State（UserStateV1 投影 / plan / goal / task 真值面）。

    铁律：会话历史不属于 state（历史是 events 通道，经 compaction 边界注入；
    state 只来自权威状态投影——USER_WORLD_MODEL「history 不替代 state」）。
    """

    category = "state"
    adapter_name = "state_adapter"
    settings_flag = "ENABLE_CONTEXT_SOURCE_STATE"

    def classify_state_payload(self, mapping: Mapping[str, Any]) -> SourceSection:
        items: list[SourcedItem] = []
        if self.enabled:
            for key, value in mapping.items():
                if KEY_CATEGORY_MAP.get(key) != "state":
                    continue  # 非本类别（含 conversation_history 等永不含入项）静默跳过
                items.append(
                    SourcedItem(
                        category=self.category,
                        key=key,
                        writer="payload",
                        item_count=len(value) if isinstance(value, (list, tuple, dict)) else 1,
                        token_estimate=self._tokens(value),
                    )
                )
        return SourceSection(
            category=self.category, enabled=self.enabled, adapter=self.adapter_name, items=tuple(items)
        )


class MemorySourceAdapter(_BaseSourceAdapter):
    """Memory（episodic + preferences [+goals 存储行]）：分类 + 计量 + seed 标记。

    预筛：M-03 已在三个候选拉取接线点（context_pack.build / context_manager /
    stage34）过滤；本适配器只分类/计量已注入条目，不重复过滤。C-02 自己的候选
    读路径（未来 D-CTX 卡）经 ``prefilter_memory_candidates_for_llm_context`` 委托。
    """

    category = "memory"
    adapter_name = "memory_adapter"
    settings_flag = "ENABLE_CONTEXT_SOURCE_MEMORY"

    def classify_episodic(self, rows: Sequence[Any]) -> SourceSection:
        items: list[SourcedItem] = []
        if self.enabled:
            for row in rows:
                if isinstance(row, Mapping):
                    record_id = str(row.get("id", "") or "")
                    summary = str(row.get("summary", "") or "")
                else:
                    record_id = str(getattr(row, "id", "") or "")
                    summary = str(getattr(row, "summary", "") or "")
                items.append(
                    SourcedItem(
                        category=self.category,
                        key=f"episodic:{record_id}" if record_id else "episodic:unknown",
                        writer="memory_service.list_recent_episodic",
                        item_count=1,
                        token_estimate=self._tokens(summary),
                        is_seed_or_demo=memory_record_is_seed(row),
                        ref=f"memory://episodic/{record_id}" if record_id else None,
                    )
                )
        return SourceSection(
            category=self.category, enabled=self.enabled, adapter=self.adapter_name, items=tuple(items)
        )


def _payload_has_seed_memory(value: Any) -> bool:
    """序列化 memory 载荷里是否有 startup_seed 条目（stage34 序列化含 source_type）。"""
    if isinstance(value, (list, tuple)):
        return any(_payload_has_seed_memory(entry) for entry in value)
    if isinstance(value, Mapping):
        return memory_record_is_seed(dict(value)) or any(_payload_has_seed_memory(entry) for entry in value.values())
    return False


class KnowledgeSourceAdapter(_BaseSourceAdapter):
    """Knowledge（RAG/document/galaxy/种子库）：payload 分类 + 计量 + seed 标记。"""

    category = "knowledge"
    adapter_name = "knowledge_adapter"
    settings_flag = "ENABLE_CONTEXT_SOURCE_KNOWLEDGE"

    def classify_knowledge_payload(self, mapping: Mapping[str, Any]) -> list[SourcedItem]:
        items: list[SourcedItem] = []
        if not self.enabled:
            return items
        for key, value in mapping.items():
            if KEY_CATEGORY_MAP.get(key) != "knowledge":
                continue
            items.append(
                SourcedItem(
                    category=self.category,
                    key=key,
                    writer="payload",
                    item_count=len(value) if isinstance(value, (list, tuple, dict)) else 1,
                    token_estimate=self._tokens(value),
                    is_seed_or_demo=key in ALWAYS_SEED_KEYS,
                )
            )
        return items


class EventSourceAdapter(_BaseSourceAdapter):
    """Events（decision_records 等追加式历史）：走 D-01 词表。

    decision_records 行 → 注册事件名 decision.recorded（registry status=reserved，
    producers 即 "v3: decision_records read projection"——本适配器）。
    """

    category = "events"
    adapter_name = "event_adapter"
    settings_flag = "ENABLE_CONTEXT_SOURCE_EVENTS"

    def classify_records(self, records: Sequence[Any]) -> SourceSection:
        items: list[SourcedItem] = []
        degraded = False
        if self.enabled:
            for record in records:
                record_id = str(getattr(record, "id", "") or "")
                try:
                    event_name = event_name_for_decision_record(record)
                except LookupError:
                    event_name = None
                    degraded = True
                summary = {
                    "module": str(getattr(record, "module", "") or ""),
                    "action": str(getattr(record, "action", "") or ""),
                    "outcome": str(getattr(record, "outcome", "") or "")[:80],
                }
                items.append(
                    SourcedItem(
                        category=self.category,
                        key=f"decision_record:{record_id}" if record_id else "decision_record:unknown",
                        writer="decision_record_service.get_recent_records",
                        item_count=1,
                        token_estimate=self._tokens(summary),
                        event_name=event_name,
                    )
                )
        note = None
        if degraded:
            note = "some records could not map to a registered D-01 event name"
        return SourceSection(
            category=self.category,
            enabled=self.enabled,
            adapter=self.adapter_name,
            items=tuple(items),
            note=note,
        )

    def classify_events_payload(self, mapping: Mapping[str, Any]) -> list[SourcedItem]:
        items: list[SourcedItem] = []
        if not self.enabled:
            return items
        for key, value in mapping.items():
            if KEY_CATEGORY_MAP.get(key) != "events":
                continue
            items.append(
                SourcedItem(
                    category=self.category,
                    key=key,
                    writer="payload",
                    item_count=len(value) if isinstance(value, (list, tuple, dict)) else 1,
                    token_estimate=self._tokens(value),
                )
            )
        return items


# ---------------------------------------------------------------------------
# payload manifest（orchestrator 侧纯函数分类面）
# ---------------------------------------------------------------------------


def build_payload_source_manifest(
    payload: Mapping[str, Any],
    *,
    registration_source: str | None = None,
    decision_records: Sequence[Any] = (),
    conversation_stats: Mapping[str, Any] | None = None,
    estimate_tokens_fn: Callable[[str], int] | None = None,
) -> dict[str, Any]:
    """装配后的 ContextBuilderMixin payload → 四类 manifest dict。

    纯函数（无 I/O）：provider 读（registration_source / decision_records /
    conversation_stats）由宿主 mixin 完成。输出进 payload["context_sources"]，
    供 trace 消费与后续 D-CTX 收敛（orchestrator 消费 ContextPack 时直接复用）。
    """
    estimate = estimate_tokens_fn or _default_estimate_tokens
    registry = SourceRegistry(estimate_tokens_fn=estimate)
    unclassified: list[str] = []
    control_keys: list[str] = []

    for key, value in payload.items():
        if key == "context_sources":
            continue
        category = KEY_CATEGORY_MAP.get(key)
        if category is None:
            unclassified.append(key)
            continue
        if category == CONTROL_BUCKET:
            control_keys.append(key)
            continue
        is_seed = (category == "knowledge" and key in ALWAYS_SEED_KEYS) or (
            category == "memory" and _payload_has_seed_memory(value)
        )
        registry.register(
            category,
            key,
            writer="payload",
            item_count=len(value) if isinstance(value, (list, tuple, dict)) else 1,
            payload=value,
            is_seed_or_demo=is_seed,
        )

    # Events provider：decision_records（D-01 词表）。
    event_adapter = EventSourceAdapter(estimate_tokens_fn=estimate)
    event_section_extra = event_adapter.classify_records(decision_records)

    # history 语义：会话历史归 events 通道，携带 compaction 边界（最近必要消息 +
    # summary），不进 state（state 通道无 conversation_history 注册路径）。
    compaction: dict[str, Any] | None = None
    if conversation_stats:
        messages = int(conversation_stats.get("messages", conversation_stats.get("pruned_count", 0)) or 0)
        registry.register(
            "events",
            "conversation_history",
            writer="context_pruner",
            item_count=messages,
            payload={"messages": messages},
        )
        compaction = {
            "original_count": int(conversation_stats.get("original_count", 0) or 0),
            "pruned_count": int(conversation_stats.get("pruned_count", messages) or messages),
            "summary_used": bool(conversation_stats.get("summary_used", False)),
            "recent_window": int(conversation_stats.get("recent_window", 0) or 0),
        }

    enabled_map = {
        "state": StateSourceAdapter(estimate_tokens_fn=estimate).enabled,
        "memory": MemorySourceAdapter(estimate_tokens_fn=estimate).enabled,
        "knowledge": KnowledgeSourceAdapter(estimate_tokens_fn=estimate).enabled,
        "events": event_adapter.enabled,
    }
    adapters = {
        "state": StateSourceAdapter.adapter_name,
        "memory": MemorySourceAdapter.adapter_name,
        "knowledge": KnowledgeSourceAdapter.adapter_name,
        "events": EventSourceAdapter.adapter_name,
    }

    manifest = registry.manifest(
        enabled_map=enabled_map, adapters=adapters, user_is_seed=user_is_seed_or_demo(registration_source)
    )

    # 类别禁用时不装条目（开关语义：禁用 = 不注入该类 manifest 条目）。
    sections: dict[str, SourceSection] = {}
    for category, section in manifest.sections.items():
        if not enabled_map.get(category, True):
            sections[category] = SourceSection(
                category=category,
                enabled=False,
                adapter=section.adapter,
                items=(),
            )
        else:
            extra_items: tuple[SourcedItem, ...] = ()
            if category == "events" and event_section_extra.items:
                extra_items = event_section_extra.items
            sections[category] = SourceSection(
                category=category,
                enabled=True,
                adapter=section.adapter,
                items=tuple(section.items) + extra_items,
                compaction=compaction if category == "events" else None,
                note=event_section_extra.note if category == "events" else None,
            )

    late_writers = {key: writers for key, writers in LATE_STAGE_WRITERS.items() if key in payload}
    if unclassified:
        logger.warning(
            "context source manifest: {count} unclassified payload keys (register them in KEY_CATEGORY_MAP): {keys}",
            count=len(unclassified),
            keys=unclassified,
        )

    # R2-F1：与 pack 面同 key 集（item_category_counts 在 orchestrator 面不适用 → None）。
    return assemble_manifest(
        sections={category: section.to_dict() for category, section in sections.items()},
        overrides=manifest.overrides,
        unclassified=unclassified,
        user_is_seed_or_demo=user_is_seed_or_demo(registration_source),
        late_stage_writers=late_writers,
        control_keys=control_keys,
        item_category_counts=None,
    )


# ---------------------------------------------------------------------------
# manifest 后置附加（宿主在 manifest 构建后补齐跨面信息时使用；copy-on-write）
# ---------------------------------------------------------------------------


def attach_conversation_history(manifest: dict[str, Any], stats: Mapping[str, Any]) -> dict[str, Any]:
    """把会话历史计量（含 compaction 边界）附加进 manifest 的 events 通道。

    历史是 events 通道条目（message sent 事件），且仅最近必要消息 + summary——
    不进 state 通道、不替代 state（铁律由 build_payload_source_manifest 的注册
    路径保证：state 无 conversation_history 写入点）。
    """
    updated = dict(manifest)
    sections = dict(updated.get("sections") or {})
    events = dict(sections.get("events") or {})
    keys = list(events.get("keys") or [])
    if "conversation_history" not in keys:
        keys.append("conversation_history")
    messages = int(stats.get("messages", stats.get("pruned_count", 0)) or 0)
    events["keys"] = keys
    events["item_count"] = int(events.get("item_count", 0) or 0) + messages
    events["compaction"] = {
        "original_count": int(stats.get("original_count", 0) or 0),
        "pruned_count": int(stats.get("pruned_count", messages) or messages),
        "summary_used": bool(stats.get("summary_used", False)),
        "recent_window": int(stats.get("recent_window", 0) or 0),
    }
    sections["events"] = events
    updated["sections"] = sections
    return updated


def attach_overrides(manifest: dict[str, Any], overrides: Sequence[SourceOverride]) -> dict[str, Any]:
    """把宿主检测到的覆盖事件（grpc 合并面 / preference 折叠面）并入 manifest。"""
    if not overrides:
        return manifest
    updated = dict(manifest)
    updated["overrides"] = list(updated.get("overrides") or []) + [
        override.to_dict() if isinstance(override, SourceOverride) else dict(override) for override in overrides
    ]
    return updated


def register_post_manifest_writes(payload: dict[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    """R2-F5：把 manifest 附加**之后**写入 payload 的 key 登记进 manifest。

    背景：orchestrator 在 `_build_user_context`（manifest 附加点）之后仍写
    use_document_context/document_filter/selected_document_ids/conversation_settings
    （process_stream）与 aurora_planning_sidecar（_attach_aurora_planning_sidecar）——
    这些 key 若不补登记，生产环境 control_keys 恒空、unclassified 告警不可见
    （登记防线的写序盲区）。

    规则：mapped→control 的 key 进 control_keys；其余进 unclassified 并告警
    （若未来后写的是四类 key，落入 unclassified 即可见，不会被静默吞掉）。
    copy-on-write：不污染共享的嵌套 dict（FT-LAT-3 缓存 deepcopy 语义）。
    manifest 缺失（降级路径）时静默跳过——附加点自身已记 warning。
    """
    manifest = payload.get("context_sources")
    if not isinstance(manifest, dict):
        return payload

    control_keys = list(manifest.get("control_keys") or [])
    unclassified = list(manifest.get("unclassified") or [])
    known_control = set(control_keys)
    known_unclassified = set(unclassified)

    changed = False
    newly_unclassified: list[str] = []
    for key in keys:
        if key not in payload:
            continue
        category = KEY_CATEGORY_MAP.get(key)
        if category == CONTROL_BUCKET:
            if key not in known_control:
                control_keys.append(key)
                known_control.add(key)
                changed = True
        else:
            if key not in known_unclassified and key not in known_control:
                unclassified.append(key)
                known_unclassified.add(key)
                newly_unclassified.append(key)
                changed = True

    if not changed:
        return payload
    if newly_unclassified:
        logger.warning(
            "context source manifest: post-manifest writes landed unclassified "
            "(register them in KEY_CATEGORY_MAP): {keys}",
            keys=newly_unclassified,
        )
    payload["context_sources"] = {**manifest, "control_keys": control_keys, "unclassified": unclassified}
    return payload
