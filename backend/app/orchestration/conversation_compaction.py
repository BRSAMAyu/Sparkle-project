"""C-06 · 长会话确定性 compaction（零 LLM 默认路径，保序保关键类）。

CONTEXT_COMPILER_V3.md §4：历史对话只保留必要摘要/最近消息，**优先保存
决策必要的 state 与明确纠正**。基线证据（REPORT B1/B2）：

- ContextPruner tier-2（10<n≤30）：关键词表未命中的纠正消息被硬截到
  150 字符——纠错的操作性尾部（"请以这次说的为准…"）直接丢失；
- tier-3（n>30，生产长会话路径）：只保 anchor 关键词命中 + 最近 4 条，
  其余全靠 ≤100 字 LLM 摘要。实测 34 轮含 3 处纠正的会话 **丢 2/3 纠正**
  （关键词没命中就静默消失）；LLM 不可用时 RB-07 退回 tier-2 继续丢。

本模块把"哪些消息绝不能丢"从**人工关键词表**升级为**确定性显著度分类**：

- ``correction``（用户纠正）：不对/纠正/作废/以这次为准/我说的是… 等边界
  显式模式，含"之前X其实Y"对比结构；
- ``decision``（关键决策）：就这么定/决定用/选定/确认方案…
- ``unresolved``（未决问题）：还没解决/待确认/存疑/下次继续…
- ``action_result``（动作结果）：携带 tool_calls/tool_results 的消息（执行
  引擎/X 链的锚）；
- ``goal_state``（目标状态）：目标是/核心目标/冲刺X分/提到X分/考上…
- ``ordinary``：其余。

``compact_history`` 三条铁律：

1. **保序**：输出消息保持原会话相对顺序（stable by index）；
2. **关键类不静默丢**：correction/decision/unresolved/action_result/
   goal_state 永远不出现在"静默消失"路径上——预算实在装不下时按 最老
   优先 显式降级并记入 ``dropped_key``（可观测，绝不无声）；
3. **确定性**：同一输入永远同一输出；零 LLM、零 I/O（tiktoken 可选，
   与 context_pack.estimate_tokens 同语义的 char/4 兜底）。

普通消息被省略时留下有界占位（``[已压缩 xN]``），不伪造内容、不静默。
LLM 摘要保留为 ContextPruner 的可选档（``ENABLE_LLM_SESSION_SUMMARY``），
默认路径零 LLM（成本与延迟纪律，红线：真模型调用 0 次）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

try:  # pragma: no cover - optional runtime dependency（与 context_pack 同策略）
    import tiktoken
except ImportError:  # pragma: no cover
    tiktoken = None

#: 消息显著度类别（输出 metadata 用，确定性字符串）。
SALIENCE_CORRECTION = "correction"
SALIENCE_DECISION = "decision"
SALIENCE_UNRESOLVED = "unresolved"
SALIENCE_ACTION_RESULT = "action_result"
SALIENCE_GOAL_STATE = "goal_state"
SALIENCE_ORDINARY = "ordinary"

#: 参与预算竞争时不可静默丢弃的类别集合。
KEY_SALIENCE: frozenset[str] = frozenset(
    {SALIENCE_CORRECTION, SALIENCE_DECISION, SALIENCE_UNRESOLVED, SALIENCE_ACTION_RESULT, SALIENCE_GOAL_STATE}
)

# ---------------------------------------------------------------------------
# 确定性分类器（模式匹配，零 LLM）。模式只服务 compaction 的裁剪决策，
# 不属于 event_registry 词表（39 词表冻结红线不涉及本模块）。
# ---------------------------------------------------------------------------

_CORRECTION_RE = re.compile(
    r"(不对[，,。；]|不是的|你说错了|我说的不是|说错了|录错了|填错了|算错了|记错了"
    r"|纠正[一下：:]|更正[一下：:]|搞错了"
    r"|全部作废|作废[，,]|之前(说|填|报|记|写|算)的.{0,12}(不对|有误|错了|作废|不算)"
    r"|以(这次|本次|现在)为准|别再(用|按|提)|不要再(用|按|提)"
    r"|(其实|实际上)我(是|住在|用的|已经))"
)

_DECISION_RE = re.compile(
    r"((就|就这)么定[了吧]|决定(用|改用|选|采用|放弃)|选定[了了]?|拍板"
    r"|(确认|敲定)(方案|计划|安排|版本)|同意这(个|套)(方案|安排)|最终(决定|选择))"
)

_UNRESOLVED_RE = re.compile(
    r"(还没(有)?(解决|弄清|搞懂|确定|答复)|(暂时|仍然)存疑|待确认|待定|待跟进"
    r"|下次(继续|再(讨论|确认|看))|悬而未决|没有结论|先(记|挂)着)"
)

_GOAL_STATE_RE = re.compile(
    r"((核心|真正(的)?)?目标(是|就是)|我的目标|目标分|冲刺\d{1,3}分|(提到|提到手|涨)\s*\d{1,3}\s*分"
    r"|(考上|拿下|通过)\s*\S{0,12}(大学|研究生|证|级)|月底前|考前(一定|必须))"
)

_UTF8_HANZI_RE = re.compile(r"[\u4e00-\u9fff]")


def _estimate_tokens(text: str) -> int:
    """与 app.core.context_pack.estimate_tokens 同语义的本地实现。

    compaction 模块刻意不 import context_pack（orchestration → core 反向
    依赖会造成 orchestration 包导入环），tiktoken 可选、char//4 兜底一致。
    """
    if not text:
        return 0
    encoding = _get_token_encoding()
    if encoding:
        try:
            return len(encoding.encode(text))
        except Exception:
            pass
    # 兜底：与 context_pack 相同的 len//4，但按 CJK 密度修正（全汉字串
    # char//4 严重低估，1.6 字/token 更接近 cl100k 实测）。
    hanzi = len(_UTF8_HANZI_RE.findall(text))
    other = len(text) - hanzi
    return max(1, int(hanzi / 1.6) + other // 4)


_encoding_cache: list[Any] = []


def _get_token_encoding():
    if not _encoding_cache:
        if tiktoken is None:
            _encoding_cache.append(None)
        else:
            try:
                _encoding_cache.append(tiktoken.get_encoding("cl100k_base"))
            except Exception:
                _encoding_cache.append(None)
    return _encoding_cache[0]


def classify_message(message: dict[str, Any]) -> str:
    """单条消息的确定性显著度分类。结构信号优先于内容模式。"""
    if not isinstance(message, dict):
        return SALIENCE_ORDINARY
    if message.get("tool_calls") or message.get("tool_results") or message.get("tool_call_id"):
        return SALIENCE_ACTION_RESULT
    if str(message.get("role") or "") == "system":
        return SALIENCE_ORDINARY
    content = str(message.get("content") or "").strip()
    if not content:
        return SALIENCE_ORDINARY
    if message.get("correction") or message.get("is_correction"):
        return SALIENCE_CORRECTION
    if _CORRECTION_RE.search(content):
        return SALIENCE_CORRECTION
    if _DECISION_RE.search(content):
        return SALIENCE_DECISION
    if _GOAL_STATE_RE.search(content):
        return SALIENCE_GOAL_STATE
    if _UNRESOLVED_RE.search(content):
        return SALIENCE_UNRESOLVED
    return SALIENCE_ORDINARY


def classify_history(messages: list[dict[str, Any]]) -> list[str]:
    """整段历史的分类快照（与输入等长、保序）——测试与观测用。"""
    return [classify_message(message) for message in messages]


# ---------------------------------------------------------------------------
# 压缩主体
# ---------------------------------------------------------------------------

#: 普通消息在压缩区的默认保留窗口（最近 N 条原样保留）。
DEFAULT_RECENT_WINDOW = 6
#: 关键类单条 content 的默认 token 上限（超限截断但保头部 + 显式标记）。
DEFAULT_KEY_MESSAGE_CAP_TOKENS = 220
#: 普通消息压缩区省略占位的模板。
_PLACEHOLDER_PREFIX = "[已压缩"
_TRUNCATED_SUFFIX = "…（超限截断）"


@dataclass
class CompactionResult:
    """compact_history 的确定性产物（同时兼容 ContextPruner 返回形状）。"""

    messages: list[dict[str, Any]]
    summary: str | None
    original_count: int
    pruned_count: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_pruner_payload(self) -> dict[str, Any]:
        return {
            "messages": self.messages,
            "summary": self.summary,
            "original_count": self.original_count,
            "pruned_count": self.pruned_count,
            "summary_used": bool(self.summary),
            "compaction_used": True,
            "compaction": self.metadata,
        }


def _truncate_content(content: str, cap_tokens: int) -> str:
    """确定性头部截断（无 tiktoken 时按估算收缩，永不超 cap）。"""
    if cap_tokens <= 0 or _estimate_tokens(content) <= cap_tokens:
        return content
    low, high = 1, len(content)
    # 二分找满足预算的最长前缀（确定性，纯字符串操作）。
    best = content[:1]
    while low <= high:
        mid = (low + high) // 2
        if _estimate_tokens(content[:mid] + _TRUNCATED_SUFFIX) <= cap_tokens:
            best = content[:mid] + _TRUNCATED_SUFFIX
            low = mid + 1
        else:
            high = mid - 1
    return best


def _digest(message: dict[str, Any]) -> str:
    content = str(message.get("content") or "").strip().replace("\n", " ")
    role = str(message.get("role") or "msg")
    return f"{role}:{content[:24]}"


def compact_history(
    messages: list[dict[str, Any]],
    *,
    recent_window: int = DEFAULT_RECENT_WINDOW,
    token_budget: int | None = None,
    key_message_cap_tokens: int = DEFAULT_KEY_MESSAGE_CAP_TOKENS,
) -> CompactionResult:
    """长历史 → 有界、保序、关键类不静默丢的压缩历史。

    步骤（全部确定性）：
      1. 分类全量消息；
      2. 最近 ``recent_window`` 条原样保留；
      3. 压缩区：关键类保留（content 超 cap 时头部截断 + 标记），普通类
         合并为有界占位（记录条数与首尾 digest，不伪造内容）；
      4. 若给了 ``token_budget`` 且仍超：先收缩占位（合并/丢弃，占位是
         可牺牲的），再按 最老优先 显式丢弃关键类（记入
         ``metadata["dropped_key"]``）——绝不无声消失。
    """
    if not isinstance(messages, list) or not messages:
        return CompactionResult(
            messages=list(messages or []),
            summary=None,
            original_count=len(messages or []),
            pruned_count=len(messages or []),
            metadata={"applied": False, "reason": "empty"},
        )

    salience = classify_history(messages)
    original_count = len(messages)
    window = max(0, int(recent_window))
    budget = int(token_budget) if token_budget is not None and int(token_budget) > 0 else None

    def _serialize_cost(msg: dict[str, Any]) -> int:
        return _estimate_tokens(f"{msg.get('role')}: {msg.get('content')}")

    # ---- 分区：压缩区（earlier） vs 保留区（recent window） ----
    cut = max(0, original_count - window)
    earlier = list(range(cut))
    recent = list(range(cut, original_count))

    kept: list[tuple[int, dict[str, Any]]] = []
    placeholders: list[tuple[int, dict[str, Any]]] = []  # (position_key, placeholder)
    compressed_count = 0
    truncated_key = 0

    run: list[int] = []

    def _flush_run() -> None:
        nonlocal compressed_count
        if not run:
            return
        first, last = run[0], run[-1]
        placeholder = {
            "role": "system",
            "content": (
                f"{_PLACEHOLDER_PREFIX} x{len(run)}] 省略普通历史消息 "
                f"{len(run)} 条（{_digest(messages[first])} … {_digest(messages[last])}）"
            ),
            "compacted_placeholder": True,
            "omitted_count": len(run),
        }
        placeholders.append((first, placeholder))
        compressed_count += len(run)
        run.clear()

    for idx in earlier:
        if salience[idx] == SALIENCE_ORDINARY:
            run.append(idx)
            continue
        _flush_run()
        content = str(messages[idx].get("content") or "")
        kept_content = content
        if key_message_cap_tokens > 0 and _estimate_tokens(content) > key_message_cap_tokens:
            kept_content = _truncate_content(content, key_message_cap_tokens)
            truncated_key += 1
        entry = dict(messages[idx])
        entry["content"] = kept_content
        if kept_content != content:
            entry["compacted_truncated"] = True
        entry["salience"] = salience[idx]
        kept.append((idx, entry))
    _flush_run()

    # ---- 组装（保序）：占位与关键消息按原 index 交织 ----
    merged = sorted(kept + placeholders, key=lambda pair: pair[0])
    final_pairs: list[tuple[int, dict[str, Any]]] = list(merged)
    final_pairs.extend((idx, dict(messages[idx])) for idx in recent)
    final_pairs.sort(key=lambda pair: pair[0])
    final_messages: list[dict[str, Any]] = [msg for _, msg in final_pairs]

    total = sum(_serialize_cost(msg) for _, msg in final_pairs)

    dropped_key: list[dict[str, Any]] = []

    if budget is not None and total > budget:
        # 第一优先牺牲：占位（可再压缩为单行摘要）。
        retained_pairs: list[tuple[int, dict[str, Any]]] = []
        placeholder_run: list[dict[str, Any]] = []
        for idx, msg in final_pairs:
            if msg.get("compacted_placeholder"):
                placeholder_run.append(msg)
                continue
            retained_pairs.append((idx, msg))
        if placeholder_run:
            folded = {
                "role": "system",
                "content": f"{_PLACEHOLDER_PREFIX} x{sum(p.get('omitted_count', 1) for p in placeholder_run)}]",
                "compacted_placeholder": True,
                "omitted_count": sum(p.get("omitted_count", 1) for p in placeholder_run),
            }
            retained_pairs.append((-1, folded))
            total = sum(_serialize_cost(msg) for _, msg in retained_pairs)

        # 仍超 → 最老优先显式丢弃关键类（保留区 recent 消息绝不丢）。
        if total > budget:
            for idx, msg in sorted(retained_pairs, key=lambda pair: pair[0]):
                if total <= budget:
                    break
                if idx >= cut:
                    continue  # recent window 不可丢
                cost = _serialize_cost(msg)
                dropped_key.append(
                    {
                        "index": idx,
                        "salience": msg.get("salience") or SALIENCE_ORDINARY,
                        "digest": _digest(msg),
                        "tokens": cost,
                    }
                )
                total -= cost
                retained_pairs = [pair for pair in retained_pairs if pair[0] != idx]

        final_pairs = sorted(retained_pairs, key=lambda pair: pair[0])
        final_messages = [msg for _, msg in final_pairs]

    key_kept = [
        {"index": idx, "salience": msg.get("salience") or "recent"}
        for idx, msg in final_pairs
        if (msg.get("salience") in KEY_SALIENCE)
    ]
    summary = None
    if compressed_count or truncated_key:
        parts = [f"压缩 {compressed_count} 条普通消息"]
        if truncated_key:
            parts.append(f"截断 {truncated_key} 条超长关键消息")
        if dropped_key:
            parts.append(f"显式丢弃 {len(dropped_key)} 条最老关键消息（见 dropped_key）")
        summary = "；".join(parts) + "。"

    metadata = {
        "applied": True,
        "engine": "deterministic_c06",
        "recent_window": window,
        "token_budget": budget,
        "compressed_ordinary": compressed_count,
        "truncated_key": truncated_key,
        "key_preserved": key_kept,
        "dropped_key": dropped_key,
        "tokens_after": total,
    }
    return CompactionResult(
        messages=final_messages,
        summary=summary,
        original_count=original_count,
        pruned_count=len(final_messages),
        metadata=metadata,
    )
