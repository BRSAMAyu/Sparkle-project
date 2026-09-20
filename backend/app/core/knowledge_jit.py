"""C-06 · 大型 knowledge 的 JIT 注入（references + top chunks，零 LLM）。

CONTEXT_COMPILER_V3.md §5 JIT retrieval：对大型材料只传 references +
高相关 chunk；Agent 可按需读取更多，而非 upfront 全载入。基线：galaxy
knowledge 与文档切片从不区分大小——只要检索命中就整段进 prompt
（大知识源一次注入数千 token，多数轮次只用到前几条）。

本模块三件事，全部纯函数、零 I/O：

1. ``build_jit_knowledge`` —— 知识文本超 ``full_load_max_tokens`` 时：
   保留 top chunks（按原文顺序 = 检索排名，检索层已排序）至
   ``keep_top_tokens``，其余降级为有界 references 列表（每条保留可追溯
   的身份行）+ JIT fetch 提示（指向既有工具面
   ``app.tools.material_retrieval_tools.RetrieveUserMaterialTool``，复用
   不重建）。小知识源原样透传（``applied=False``）——零回归。
2. ``build_omitted_chunk_references`` —— 文档切片路径的 omitted 结果
   （format_document_chunks_for_prompt 预算内放不下的低排名块）的
   references 行构造。行首用 ``·``，绝不以 ``[数字]`` 开头——保护 C-04
   引用标记的序号识别面（annotate_citation_markers 只认行首 ``[N] ``）。
3. 与 C-07 的边界：JIT 是注入形态变换，发生在 cache 键解析**之后**的
   prompt 组装面，不接触 context_cache_key 的任何版本字段。

降级内容不伪造：references 只搬运原文本的身份行（截断到有界长度），
不生成新的事实陈述。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.orchestration.conversation_compaction import _estimate_tokens

#: Agent JIT fetch 提示（确定性文案；指向既有 retrieve_user_material 工具面）。
JIT_FETCH_TOOL_HINT = (
    "（以上仅注入最高相关摘录；其余相关材料已列为 References，"
    "需要更多原文时可调用 retrieve_user_material 工具按需检索，勿凭空补全。）"
)

#: references 段标题（行首不是 [数字]，与 C-04 标记识别面无冲突）。
REFERENCES_HEADER = "References (未全文注入，可按需 JIT 检索):"

#: 身份行默认上限（字符）；references 是索引不是正文，必须有界。
_DEFAULT_REFERENCE_LINE_MAX_CHARS = 120


@dataclass
class JitKnowledgeResult:
    text: str
    applied: bool
    total_tokens: int = 0
    kept_tokens: int = 0
    reference_count: int = 0
    omitted_lines: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "applied": self.applied,
            "total_tokens": self.total_tokens,
            "kept_tokens": self.kept_tokens,
            "reference_count": self.reference_count,
            "omitted_lines": self.omitted_lines,
        }


def _split_knowledge_units(text: str) -> list[str]:
    """把知识文本切成注入单元：优先段落（\\n\\n），退化为行（\\n）。

    galaxy knowledge（KnowledgeService.retrieve_context）是行格式，
    graph_rag/文档块是段落格式；两种都稳定可切。
    """
    normalized = str(text or "").strip()
    if not normalized:
        return []
    if "\n\n" in normalized:
        units = [unit.strip() for unit in normalized.split("\n\n")]
    else:
        units = [line.strip() for line in normalized.split("\n")]
    return [unit for unit in units if unit]


def _reference_line(unit: str, max_chars: int = _DEFAULT_REFERENCE_LINE_MAX_CHARS) -> str:
    """身份行：只取**可追溯的索引头**，不搬运正文。

    优先提取行首方括号身份（``- [知识点3]`` / ``- [file.pdf | p12 #4]``），
    附Status 类元标记；无括号形态退化为行首 48 字符。references 是索引
    不是正文——行越短，同一 reserve 预算能装下的可追溯源越多。
    """
    text = str(unit or "").strip()
    if not text:
        return ""
    first_line = text.splitlines()[0]
    bracket = re.match(r"^\s*[-·*]?\s*(\[[^\]\n]{1,80}\])", first_line)
    if bracket:
        identity = bracket.group(1)
        status = re.search(r"\(Status:\s*[^)]*\)", first_line)
        if status:
            identity = f"{identity} {status.group(0)}"
        else:
            relevance = re.search(r"\(relevance:\s*[^)]*\)", first_line)
            if relevance:
                identity = f"{identity} {relevance.group(0)}"
    else:
        identity = " ".join(first_line.split())[:48]
    if len(identity) > max_chars:
        identity = identity[: max_chars - 1].rstrip() + "…"
    return identity


def build_jit_knowledge(
    text: str,
    *,
    full_load_max_tokens: int,
    keep_top_tokens: int,
    max_references: int = 8,
) -> JitKnowledgeResult:
    """大型 knowledge → top chunks（预算内）+ references + fetch 提示。

    小知识源（<= full_load_max_tokens）原样透传；畸形参数同样透传
    （JIT 是优化不是正确性依赖，fail-open 到现状）。
    """
    raw = str(text or "").strip()
    if not raw:
        return JitKnowledgeResult(text="", applied=False)
    if full_load_max_tokens <= 0 or keep_top_tokens <= 0:
        return JitKnowledgeResult(text=raw, applied=False, total_tokens=_estimate_tokens(raw))

    total_tokens = _estimate_tokens(raw)
    if total_tokens <= full_load_max_tokens:
        return JitKnowledgeResult(
            text=raw,
            applied=False,
            total_tokens=total_tokens,
            kept_tokens=total_tokens,
        )

    units = _split_knowledge_units(raw)
    kept: list[str] = []
    used = 0
    omitted: list[str] = []
    for unit in units:
        unit_tokens = _estimate_tokens(unit)
        if len(kept) > 0 and used + unit_tokens > keep_top_tokens:
            omitted.append(unit)
            continue
        if len(kept) == 0 and unit_tokens > keep_top_tokens:
            # 首单元超预算：整单元保序降级为 reference（不截断正文语义，
            # 由 references 面兜底），保持「只注入高信号」的纪律。
            omitted.append(unit)
            continue
        kept.append(unit)
        used += unit_tokens

    reference_lines = [_reference_line(unit) for unit in omitted[: max(0, int(max_references))]]
    extra = len(omitted) - len(reference_lines)
    if extra > 0:
        reference_lines.append(f"…其余 {extra} 条未列出")

    parts: list[str] = []
    parts.extend(kept)
    if reference_lines:
        parts.append(REFERENCES_HEADER)
        parts.extend(f"· {line}" for line in reference_lines)
        parts.append(JIT_FETCH_TOOL_HINT)

    result_text = "\n".join(parts).strip()
    return JitKnowledgeResult(
        text=result_text,
        applied=True,
        total_tokens=total_tokens,
        kept_tokens=used,
        reference_count=len([line for line in reference_lines if not line.startswith("…")]),
        omitted_lines=len(omitted),
        metadata={"engine": "knowledge_jit_c06"},
    )


def build_omitted_chunk_references(
    omitted_labels: list[str],
    *,
    max_references: int = 8,
    include_tool_hint: bool = True,
) -> str:
    """预算内放不下的文档切片 → references 块（无块时返回空串）。

    ``omitted_labels`` 是 format_document_chunks_for_prompt 已有的排名
    label（file | section | p页 #chunk，可追溯）。行首 ``·``——不是
    ``[数字]``，annotate_citation_markers 的序号识别面不受污染（C-04）。
    """
    labels = [str(label or "").strip() for label in omitted_labels or []]
    labels = [label for label in labels if label]
    if not labels:
        return ""
    shown = labels[: max(1, int(max_references))]
    extra = len(labels) - len(shown)
    lines = [REFERENCES_HEADER]
    lines.extend(f"· {label}" for label in shown)
    if extra > 0:
        lines.append(f"· …其余 {extra} 个切片未列出")
    if include_tool_hint:
        lines.append(JIT_FETCH_TOOL_HINT)
    return "\n".join(lines)
