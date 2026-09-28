"""V4-I09 真正零模型的确定性快路（L0）：问候/确认/无信息量轮的纯模板应答。

定位（B06 全链探针实证，v4/evidence/V4-B06/probe/probe_raw.json t3）：
问候语轮现行仍进 generation_node → 真实上游流式调用（dashscope 400）→
rescue 非流式二次调用 → 合成估算记账 44 tok（客户端零 usage 帧）——
「已知问候/状态不走分类+生成双调用」（LATENCY_COST_RUNTIME L0 铁律）在
现行代码不成立，既有「快路」（capability_lane fast / balanced fast path）
仍烧真实模型。本模块补上真正的零模型层：

- 纯规则判定（零 LLM、零 embedding、零上游调用）+ 版本化模板直出；
- 命中即 token=0 且无任何隐含模型 attempt（路由层跳过 RouterNode 的
  embedding 相似度调用，生成层短路 generation，审查层显式跳过）；
- 记账面跳过合成 token 估算（response_builder._cleanup），不再产生
  「模板直出却记 44 tok 估算」的计量污染；
- lane 契约可观测：``context_data["chat_lane"]`` ∈ {"deterministic",
  "model"}（model = 既有真模型慢路，capability_lane fast/deliberate 继续
  表述模型深度轴），终帧 metadata 透传 ``chat_lane``。

保护约束（硬边界，卡验收「有效首内容不以 stage/ack/模板鸡汤抵扣」）：
- 只吃「剥掉问候/确认/告别词与标点语气词后无剩余实质内容」的短消息；
- 剥词后仍有任何实质字符（中英文/数字）→ 一律回落慢路（真模型）；
- 上下文防误伤（与 capability_lane 的 deliberate 触发同源）：工具流在场、
  非 standard chat_mode、显式 deep 模式、文档/专家/显式角色、文档级检索 →
  永不快路；
- 文本防误伤（同源共享 capability_lane 常量，禁止抄清单）：工具动作意图、
  个人数据意图、深度词任一命中 → 永不快路；
- 确认类（好的/收到/嗯…）在上一条助手消息以问句/提案收尾时不生效——
  「好的」可能是对提案的应允（模型需要执行动作），不得被模板顶掉。

行为开关：``ENABLE_DETERMINISTIC_FAST_LANE``（settings.py，默认 False，
release_flags 同族模式——权威在 Settings 单例）。关闭时本模块零行为，
既有真模型链路逐字节保持。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from loguru import logger

from app.core.metrics import CHAT_DETERMINISTIC_LANE_TOTAL
from app.orchestration.capability_lane import (
    _DOCUMENT_RETRIEVAL_MODES,
    DEEP_ANALYSIS_TEXT_MARKERS,
    _light_reply_text_allowed,
)


class DeterministicLaneKind(StrEnum):
    """零模型快路命中的消息形态（封闭枚举，metric kind 标签取值域）。"""

    GREETING = "greeting"  # 问候/寒暄/在吗
    ACKNOWLEDGMENT = "acknowledgment"  # 确认/致谢/语气附和（无信息量轮）
    FAREWELL = "farewell"  # 告别/晚安


CHAT_LANE_DETERMINISTIC = "deterministic"
CHAT_LANE_MODEL = "model"

# 消息长度上限（问候/确认天然短句；超长/刷屏一律慢路）。
_MAX_LANE_MESSAGE_CHARS = 24

# —— 问候词（含在吗类呼叫）——
_GREETING_TOKENS: tuple[str, ...] = (
    "good morning",
    "good afternoon",
    "good evening",
    "hello there",
    "hello",
    "hi",
    "hey",
    "你好呀",
    "您好",
    "你好",
    "哈喽",
    "哈罗",
    "嗨",
    "早上好",
    "早晨好",
    "上午好",
    "中午好",
    "下午好",
    "晚上好",
    "在不在",
    "在吗",
    "在么",
    "在嘛",
    "在",
)

# —— 确认/致谢词（无信息量轮；待提案守卫见 _ASSISTANT_PROPOSAL_MARKERS）——
_ACKNOWLEDGMENT_TOKENS: tuple[str, ...] = (
    "thank you",
    "thanks",
    "thx",
    "好嘞好嘞",
    "好的好的",
    "没问题的",
    "没问题",
    "收到",
    "明白啦",
    "明白了",
    "明白",
    "了解",
    "知道啦",
    "知道了",
    "懂了",
    "多谢",
    "感谢",
    "谢谢",
    "谢啦",
    "3q",
    "嗯哼",
    "嗯嗯",
    "嗯呐",
    "嗯呢",
    "嗯",
    "好滴",
    "好嘞",
    "好哒",
    "好呀",
    "好哦",
    "好的",
    "哈哈",
    "嘿嘿",
    "嘻嘻",
    "呵呵",
    "okay",
    "okok",
    "ok",
    "kk",
    "okk",
    "好",
)

# —— 告别词 ——
_FAREWELL_TOKENS: tuple[str, ...] = (
    "good night",
    "bye bye",
    "byebye",
    "bye",
    "下次见",
    "回见",
    "拜拜",
    "再见",
    "晚安",
)

# 有意排除（语义依赖上下文，模板直出会丢动作/答非所问）：
# - 对/是的/没错/行/可以/中：可能是对助手提案的应允（需执行动作）
# - 继续/go on/continue：指「继续上文」，需模型续写
# - no/nope：拒绝也可能是决策
# 排除方式：不进词表即可（剥词校验会让「对的，但是…」这类复合句自然回落慢路）。

# 上一条助手消息含问句/提案收尾 → 确认类可能是应允，快路必须让位。
_ASSISTANT_PROPOSAL_MARKERS: tuple[str, ...] = (
    "？",
    "?",
    "吗",
    "要不要",
    "需要我",
    "要我",
    "是否",
)

# 剥词后的语气词/标点白名单（纯语气词不构成实质内容）。
_FILLER_CHARS = frozenset(
    " \t\r\n。，、！!？?~～·.,;；:：-—_()（）[]【】{}《》<>“”‘’\"'`|\\/*&#@$%^+=…‥"
    "呀啊哟哦噢喔哈嘿啦咯呗嘞哒滴咩哇咯唷"
)

_SUBSTANTIVE_RE = re.compile(r"[0-9a-zA-Z\u4e00-\u9fff\uff10-\uff19]")  # R1-C2: 全角数字０-９

# 上下文守卫复用 capability_lane 的 deliberate 触发面（单一权威）。
_FAST_CHAT_MODES = {"standard", "chat"}

# 模板（版本化；措辞对齐 B06 t3 真模型问候输出的形态，保证行为差最小）。
_TEMPLATE_VERSION = "v1"

_GREETING_REPLY = "你好！我是 Sparkle，你的学习成长伙伴。\n\n今天有什么想聊的，或者需要我协助梳理的学习内容吗？"
_ACKNOWLEDGMENT_REPLY = "好的！想继续聊什么，或者需要我协助梳理的学习内容，直接说就行。"
_THANKS_REPLY = "不客气！有新的学习问题，或者想继续梳理的内容，随时找我。"
_FAREWELL_REPLY = "好的，下次见！有学习问题或想继续的话题，随时回来找我。"


@dataclass(frozen=True)
class DeterministicLaneDecision:
    """零模型快路判定（可观测、可审计）。"""

    kind: DeterministicLaneKind
    trigger: str  # 命中的封闭词表词（metric trigger 标签）
    reply: str
    template_version: str = _TEMPLATE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "trigger": self.trigger,
            "template_version": self.template_version,
            "lane": CHAT_LANE_DETERMINISTIC,
        }


def _reply_for(kind: DeterministicLaneKind, trigger: str) -> str:
    lowered = trigger.lower()
    if kind is DeterministicLaneKind.GREETING:
        return _GREETING_REPLY
    if kind is DeterministicLaneKind.FAREWELL:
        return _FAREWELL_REPLY
    # 确认类细分：致谢 vs 附和
    if any(token in lowered for token in ("谢谢", "感谢", "thanks", "thank", "thx", "3q", "多谢", "谢啦")):
        return _THANKS_REPLY
    return _ACKNOWLEDGMENT_REPLY


def _token_kind(token: str) -> DeterministicLaneKind:
    if token in _FAREWELL_TOKENS:
        return DeterministicLaneKind.FAREWELL
    if token in _GREETING_TOKENS:
        return DeterministicLaneKind.GREETING
    return DeterministicLaneKind.ACKNOWLEDGMENT


def _context_lane_blocked(context_data: dict[str, Any]) -> bool:
    """上下文守卫：任一 deliberate 事实在场 → 永不快路（与 capability_lane 同源）。"""
    chat_mode = str(context_data.get("chat_mode") or "standard").strip().lower()
    if chat_mode not in _FAST_CHAT_MODES:
        return True
    if bool(context_data.get("planned_tool_sequence")):
        return True
    if str(context_data.get("reasoning_mode") or "").strip().lower() == "deep":
        return True
    if bool(context_data.get("file_ids")) or bool(str(context_data.get("document_context") or "").strip()):
        return True
    if bool(context_data.get("selected_experts") or context_data.get("answer_experts")):
        return True
    if bool(str(context_data.get("agent_role") or "").strip()):
        return True
    retrieval = context_data.get("document_retrieval_decision") or context_data.get("retrieval_decision")
    if isinstance(retrieval, dict):
        retrieval_mode = str(retrieval.get("retrieval_mode") or "")
        if retrieval.get("should_retrieve") and retrieval_mode in _DOCUMENT_RETRIEVAL_MODES:
            return True
    return False


def _pending_proposal_in_history(context_data: dict[str, Any]) -> bool:
    """上一条助手消息以问句/提案收尾 → 确认类可能是应允，快路让位。"""
    conversation = context_data.get("conversation_context")
    messages: list[Any] = []
    if isinstance(conversation, dict) and isinstance(conversation.get("messages"), list):
        messages = list(conversation["messages"])
    for message in reversed(messages):
        role = str((message or {}).get("role") or "")
        if role != "assistant":
            continue
        content = str((message or {}).get("content") or "").strip()
        if not content:
            continue
        return any(marker in content for marker in _ASSISTANT_PROPOSAL_MARKERS)
    return False


def resolve_deterministic_lane(
    user_message: str,
    context_data: dict[str, Any] | None = None,
) -> DeterministicLaneDecision | None:
    """判定消息是否可零模型直出（纯规则，零 LLM / 零上游调用）。

    返回 None = 不可快路（必须走既有真模型慢路，行为不变）。
    """
    context = context_data if isinstance(context_data, dict) else {}
    text = str(user_message or "").strip()
    if not text or len(text) > _MAX_LANE_MESSAGE_CHARS:
        return None

    lowered = text.lower()
    # 文本防误伤（同源共享 capability_lane 常量）：工具动作/个人数据/深度词。
    if any(marker in lowered for marker in DEEP_ANALYSIS_TEXT_MARKERS):
        return None
    if not _light_reply_text_allowed(lowered):
        return None

    if _context_lane_blocked(context):
        return None

    # 词表命中（长词优先，避免「好」吃掉「你好」）。
    matched: str | None = None
    for token in sorted(
        (*_GREETING_TOKENS, *_ACKNOWLEDGMENT_TOKENS, *_FAREWELL_TOKENS),
        key=len,
        reverse=True,
    ):
        if token in lowered:
            matched = token
            break
    if matched is None:
        return None

    # 剥词校验：去掉全部命中词 + 标点/语气词后必须零实质字符。
    remainder = lowered
    for token in (*_GREETING_TOKENS, *_ACKNOWLEDGMENT_TOKENS, *_FAREWELL_TOKENS):
        remainder = remainder.replace(token, "")
    remainder = "".join(ch for ch in remainder if ch not in _FILLER_CHARS)
    if _SUBSTANTIVE_RE.search(remainder):
        return None

    # 确认类待提案守卫：「好的」可能是对助手提案的应允。
    kind = _token_kind(matched)
    if kind is DeterministicLaneKind.ACKNOWLEDGMENT and _pending_proposal_in_history(context):
        return None

    return DeterministicLaneDecision(kind=kind, trigger=matched, reply=_reply_for(kind, matched))


def record_deterministic_lane_decision(
    decision: DeterministicLaneDecision,
    *,
    context_data: dict[str, Any] | None = None,
) -> None:
    """快路执行点落遥测（结构化日志 + counter）并回写 context_data 供透传。"""
    try:
        CHAT_DETERMINISTIC_LANE_TOTAL.labels(kind=decision.kind.value, trigger=decision.trigger).inc()
    except Exception:  # pragma: no cover - 遥测失败不影响主链路
        logger.opt(exception=True).warning("deterministic lane metric recording failed")

    logger.info(
        "[DeterministicLane] lane={} kind={} trigger={} template_version={}",
        CHAT_LANE_DETERMINISTIC,
        decision.kind.value,
        decision.trigger,
        decision.template_version,
    )

    if isinstance(context_data, dict):
        context_data["deterministic_lane"] = decision.to_dict()
        context_data["chat_lane"] = CHAT_LANE_DETERMINISTIC
