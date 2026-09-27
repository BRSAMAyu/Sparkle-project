"""O-06 · Kill Switch / Release / Rollback 统一操作面 —— 能力注册表与受控翻转面.

单一权威不变（Forbidden #1：不得重建已存在的权威真源）：
- 模式判定权威仍是 ``app/core/kill_switch.py`` 的 read_mode/write_mode
  （Redis 现值优先、settings tri-state 判据、legacy bool 兜底、Prometheus gauge）。
- 各能力绑定的权威仍是各 service/bridge 模块里既有的 KillSwitchBinding 实例。

本模块只是这 60+ 既有绑定的**统一索引 + 受控翻转入口**：
- ``CAPABILITY_SPECS`` 惰性解析（importlib + getattr/item 走径）引用既有绑定对象，
  零复制绑定定义、零提前 import 服务模块（防核心层反向拖入 services 导入链）。
- ``set_capability_mode`` / ``rollback_capability`` 走同一个核心 write_mode 语义，
  额外提供 per-capability 回滚史（Redis list，``sparkle:ops:rollback_history:*``）。
- 未知/越词表 mode **显式拒绝**（fail-closed），不复用 normalize_mode 的静默回落——
  运维面写错词不能被悄悄改写成 fallback_mode。
- Redis 缺席时写路径拒绝（503 语义），绝不把「未落盘的 no-op 写」冒充成功。

新增能力接线契约（registered-iff-read，V3-FIX-345 学说）：先有真实读者 + settings
tri-state 字段 + KillSwitchBinding（归服务模块所有），再在 ``CAPABILITY_SPECS``
追加一行 spec；``tests/unit/test_ops_surface_registry.py`` 的金样表与唯一性/
字段存在性守卫会同时钉住。
"""

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from typing import Any, Mapping

from app.core.kill_switch import (
    KillSwitchBinding,
    normalize_mode,
    read_mode,
    resolve_settings_mode,
    write_mode,
)

# ---------------------------------------------------------------------------
# 词表与键位
# ---------------------------------------------------------------------------

DOMAINS: frozenset[str] = frozenset({"aurora", "memory", "fme", "infra"})

HISTORY_KEY_TEMPLATE = "sparkle:ops:rollback_history:{capability_id}"
HISTORY_MAX_ENTRIES = 20
HISTORY_TTL_SECONDS = 30 * 24 * 3600

# normalize_mode 的 fallback 槽被借作「词表外」哨兵：本面禁用静默回落，
# 解析出哨兵即显式拒绝（见 _validate_mode）。
_INVALID_MODE = "__invalid__"


class CapabilityError(Exception):
    """Ops surface 基类错误（capability_id / 词表 / 前置条件）。"""


class UnknownCapabilityError(CapabilityError):
    """capability_id 不在注册表内（API 层映射 404）。"""


class InvalidModeError(CapabilityError):
    """mode 不在该绑定 allowed_modes 词表内（API 层映射 400）。"""


class NoRollbackPointError(CapabilityError):
    """回滚史中找不到与现值不同的恢复点（API 层映射 409）。"""


class RedisUnavailableError(CapabilityError):
    """写路径要求 Redis 在场；缺席即拒绝（API 层映射 503）。"""


# ---------------------------------------------------------------------------
# 注册表 —— 每行引用一个既有绑定（权威留在原模块，本表只持有走径）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CapabilitySpec:
    """单个受控能力：指向既有 KillSwitchBinding 的惰性走径 + 运维元数据.

    capability_id = ``<binding.stage>.<binding.feature>``，与 Prometheus
    ``KILL_SWITCH_MODE`` 的 (stage, feature) 标签逐字一致（可观测对齐）。
    prefix 必须与拥有方 service 传给 read_mode/write_mode 的 prefix 逐字一致
    （金样测试钉住）。
    """

    capability_id: str
    domain: str
    module: str
    binding_path: str
    prefix: str
    description: str


CAPABILITY_SPECS: tuple[CapabilitySpec, ...] = (
    # --- Aurora 横切面 ---
    CapabilitySpec(
        "doc_context.document_context_injection",
        "aurora",
        "app.services.aurora_doc_context_kill_switch_service",
        "AuroraDocContextKillSwitchService.BINDING",
        "aurora:doc_context:",
        "文档上下文注入",
    ),
    CapabilitySpec(
        "dual_core_router.mode",
        "aurora",
        "app.services.aurora_dual_core_router_kill_switch_service",
        "AuroraDualCoreRouterKillSwitchService.MASTER_BINDING",
        "aurora:dual_core_router:",
        "双核路由总开关",
    ),
    CapabilitySpec(
        "privacy.pii_redaction",
        "aurora",
        "app.services.aurora_privacy_kill_switch_service",
        "AuroraPrivacyKillSwitchService.BINDING",
        "aurora:privacy:",
        "PII 脱敏",
    ),
    CapabilitySpec(
        "23.mode",
        "aurora",
        "app.services.aurora_stage23_kill_switch_service",
        "AuroraStage23KillSwitchService.BINDING",
        "aurora:stage23:killswitch:",
        "贝叶斯证据融合",
    ),
    CapabilitySpec(
        "24.policy_compiler",
        "aurora",
        "app.services.aurora_stage24_policy_kill_switch_service",
        "AuroraStage24PolicyKillSwitchService.BINDING",
        "aurora:stage24:killswitch:",
        "策略编译器",
    ),
    CapabilitySpec(
        "25.reflection_wire",
        "aurora",
        "app.services.aurora_stage25_reflection_kill_switch_service",
        "AuroraStage25ReflectionKillSwitchService.BINDING",
        "aurora:stage25:killswitch:",
        "反思接线",
    ),
    CapabilitySpec(
        "26.scene",
        "aurora",
        "app.services.aurora_stage26_scene_kill_switch_service",
        "AuroraStage26SceneKillSwitchService.BINDING",
        "aurora:stage26:scene:",
        "场景理解",
    ),
    CapabilitySpec(
        "28.mode",
        "aurora",
        "app.services.aurora_stage28_traits_kill_switch_service",
        "AuroraStage28TraitsKillSwitchService.MASTER_BINDING",
        "aurora:stage28:traits:",
        "特质建模总开关",
    ),
    CapabilitySpec(
        "28.nlp",
        "aurora",
        "app.services.aurora_stage28_traits_kill_switch_service",
        "AuroraStage28TraitsKillSwitchService.NLP_BINDING",
        "aurora:stage28:traits:",
        "特质 NLP 抽取",
    ),
    CapabilitySpec(
        "28.coldstart",
        "aurora",
        "app.services.aurora_stage28_traits_kill_switch_service",
        "AuroraStage28TraitsKillSwitchService.COLDSTART_BINDING",
        "aurora:stage28:traits:",
        "特质冷启动",
    ),
    CapabilitySpec(
        "29.mode",
        "aurora",
        "app.services.aurora_stage29_srl_kill_switch_service",
        "AuroraStage29SRLKillSwitchService.MASTER_BINDING",
        "aurora:stage29:srl:",
        "SRL 总开关",
    ),
    CapabilitySpec(
        "29.tracker",
        "aurora",
        "app.services.aurora_stage29_srl_kill_switch_service",
        "AuroraStage29SRLKillSwitchService.TRACKER_BINDING",
        "aurora:stage29:srl:",
        "SRL 阶段追踪",
    ),
    CapabilitySpec(
        "29.bridge",
        "aurora",
        "app.services.aurora_stage29_srl_kill_switch_service",
        "AuroraStage29SRLKillSwitchService.BRIDGE_BINDING",
        "aurora:stage29:srl:",
        "SRL 桥",
    ),
    CapabilitySpec(
        "29.scaffolding_consume",
        "aurora",
        "app.services.aurora_stage29_srl_kill_switch_service",
        "AuroraStage29SRLKillSwitchService.SCAFFOLDING_BINDING",
        "aurora:stage29:srl:",
        "SRL 脚手架消费",
    ),
    CapabilitySpec(
        "31.idiographic",
        "aurora",
        "app.services.aurora_stage31_idiographic_kill_switch_service",
        "AuroraStage31IdiographicKillSwitchService.BINDING",
        "aurora:stage31:idiographic:",
        "个人化（idiographic）面",
    ),
    CapabilitySpec(
        "37.llm_safety",
        "aurora",
        "app.services.aurora_stage37_llm_safety_kill_switch_service",
        "_STAGE37_BINDING",
        "sparkle:",
        "LLM 安全护栏",
    ),
    CapabilitySpec(
        "38.err_replan",
        "aurora",
        "app.services.aurora_stage38_kill_switch_service",
        "_ERR_REPLAN_BINDING",
        "aurora_stage38:",
        "错误重规划",
    ),
    CapabilitySpec(
        "38.push_scheduler",
        "aurora",
        "app.services.aurora_stage38_kill_switch_service",
        "_PUSH_SCHEDULER_BINDING",
        "aurora_stage38:",
        "推送调度器",
    ),
    CapabilitySpec(
        "38.aurora_runtime",
        "aurora",
        "app.services.aurora_stage38_kill_switch_service",
        "_AURORA_RUNTIME_BINDING",
        "aurora_stage38:",
        "Aurora 运行时",
    ),
    CapabilitySpec(
        "39.mode",
        "aurora",
        "app.services.aurora_stage39_kill_switch_service",
        "_BINDING_MASTER",
        "sparkle:",
        "Stage39 总开关",
    ),
    CapabilitySpec(
        "39.scaffolding_prompt_mode",
        "aurora",
        "app.services.aurora_stage39_kill_switch_service",
        "_FEATURE_BINDINGS.scaffolding_prompt",
        "sparkle:",
        "脚手架提示",
    ),
    CapabilitySpec(
        "39.cogload_route_mode",
        "aurora",
        "app.services.aurora_stage39_kill_switch_service",
        "_FEATURE_BINDINGS.cogload_route",
        "sparkle:",
        "认知负载路由",
    ),
    CapabilitySpec(
        "39.galaxy_inject_mode",
        "aurora",
        "app.services.aurora_stage39_kill_switch_service",
        "_FEATURE_BINDINGS.galaxy_inject",
        "sparkle:",
        "星系注入",
    ),
    CapabilitySpec(
        "40.calendar",
        "aurora",
        "app.services.aurora_stage40_calendar_kill_switch_service",
        "AuroraStage40CalendarKillSwitchService.BINDING",
        "aurora:stage40:calendar:",
        "日历能力",
    ),
    CapabilitySpec(
        "meta_learning.routing_parameters",
        "aurora",
        "app.orchestration.routing_parameter_registry",
        "META_LEARNING_BINDING",
        "aurora:",
        "路由参数元学习",
    ),
    # --- Aurora stage 多特性族（stage 常量/类属性走径） ---
    CapabilitySpec(
        "18.aggregator",
        "aurora",
        "app.services.aurora_stage18_kill_switch_service",
        "AuroraStage18KillSwitchService.BINDINGS.aggregator_enabled",
        "aurora:stage18:killswitch:",
        "聚合器",
    ),
    CapabilitySpec(
        "18.push_policy",
        "aurora",
        "app.services.aurora_stage18_kill_switch_service",
        "AuroraStage18KillSwitchService.BINDINGS.push_policy_enabled",
        "aurora:stage18:killswitch:",
        "推送策略",
    ),
    CapabilitySpec(
        "18.push_delivery",
        "aurora",
        "app.services.aurora_stage18_kill_switch_service",
        "AuroraStage18KillSwitchService.BINDINGS.push_delivery_enabled",
        "aurora:stage18:killswitch:",
        "推送投递",
    ),
    CapabilitySpec(
        "20.sufficiency_judge",
        "aurora",
        "app.services.aurora_stage20_kill_switch_service",
        "AuroraStage20KillSwitchService.BINDINGS.sufficiency_judge",
        "aurora:stage20:killswitch:",
        "充分性判定",
    ),
    CapabilitySpec(
        "20.conflict_resolver",
        "aurora",
        "app.services.aurora_stage20_kill_switch_service",
        "AuroraStage20KillSwitchService.BINDINGS.conflict_resolver",
        "aurora:stage20:killswitch:",
        "冲突消解",
    ),
    CapabilitySpec(
        "21.skill_store",
        "aurora",
        "app.services.aurora_stage21_kill_switch_service",
        "AuroraStage21KillSwitchService.BINDINGS.skill_store_enabled",
        "aurora:stage21:killswitch:",
        "技能库",
    ),
    CapabilitySpec(
        "21.skill_selection",
        "aurora",
        "app.services.aurora_stage21_kill_switch_service",
        "AuroraStage21KillSwitchService.BINDINGS.skill_selection_enabled",
        "aurora:stage21:killswitch:",
        "技能选择",
    ),
    CapabilitySpec(
        "21.skill_share",
        "aurora",
        "app.services.aurora_stage21_kill_switch_service",
        "AuroraStage21KillSwitchService.BINDINGS.skill_share_enabled",
        "aurora:stage21:killswitch:",
        "技能共享",
    ),
    CapabilitySpec(
        "27.mode",
        "aurora",
        "app.services.aurora_stage27_foresight_kill_switch_service",
        "AuroraStage27ForesightKillSwitchService.MASTER_BINDING",
        "aurora:stage27:foresight:",
        "前瞻总开关",
    ),
    CapabilitySpec(
        "27.attractor",
        "aurora",
        "app.services.aurora_stage27_foresight_kill_switch_service",
        "AuroraStage27ForesightKillSwitchService.FEATURE_BINDINGS.attractor",
        "aurora:stage27:foresight:",
        "吸引子",
    ),
    CapabilitySpec(
        "27.deviation",
        "aurora",
        "app.services.aurora_stage27_foresight_kill_switch_service",
        "AuroraStage27ForesightKillSwitchService.FEATURE_BINDINGS.deviation",
        "aurora:stage27:foresight:",
        "偏差检测",
    ),
    CapabilitySpec(
        "27.jitai",
        "aurora",
        "app.services.aurora_stage27_foresight_kill_switch_service",
        "AuroraStage27ForesightKillSwitchService.FEATURE_BINDINGS.jitai",
        "aurora:stage27:foresight:",
        "即态（jitai）检测",
    ),
    CapabilitySpec(
        "30.mode",
        "aurora",
        "app.services.aurora_stage30_metacognition_kill_switch_service",
        "AuroraStage30MetacognitionKillSwitchService.MASTER_BINDING",
        "aurora:stage30:metacognition:",
        "元认知总开关",
    ),
    CapabilitySpec(
        "30.dashboard",
        "aurora",
        "app.services.aurora_stage30_metacognition_kill_switch_service",
        "AuroraStage30MetacognitionKillSwitchService.FEATURE_BINDINGS.dashboard",
        "aurora:stage30:metacognition:",
        "元认知仪表盘",
    ),
    CapabilitySpec(
        "30.process_scaffolding",
        "aurora",
        "app.services.aurora_stage30_metacognition_kill_switch_service",
        "AuroraStage30MetacognitionKillSwitchService.FEATURE_BINDINGS.process_scaffolding",
        "aurora:stage30:metacognition:",
        "过程脚手架",
    ),
    CapabilitySpec(
        "30.fsm_combine",
        "aurora",
        "app.services.aurora_stage30_metacognition_kill_switch_service",
        "AuroraStage30MetacognitionKillSwitchService.FEATURE_BINDINGS.fsm_combine",
        "aurora:stage30:metacognition:",
        "FSM 合并",
    ),
    CapabilitySpec(
        "33.mode",
        "aurora",
        "app.services.aurora_stage33_kill_switch_service",
        "AuroraStage33KillSwitchService.MASTER_BINDING",
        "aurora_stage33:",
        "Stage33 总开关",
    ),
    CapabilitySpec(
        "33.social",
        "aurora",
        "app.services.aurora_stage33_kill_switch_service",
        "AuroraStage33KillSwitchService.FEATURE_BINDINGS.social",
        "aurora_stage33:",
        "社交",
    ),
    CapabilitySpec(
        "33.srl",
        "aurora",
        "app.services.aurora_stage33_kill_switch_service",
        "AuroraStage33KillSwitchService.FEATURE_BINDINGS.srl",
        "aurora_stage33:",
        "SRL 关联",
    ),
    CapabilitySpec(
        "33.wm_prompt",
        "aurora",
        "app.services.aurora_stage33_kill_switch_service",
        "AuroraStage33KillSwitchService.FEATURE_BINDINGS.wm_prompt",
        "aurora_stage33:",
        "工作记忆提示",
    ),
    CapabilitySpec(
        "33.events",
        "aurora",
        "app.services.aurora_stage33_kill_switch_service",
        "AuroraStage33KillSwitchService.FEATURE_BINDINGS.events",
        "aurora_stage33:",
        "事件面",
    ),
    CapabilitySpec(
        "33.community",
        "aurora",
        "app.services.aurora_stage33_kill_switch_service",
        "AuroraStage33KillSwitchService.FEATURE_BINDINGS.community",
        "aurora_stage33:",
        "社群面",
    ),
    CapabilitySpec(
        "34.mode",
        "aurora",
        "app.services.aurora_stage34_kill_switch_service",
        "AuroraStage34KillSwitchService.MASTER_BINDING",
        "aurora_stage34:",
        "Stage34 总开关",
    ),
    CapabilitySpec(
        "34.error_bridge",
        "aurora",
        "app.services.aurora_stage34_kill_switch_service",
        "AuroraStage34KillSwitchService.FEATURE_BINDINGS.error_bridge",
        "aurora_stage34:",
        "错误桥",
    ),
    CapabilitySpec(
        "34.capsule",
        "aurora",
        "app.services.aurora_stage34_kill_switch_service",
        "AuroraStage34KillSwitchService.FEATURE_BINDINGS.capsule",
        "aurora_stage34:",
        "胶囊",
    ),
    CapabilitySpec(
        "34.journey_subscribers",
        "aurora",
        "app.services.aurora_stage34_kill_switch_service",
        "AuroraStage34KillSwitchService.FEATURE_BINDINGS.journey_subscribers",
        "aurora_stage34:",
        "旅程订阅者",
    ),
    CapabilitySpec(
        "35.mode",
        "aurora",
        "app.services.aurora_stage35_kill_switch_service",
        "AuroraStage35KillSwitchService.MASTER_BINDING",
        "aurora_stage35:",
        "Stage35 总开关",
    ),
    CapabilitySpec(
        "35.metacog_router",
        "aurora",
        "app.services.aurora_stage35_kill_switch_service",
        "AuroraStage35KillSwitchService.FEATURE_BINDINGS.metacog_router",
        "aurora_stage35:",
        "元认知路由",
    ),
    # --- Memory（stage19 = Memory V3，M-02 语义见绑定注释） ---
    CapabilitySpec(
        "19.working_memory",
        "memory",
        "app.services.aurora_stage19_kill_switch_service",
        "AuroraStage19KillSwitchService.BINDINGS.working_memory_enabled",
        "aurora:stage19:killswitch:",
        "工作记忆",
    ),
    CapabilitySpec(
        "19.llm_extractor",
        "memory",
        "app.services.aurora_stage19_kill_switch_service",
        "AuroraStage19KillSwitchService.BINDINGS.llm_extractor_enabled",
        "aurora:stage19:killswitch:",
        "LLM 记忆抽取",
    ),
    CapabilitySpec(
        "19.consolidation",
        "memory",
        "app.services.aurora_stage19_kill_switch_service",
        "AuroraStage19KillSwitchService.BINDINGS.consolidation_enabled",
        "aurora:stage19:killswitch:",
        "记忆巩固",
    ),
    CapabilitySpec(
        "19.storage_gate",
        "memory",
        "app.services.aurora_stage19_kill_switch_service",
        "AuroraStage19KillSwitchService.BINDINGS.storage_gate_enabled",
        "aurora:stage19:killswitch:",
        "episodic 写路径存储闸",
    ),
    # --- FME ---
    CapabilitySpec(
        "fme.goal_first_minute",
        "fme",
        "app.services.fme_kill_switch_service",
        "FmeKillSwitchService.FEATURE_BINDINGS.goal_first_minute",
        "fme:",
        "首分钟意图分析",
    ),
    CapabilitySpec(
        "fme.l3_closure", "fme", "app.services.fme_l3_closure_bridge", "_FME_L3_CLOSURE_BINDING", "aurora:", "L3 收口桥"
    ),
    # --- Infra（SLO 自动降级，写方 = app/api/internal/auto_degrade.py；
    #     键为 AlertType(StrEnum) 成员，str 段名即枚举值逐字） ---
    CapabilitySpec(
        "slo_auto.llm_degrade",
        "infra",
        "app.api.internal.auto_degrade",
        "SLO_AUTO_DEGRADE_BINDINGS.LLM_LATENCY_HIGH",
        "sparkle:",
        "LLM 降档",
    ),
    CapabilitySpec(
        "slo_auto.redis_fallback",
        "infra",
        "app.api.internal.auto_degrade",
        "SLO_AUTO_DEGRADE_BINDINGS.REDIS_NEAR_FULL",
        "sparkle:",
        "Redis 磁盘兜底",
    ),
    CapabilitySpec(
        "slo_auto.db_throttle",
        "infra",
        "app.api.internal.auto_degrade",
        "SLO_AUTO_DEGRADE_BINDINGS.DB_CONNECTION_EXHAUST",
        "sparkle:",
        "DB 连接节流",
    ),
    CapabilitySpec(
        "slo_auto.event_bus_throttle",
        "infra",
        "app.api.internal.auto_degrade",
        "SLO_AUTO_DEGRADE_BINDINGS.EVENT_BUS_LAG",
        "sparkle:",
        "事件总线节流",
    ),
    CapabilitySpec(
        "slo_auto.rate_limit_tighten",
        "infra",
        "app.api.internal.auto_degrade",
        "SLO_AUTO_DEGRADE_BINDINGS.GW_HIGH_5XX",
        "sparkle:",
        "限流收紧/熔断",
    ),
)

_SPEC_INDEX: dict[str, CapabilitySpec] = {spec.capability_id: spec for spec in CAPABILITY_SPECS}


def get_spec(capability_id: str) -> CapabilitySpec:
    """按 capability_id 取 spec；未知 id 抛 UnknownCapabilityError（fail-closed）。"""
    spec = _SPEC_INDEX.get(str(capability_id or "").strip())
    if spec is None:
        raise UnknownCapabilityError(f"unknown capability_id: {capability_id!r}")
    return spec


@cache
def _resolve_attr_path(module_name: str, attr_path: str) -> Any:
    """惰性解析 ``模块.属性路径``（getattr 优先、Mapping 键兜底），并缓存结果."""
    module = importlib.import_module(module_name)
    current: Any = module
    for segment in attr_path.split("."):
        if hasattr(current, segment):
            current = getattr(current, segment)
        elif isinstance(current, Mapping) and segment in current:
            current = current[segment]
        else:
            raise CapabilityError(f"cannot resolve {module_name}.{attr_path} at segment {segment!r}")
    return current


def resolve_binding(spec: CapabilitySpec) -> KillSwitchBinding:
    """解析 spec 指向的既有 KillSwitchBinding 实例（权威对象，非副本）。"""
    binding = _resolve_attr_path(spec.module, spec.binding_path)
    if not isinstance(binding, KillSwitchBinding):
        raise CapabilityError(f"{spec.capability_id}: resolved object is not a KillSwitchBinding")
    return binding


# ---------------------------------------------------------------------------
# 观测（读路径：永远可用，Redis 缺席回落 settings 判据并如实标注）
# ---------------------------------------------------------------------------


def describe_capabilities() -> list[dict[str, Any]]:
    """静态描述（无 I/O）：注册表清单。"""
    return [
        {
            "capability_id": spec.capability_id,
            "domain": spec.domain,
            "stage": resolve_binding(spec).stage,
            "feature": resolve_binding(spec).feature,
            "settings_attr": resolve_binding(spec).settings_attr,
            "fallback_mode": resolve_binding(spec).fallback_mode,
            "redis_key": f"{spec.prefix}{resolve_binding(spec).redis_key}",
            "description": spec.description,
        }
        for spec in CAPABILITY_SPECS
    ]


async def capability_snapshot(redis_client: Any, spec: CapabilitySpec) -> dict[str, Any]:
    """单能力当前态：运行时模式（Redis 优先）+ settings 判据模式 + 恢复点数."""
    binding = resolve_binding(spec)
    settings_mode = resolve_settings_mode(binding)
    if redis_client is not None:
        runtime_mode = await read_mode(redis_client=redis_client, prefix=spec.prefix, binding=binding)
        runtime_available = True
    else:
        # 与 kill_switch.read_mode 的缺席语义一致：回落 settings 判据。
        runtime_mode = settings_mode
        runtime_available = False
    return {
        "capability_id": spec.capability_id,
        "domain": spec.domain,
        "mode": runtime_mode,
        "settings_mode": settings_mode,
        "runtime_mode_available": runtime_available,
        "stage": binding.stage,
        "feature": binding.feature,
        "settings_attr": binding.settings_attr,
        "fallback_mode": binding.fallback_mode,
        "redis_key": f"{spec.prefix}{binding.redis_key}",
        "description": spec.description,
    }


async def list_capability_snapshots(redis_client: Any) -> list[dict[str, Any]]:
    """全量能力快照（flag 状态可观测的主读面）。"""
    return [await capability_snapshot(redis_client, spec) for spec in CAPABILITY_SPECS]


async def _history_length(redis_client: Any, spec: CapabilitySpec) -> int:
    return int(await redis_client.llen(_history_key(spec)))


def _history_key(spec: CapabilitySpec) -> str:
    return HISTORY_KEY_TEMPLATE.format(capability_id=spec.capability_id)


async def capability_history(redis_client: Any, spec: CapabilitySpec, limit: int = 10) -> list[dict[str, Any]]:
    """回滚史尾部（最新在前）。Redis 缺席返回空表（读路径不抛）。"""
    if redis_client is None:
        return []
    raw_entries = await redis_client.lrange(_history_key(spec), 0, max(0, limit - 1))
    entries: list[dict[str, Any]] = []
    for raw in raw_entries:
        try:
            entries.append(_decode_entry(raw))
        except CapabilityError:
            continue
    return entries


# ---------------------------------------------------------------------------
# 受控翻转 + per-capability 回滚
# ---------------------------------------------------------------------------


def _decode_entry(raw: Any) -> dict[str, Any]:
    try:
        entry = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise CapabilityError(f"malformed history entry: {exc}") from exc
    if not isinstance(entry, dict) or "from" not in entry or "to" not in entry:
        raise CapabilityError("malformed history entry")
    return entry


def _encode_entry(entry: Mapping[str, Any]) -> str:
    return json.dumps(entry, ensure_ascii=False, sort_keys=True)


def _validate_mode(mode: Any, binding: KillSwitchBinding) -> str:
    """词表严格校验：合法即归一化返回，越词表显式拒绝（不静默回落）。"""
    normalized = normalize_mode(mode, allowed_modes=binding.allowed_modes, fallback=_INVALID_MODE)
    if normalized == _INVALID_MODE:
        raise InvalidModeError(f"mode {mode!r} outside allowed vocabulary {sorted(binding.allowed_modes)}")
    return normalized


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


async def set_capability_mode(
    redis_client: Any,
    spec: CapabilitySpec,
    mode: Any,
    *,
    actor: str = "ops-api",
    reason: str | None = None,
) -> dict[str, Any]:
    """翻转单个能力模式：先记回滚史，再走核心 write_mode（语义与拥有方一致）.

    Redis 缺席 → 拒绝（write_mode 对 None client 只 log 不落盘，运维面绝不把
    no-op 冒充成功）；词表外 mode → 拒绝。回滚史写入失败不阻断翻转本身
    （翻转是权威动作，史是兜下面），但响应里如实标注 history_recorded。
    """
    if redis_client is None:
        raise RedisUnavailableError("Redis unavailable: refusing mode write that would not persist (fail-closed)")
    binding = resolve_binding(spec)
    normalized = _validate_mode(mode, binding)
    previous_mode = await read_mode(redis_client=redis_client, prefix=spec.prefix, binding=binding)

    applied_mode = await write_mode(
        redis_client=redis_client,
        prefix=spec.prefix,
        binding=binding,
        mode=normalized,
    )

    entry = {
        "from": previous_mode,
        "to": applied_mode,
        "actor": actor,
        "at": _utcnow_iso(),
        "action": "set",
        "reason": reason,
    }
    history_recorded = await _push_history(redis_client, spec, entry)
    return {
        "capability_id": spec.capability_id,
        "previous_mode": previous_mode,
        "mode": applied_mode,
        "actor": actor,
        "history_recorded": history_recorded,
    }


async def rollback_capability(
    redis_client: Any,
    spec: CapabilitySpec,
    *,
    actor: str = "ops-api",
) -> dict[str, Any]:
    """回滚到回滚史中最近的「与现值不同」的先前模式（stepwise、可连续回退）.

    语义：读全史（最新在前）→ 在 ``action=="set"`` 记录中找第一条
    ``from != 当前模式`` 的条目 → 经核心 write_mode 恢复该 ``from`` → 该条目
    （含其上的同值记录）出栈，并压入一条 rollback 标记。rollback 标记本身
    **不是**恢复点（否则连续回滚会在「回滚前值」上震荡），扫描时跳过。
    找不到可恢复点 → NoRollbackPointError。
    """
    if redis_client is None:
        raise RedisUnavailableError("Redis unavailable: rollback history lives in Redis (fail-closed)")
    binding = resolve_binding(spec)
    current_mode = await read_mode(redis_client=redis_client, prefix=spec.prefix, binding=binding)

    raw_entries = await redis_client.lrange(_history_key(spec), 0, -1)
    entries: list[dict[str, Any]] = []
    for raw in raw_entries:
        try:
            entries.append(_decode_entry(raw))
        except CapabilityError:
            continue  # 损坏条目跳过，不阻断可用恢复点的查找

    restore_index = next(
        (i for i, entry in enumerate(entries) if entry.get("action") == "set" and entry.get("from") != current_mode),
        None,
    )
    if restore_index is None:
        raise NoRollbackPointError(f"no rollback point available for {spec.capability_id}")

    restore_mode_raw = entries[restore_index]["from"]
    restore_mode = _validate_mode(restore_mode_raw, binding)
    applied_mode = await write_mode(
        redis_client=redis_client,
        prefix=spec.prefix,
        binding=binding,
        mode=restore_mode,
    )

    rollback_entry = {
        "from": current_mode,
        "to": applied_mode,
        "actor": actor,
        "at": _utcnow_iso(),
        "action": "rollback",
        "reason": None,
    }
    remaining = entries[restore_index + 1 :] + [rollback_entry]
    key = _history_key(spec)
    try:
        await redis_client.delete(key)
        if remaining:
            encoded = [
                _encode_entry(entry) for entry in reversed(remaining)
            ]  # RPUSH 后 index 0=最新（与 LPUSH 约定一致）
            await redis_client.rpush(key, *encoded)
            await redis_client.ltrim(key, 0, HISTORY_MAX_ENTRIES - 1)
        await redis_client.expire(key, HISTORY_TTL_SECONDS)
        history_recorded = True
    except Exception:
        # 史损坏不阻断回滚本身；模式已恢复，如实返回。
        history_recorded = False

    return {
        "capability_id": spec.capability_id,
        "previous_mode": current_mode,
        "mode": applied_mode,
        "actor": actor,
        "rolled_back_to_entry": entries[restore_index],
        "history_recorded": history_recorded,
    }


async def _push_history(redis_client: Any, spec: CapabilitySpec, entry: Mapping[str, Any]) -> bool:
    key = _history_key(spec)
    try:
        encoded = _encode_entry(entry)
        await redis_client.lpush(key, encoded)
        await redis_client.ltrim(key, 0, HISTORY_MAX_ENTRIES - 1)
        await redis_client.expire(key, HISTORY_TTL_SECONDS)
        return True
    except Exception:
        return False
