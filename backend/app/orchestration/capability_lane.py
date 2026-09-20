"""E-02 能力路由：Fast Semantic / Deliberate Decision lane 判定。

Core: infra ｜ Phase: sense/clarify ｜ Stage: E-02

定位（E-01 ROUTING_MAP §4 C1 探针四步法结论，2026-09-19）：
- 记忆指令/检索问答级消息长期落 plus+balanced 的判据破点 =
  ``_should_use_slim_standard_context`` 被
  ``retrieval_decision.should_retrieve=True`` 一票否决；记忆类消息会被
  retrieval_intent 误判为 ambiguous("帮我")/knowledge("是什么") →
  graph_only/targeted_source_rag。
- 本模块给出确定性的能力 lane 判定（零 LLM）：
  - FAST（L1 Fast Semantic）：记忆指令确认、记忆检索问答、轻量标准问答——
    单次轻调用（thinking off），走既有 balanced fast path 机制（FAST tier +
    QUICK_QUERY），slim 上下文保留记忆最小说集（MR-2）。
  - DELIBERATE（L2/L3）：工具流（exam_preparation/task_decomposition/
    skill_building 的 planned_tool_sequence）、文档接地检索、专家协作、
    深度词、超长消息、非 standard chat_mode。

保护约束（硬规则）：
- ``planned_tool_sequence`` 在场 → 永远 DELIBERATE（exam_preparation 工具流
  依赖真实工具执行，不得被 fast lane 降级成"会说话但不能执行"）。
- 文档级检索模式（targeted_source_rag / deep_source_synthesis /
  user_pinned_sources / task_bound_rag）→ DELIBERATE。
- graph_only 仅对记忆类消息放行 FAST（graph_only=用户知识星图摘要，非文档；
  但规划类消息同样落 graph_only，必须保持 DELIBERATE）。
- 方法建议问法（怎么/如何/怎样记住…、有什么记住…的方法）语义是求方法而非
  写记忆 → 不属记忆类，保持文档接地/deliberate（R2-F1）；"我记住了…"
  完成时陈述同理（R2-F1b）。

与 dual_core（认知调制轴）正交：本模块只决定模型深度轴（fast/deliberate）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from loguru import logger

from app.core.metrics import CHAT_CAPABILITY_LANE_TOTAL


class ChatCapabilityLane(StrEnum):
    FAST = "fast"
    DELIBERATE = "deliberate"


MEMORY_CLASS_INSTRUCTION = "memory_instruction"
MEMORY_CLASS_QUERY = "memory_retrieval_query"

# —— 记忆指令（写入/更新用户记忆）——
_MEMORY_INSTRUCTION_RE = re.compile(r"(请)?(帮我)?(记一下|记住|记着|记下来|别忘了|不要忘记)")

# —— 记忆检索问答（第一人称 + 身份/回属性疑问）——
# 只收"关于用户自身事实"的疑问（是什么/有哪些/有几个/是谁/多少/几点/什么来着），
# 排除为什么（自我分析）、怎么/如何（方法建议）——这两类需要 deliberate。
# (?!们) 排除"我们…"（小组/团体事实，非用户个人记忆，记忆系统无此数据）；
# "问我"（老师问我…）是转述第三方问答，同样排除。
_MEMORY_QUERY_RE = re.compile(r"我(?!们).{0,24}(是什么|是什么来着|叫什么|有哪些|有几个|是谁|多少|什么时候|几点)")

# —— 反模式（指令）：文档诉求 / 工具-规划动作 / 深度词 ——
# 注意只排"动作词"（制定/安排/创建...），不排名词（复习/考试可以是被记住的事实：
# "记一下我的复习方式是刷题"仍是记忆指令）；"记住…然后帮我制定计划"类复合
# 意图含动作词 → 排除，交给 planned_tool_sequence 工具流。
# R2-F1：方法建议问法族（怎么记住/如何记住/有什么记住…的方法）是核心高频学习
# 问法，语义是求方法（deliberate/文档接地），不是写记忆——动词裸匹配必须排除；
# "记住了/记下了"（完成时陈述，如"我记住了老师讲的重点"）不是写入指令。
_MEMORY_INSTRUCTION_EXCLUDE_RE = re.compile(
    r"(资料|文档|文件|课件|论文|pdf"
    r"|制定|规划|安排|拆解|创建|新建|添加|保存|同步|提醒|预约|倒计时"
    r"|create|add|save|remind|schedule"
    r"|深入|详细|原理|推导|证明|严谨|系统地|in depth|deep dive"
    r"|为什么|错在哪|诊断"
    r"|怎么|如何|怎样|方法|技巧|妙招|更快|更高效|更有效"
    r"|记住了|记下了|接下来)"
)

# —— 反模式（检索问答）：指令反模式 + 计划/任务数据名词 ——
# "我的计划是什么"类问题需要计划工具数据，保持 deliberate。
_MEMORY_QUERY_EXCLUDE_RE = re.compile(
    r"(资料|文档|文件|课件|论文|pdf"
    r"|制定|规划|安排|拆解|创建|新建|添加|保存|同步|提醒|预约|倒计时"
    r"|create|add|save|remind|schedule"
    r"|深入|详细|原理|推导|证明|严谨|系统地|in depth|deep dive"
    r"|为什么|错在哪|诊断"
    r"|计划|任务|日程|进度|待办|plan|task|todo"
    r"|问我)"
)

_DOCUMENT_RETRIEVAL_MODES = {
    "targeted_source_rag",
    "deep_source_synthesis",
    "user_pinned_sources",
    "task_bound_rag",
}

_FAST_CHAT_MODES = {"standard", "chat"}

# 深度词标记（与 generation 的 balanced fast path 判据同源共享——
# standard_workflow._should_force_balanced_fast_first_touch 直接引用本常量，
# 避免两处清单漂移导致 lane 可观测与实际 tier 行为不一致）。
DEEP_ANALYSIS_TEXT_MARKERS = (
    "深入",
    "详细",
    "原理",
    "推导",
    "证明",
    "严谨",
    "系统地",
    "systematically",
    "in depth",
    "deep dive",
    "why exactly",
)

# 轻量回复反指标：显式工具动作意图 / 个人数据意图（R2-F2B：与 generation 层
# `_should_disable_tools_for_light_standard_reply` 同源共享——standard_workflow
# 直接引用本常量，禁止再抄清单；命中任一词的轮次实际 tier 走默认链（工具/
# 个人数据需要完整上下文），lane 必须如实报 deliberate）。
LIGHT_REPLY_TOOL_INTENT_MARKERS = (
    "创建",
    "新建",
    "添加",
    "保存",
    "同步",
    "提醒",
    "加入日历",
    "开始专注",
    "帮我建",
    "帮我加",
    "帮我创建",
    "帮我安排",
    "设个提醒",
    "预约",
    "schedule",
    "remind",
    "create",
    "add",
    "save",
    "sync",
    "start focus",
    # 材料检索意图（2026-09-20 演示验证实锤：问「上传的小结/材料/出处」
    # 被判 light_standard_reply → generation 关工具 → 模型拿不到
    # retrieve_user_material，引用问答全断——检索材料是工具意图，
    # 命中即走 DELIBERATE 保工具）
    "材料",
    "小结",
    "笔记",
    "文档",
    "资料",
    "出处",
    "引用",
    "来源",
    "上传",
    "我传的",
    "附件",
    "document",
    "material",
    "citation",
    "reference",
    "source",
)
LIGHT_REPLY_PERSONAL_DATA_MARKERS = (
    "我的计划",
    "我现在的计划",
    "我的任务",
    "我当前的任务",
    "我的日程",
    "我的日历",
    "我的知识星图",
    "我的画像",
    "我的专注",
    "我的进度",
    "我的状态",
    "结合我现在",
    "根据我的",
    "看看我的",
    "查一下我的",
    "我今天要做什么",
    "我今天该做什么",
    "my plan",
    "my task",
    "my tasks",
    "my schedule",
    "my calendar",
    "my progress",
    "my profile",
    "based on my",
    "check my",
)


def _light_reply_text_allowed(lowered_text: str) -> bool:
    """轻量 fast 判据的文本面：无工具动作/个人数据意图词（与 generation 层同源）。"""
    return not (
        any(marker in lowered_text for marker in LIGHT_REPLY_TOOL_INTENT_MARKERS)
        or any(marker in lowered_text for marker in LIGHT_REPLY_PERSONAL_DATA_MARKERS)
    )


def classify_memory_class_message(text: str) -> str | None:
    """判定消息是否属于记忆类（写入指令 / 检索问答）。

    返回 ``memory_instruction`` / ``memory_retrieval_query`` / None。
    纯规则、零 LLM；反模式（规划/深度/文档/工具动作/自我分析）优先排除。
    """
    normalized = str(text or "").strip()
    if not normalized or len(normalized) > 200:
        return None
    if _MEMORY_INSTRUCTION_RE.search(normalized):
        if _MEMORY_INSTRUCTION_EXCLUDE_RE.search(normalized):
            return None
        return MEMORY_CLASS_INSTRUCTION
    if _MEMORY_QUERY_RE.search(normalized):
        if _MEMORY_QUERY_EXCLUDE_RE.search(normalized):
            return None
        return MEMORY_CLASS_QUERY
    return None


@dataclass(frozen=True)
class CapabilityLaneDecision:
    """每 turn 的能力 lane 判定（可观测）。"""

    lane: ChatCapabilityLane
    reasons: tuple[str, ...] = field(default_factory=tuple)
    memory_class: str | None = None
    retrieval_mode: str = "unknown"
    tool_flow_protected: bool = False

    @property
    def trigger(self) -> str:
        return self.reasons[0] if self.reasons else ("fast" if self.lane is ChatCapabilityLane.FAST else "deliberate")

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane": self.lane.value,
            "reasons": list(self.reasons),
            "memory_class": self.memory_class,
            "retrieval_mode": self.retrieval_mode,
            "tool_flow_protected": self.tool_flow_protected,
        }


def _resolve_retrieval_decision(
    context_data: dict[str, Any] | None,
    retrieval_decision: dict[str, Any] | None,
) -> dict[str, Any]:
    if isinstance(retrieval_decision, dict):
        return retrieval_decision
    if isinstance(context_data, dict):
        for key in ("document_retrieval_decision", "retrieval_decision"):
            value = context_data.get(key)
            if isinstance(value, dict):
                return value
    return {}


def resolve_capability_lane(
    *,
    user_message: str,
    context_data: dict[str, Any] | None,
    retrieval_decision: dict[str, Any] | None = None,
    reasoning_mode: str | None = None,
) -> CapabilityLaneDecision:
    """按消息能力需求判定 fast/deliberate lane（零 LLM）。

    判定顺序（先命中先定，reasons 记录全部触发的标签）：
    1. planned_tool_sequence（exam/task/skill 工具流）→ DELIBERATE
    2. chat_mode 非 standard/chat（deep_analysis/study_plan/expert...）→ DELIBERATE
    3. 用户显式 deep 模式 → DELIBERATE（lane 反映生效行为，非意图）
    4. 文档在场（file_ids/document_context）/ 显式专家角色 → DELIBERATE
    5. 文档级检索模式 → DELIBERATE
    6. 记忆类消息（graph_only 或 no_retrieval，且 ≤120 字、无工具/个人数据
       意图词——与 balanced fast path 文本判据同源）→ FAST
    7. 轻量标准问答（短、无深度词、无检索需求、无工具/个人数据意图词）→ FAST；
       含深度词或工具/个人数据意图词 → DELIBERATE
    8. 其余（含超长/带检索的通用消息）→ DELIBERATE
    """
    context = context_data if isinstance(context_data, dict) else {}
    text = str(user_message or "").strip()
    reasons: list[str] = []

    retrieval = _resolve_retrieval_decision(context, retrieval_decision)
    retrieval_mode = str(retrieval.get("retrieval_mode") or "unknown")
    should_retrieve = bool(retrieval.get("should_retrieve"))

    planned_tools = context.get("planned_tool_sequence")
    tool_flow_protected = bool(planned_tools)

    chat_mode = str(context.get("chat_mode") or "standard").strip().lower()
    has_documents = bool(context.get("file_ids")) or bool(str(context.get("document_context") or "").strip())
    has_experts = bool(context.get("selected_experts") or context.get("answer_experts"))
    has_explicit_role = bool(str(context.get("agent_role") or "").strip())

    memory_class = classify_memory_class_message(text)
    user_mode = str(reasoning_mode or "").strip().lower()

    # 1. 工具流保护（exam_preparation/task_decomposition/skill_building）
    if tool_flow_protected:
        reasons.append("tool_flow_protected")
    # 2. 非 standard chat_mode
    if chat_mode not in _FAST_CHAT_MODES:
        reasons.append(f"chat_mode_{chat_mode}")
    # 3. 用户显式 deep 模式
    if user_mode == "deep":
        reasons.append("user_mode_deep")
    # 4. 文档在场 / 显式专家角色
    if has_documents:
        reasons.append("document_grounded")
    if has_explicit_role:
        reasons.append("explicit_agent_role")
    # 5. 专家协作
    if has_experts:
        reasons.append("experts_selected")
    # 6. 文档级检索模式
    if should_retrieve and retrieval_mode in _DOCUMENT_RETRIEVAL_MODES:
        reasons.append("document_retrieval")

    if reasons:
        return CapabilityLaneDecision(
            lane=ChatCapabilityLane.DELIBERATE,
            reasons=tuple(reasons),
            memory_class=memory_class,
            retrieval_mode=retrieval_mode,
            tool_flow_protected=tool_flow_protected,
        )

    # 7. 记忆类消息：graph_only（知识星图/用户图，非文档）或无检索 → FAST。
    # R2-F2A/F2B：与实际 tier 判据同源——balanced fast path 还要求 ≤120 字且
    # `_should_disable_tools_for_light_standard_reply` 放行（无工具/个人数据
    # 意图词）。超长（121–200）或含个人数据词的记忆轮实际走默认链 → lane
    # 不得报 fast（否则 D-06 L1 占比被系统性高估）。
    lowered = text.lower()
    if (
        memory_class is not None
        and (not should_retrieve or retrieval_mode == "graph_only")
        and len(text) <= 120
        and _light_reply_text_allowed(lowered)
    ):
        reasons.append(
            "memory_instruction_fast_lane" if memory_class == MEMORY_CLASS_INSTRUCTION else "memory_query_fast_lane"
        )
        return CapabilityLaneDecision(
            lane=ChatCapabilityLane.FAST,
            reasons=tuple(reasons),
            memory_class=memory_class,
            retrieval_mode=retrieval_mode,
            tool_flow_protected=False,
        )

    # 8. 轻量标准问答（与 balanced fast path 判据同域：短消息、无深度词、无检索需求）。
    # 深度词在场时实际 tier 走默认链（deep 标记否决 balanced fast path）→ lane 必须如实
    # 反映 deliberate，否则遥测把 deliberate 轮误计为 fast。
    if text and len(text) <= 120 and not should_retrieve:
        if any(marker in lowered for marker in DEEP_ANALYSIS_TEXT_MARKERS):
            return CapabilityLaneDecision(
                lane=ChatCapabilityLane.DELIBERATE,
                reasons=("deep_marker_text",),
                memory_class=memory_class,
                retrieval_mode=retrieval_mode,
                tool_flow_protected=False,
            )
        # R2-F2B：个人数据/工具意图词轮次实际 tier 走默认链（light-reply 判据
        # 否决 slim），lane 必须报 deliberate。
        if not _light_reply_text_allowed(lowered):
            return CapabilityLaneDecision(
                lane=ChatCapabilityLane.DELIBERATE,
                reasons=("personal_data_or_tool_intent",),
                memory_class=memory_class,
                retrieval_mode=retrieval_mode,
                tool_flow_protected=False,
            )
        return CapabilityLaneDecision(
            lane=ChatCapabilityLane.FAST,
            reasons=("light_standard_reply",),
            memory_class=None,
            retrieval_mode=retrieval_mode,
            tool_flow_protected=False,
        )

    # 8. 其余（含超长/带检索的通用消息）→ DELIBERATE
    return CapabilityLaneDecision(
        lane=ChatCapabilityLane.DELIBERATE,
        reasons=(("retrieval_required",) if should_retrieve else ("default_deliberate",)),
        memory_class=memory_class,
        retrieval_mode=retrieval_mode,
        tool_flow_protected=False,
    )


def record_capability_lane_decision(
    decision: CapabilityLaneDecision,
    *,
    context_data: dict[str, Any] | None = None,
) -> None:
    """lane 判定落遥测（结构化日志 + counter）并回写 context_data 供下游透传。"""
    try:
        CHAT_CAPABILITY_LANE_TOTAL.labels(
            lane=decision.lane.value,
            memory_class=decision.memory_class or "none",
            retrieval_mode=decision.retrieval_mode or "unknown",
            trigger=decision.trigger,
        ).inc()
    except Exception:  # pragma: no cover - 遥测失败不影响主链路
        logger.opt(exception=True).warning("capability lane metric recording failed")

    logger.info(
        "[CapabilityLane] lane={} memory_class={} retrieval_mode={} tool_flow_protected={} reasons={}",
        decision.lane.value,
        decision.memory_class or "none",
        decision.retrieval_mode,
        decision.tool_flow_protected,
        list(decision.reasons),
    )

    if isinstance(context_data, dict):
        context_data["capability_lane"] = decision.to_dict()
