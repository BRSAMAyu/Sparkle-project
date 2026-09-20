"""C-08 · hermetic 模拟模型 + 四臂上下文装配。

模拟层正是「LLM 作答决策」这一件事（对齐 memory_eval harness 的红线设计）：
确定性抽取式作答规则，零真实 LLM 调用。四臂只改变**注入的上下文**，不改
作答规则——utility 的组间差全部归因于 context 本身。

作答规则（对真实抽取行为的确定性近似）：

1. **共享注意力窗**：材料（rerank 分数降序）与记忆共同消耗
   ``max_seen_items`` 个槽位与 ``token_budget`` 预算——超窗材料/记忆对模型
   不可见（context bloat 的确定性效应面）；
2. **引用**：可见材料与 query 的 token 重叠（hanzi bigram + ascii 词，与
   C-04 同粒度）≥ ``CITE_THRESHOLD`` 才引用 ``[Sk]``；
3. **记忆使用**：可见记忆与 query 重叠 ≥ 阈值才织入回答；
4. **克制**：无可引材料时输出无引用的保守回答（adversarial 的正确行为）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.citation_markers import CITATION_GUIDE, annotate_citation_markers
from app.orchestration.context_funnel import make_source_ref

from .context_eval_schema import (
    ARM_FULL,
    ARM_NO_MEMORY,
    ARM_NO_OUTCOME,
    ARM_NO_RAG,
    MemoryItem,
    Material,
    OUTCOME_NONE,
    Scenario,
)

#: 引用/使用阈值（hanzi bigram 重叠粒度；与 C-04 support 阈同量级）。
CITE_THRESHOLD = 0.15

#: 共享注意力窗（少而对的确定性杠杆）。材料（近邻 user 消息）先占窗、
#: 记忆（系统提示）后入窗——挤占效应作用于记忆面，与生产渲染顺序一致。
MAX_SEEN_ITEMS = 4
TOKEN_BUDGET = 420

_ASCII_TOKEN_RE = re.compile(r"[a-z0-9]+")
_HANZI_RUN_RE = re.compile(r"[\u4e00-\u9fff]+")


def overlap_tokens(text: str) -> set[str]:
    """ascii 词 + hanzi 二元组（与 app.core.citation_markers._support_tokens 同粒度）。"""
    lowered = str(text or "").lower()
    tokens: set[str] = set(_ASCII_TOKEN_RE.findall(lowered))
    for run in _HANZI_RUN_RE.findall(lowered):
        if len(run) == 1:
            tokens.add(run)
            continue
        tokens.update(run[idx : idx + 2] for idx in range(len(run) - 1))
    return tokens


def query_overlap(query: str, content: str) -> float:
    """query token 覆盖率：|query∩content| / |query|（与 graph_rag 关键词重叠同式）。"""
    query_tokens = overlap_tokens(query)
    if not query_tokens:
        return 0.0
    return len(query_tokens & overlap_tokens(content)) / len(query_tokens)


def estimate_tokens(text: str) -> int:
    """确定性 token 近似（评测域内一致即可，不依赖 tiktoken 可用性）。"""
    return max(1, len(text) // 4) if text else 0


# ---------------------------------------------------------------------------
# 四臂装配
# ---------------------------------------------------------------------------


@dataclass
class AssembledContext:
    """单臂装配结果：注入块 + 漏斗观测 + source_ref（全部 metadata-only 可导出）。"""

    document_block: str
    memory_section: str
    markers: list[str]
    source_refs: list[dict]
    total_tokens: int
    seen_material_refs: list[str]
    seen_memory_refs: list[str]
    dropped_by_attention: list[tuple[str, str]] = field(default_factory=list)
    funnel_surfaces: dict = field(default_factory=dict)


def assemble(scenario: Scenario, arm: str) -> AssembledContext:
    """按评测臂装配上下文（arm 只裁剪注入面，不改排序/注意力/作答规则）。"""
    materials: tuple[Material, ...] = scenario.materials
    memories: tuple[MemoryItem, ...] = scenario.memories
    if arm == ARM_NO_MEMORY:
        memories = ()
    elif arm == ARM_NO_RAG:
        materials = ()
    elif arm == ARM_NO_OUTCOME:
        memories = tuple(memory for memory in memories if memory.outcome == OUTCOME_NONE)

    # rerank：分数降序（稳定排序，与生产 _rank_document_chunks 的语义对齐）。
    ranked = sorted(materials, key=lambda item: (-item.relevance_score, item.ref))

    # 共享注意力窗：记忆（系统提示，prompt 前段）先入窗，材料（近邻 user
    # 消息）按 rerank 分序随后——记忆体量挤占材料槽位是「context bloat 淹没
    # 检索材料」的真实失效形态；窗宽即「少而对」的确定性杠杆。
    seen_materials: list[Material] = []
    seen_memories: list[MemoryItem] = []
    dropped: list[tuple[str, str]] = []
    slots = MAX_SEEN_ITEMS
    used = 0
    for memory in memories:
        cost = estimate_tokens(memory.content)
        if slots <= 0 or used + cost > TOKEN_BUDGET:
            dropped.append((memory.ref, "attention_window"))
            continue
        seen_memories.append(memory)
        slots -= 1
        used += cost
    for material in ranked:
        cost = estimate_tokens(material.content)
        if slots <= 0 or used + cost > TOKEN_BUDGET:
            dropped.append((material.ref, "attention_window"))
            continue
        seen_materials.append(material)
        slots -= 1
        used += cost

    # 材料块：生产 format_filtered_study_materials_context 的稳定格式
    # （[k] 行首序号 + 引文行），再经 C-04 annotate 得 [S#] 标记。
    lines = ["[Study Materials — Referenced Documents]"]
    for index, material in enumerate(seen_materials, start=1):
        lines.extend(
            [
                "",
                f"[{index}] study-material-{material.ref}",
                f'"{material.content}"',
                f"(relevance: {material.relevance_score:.2f})",
            ]
        )
    raw_block = "\n".join(lines) if seen_materials else ""
    document_block, markers = annotate_citation_markers(raw_block)
    if document_block:
        document_block = f"{document_block}\n\n{CITATION_GUIDE}"

    memory_lines = ["## Cross-Session Memory"]
    for memory in seen_memories:
        memory_lines.append(f"- {memory.content}")
    memory_section = "\n".join(memory_lines) if seen_memories else ""

    source_refs = [
        make_source_ref(
            kind="document",
            ref_id=material.ref,
            content=material.content,
            extra={"relevance_score": material.relevance_score},
        )
        for material in seen_materials
    ] + [
        make_source_ref(
            kind="episodic",
            ref_id=memory.ref,
            content=memory.content,
            extra={"outcome": memory.outcome},
        )
        for memory in seen_memories
    ]

    total_tokens = estimate_tokens(document_block) + estimate_tokens(memory_section)
    return AssembledContext(
        document_block=document_block,
        memory_section=memory_section,
        markers=[entry for entry in markers],
        source_refs=source_refs,
        total_tokens=total_tokens,
        seen_material_refs=[material.ref for material in seen_materials],
        seen_memory_refs=[memory.ref for memory in seen_memories],
        dropped_by_attention=dropped,
    )


# ---------------------------------------------------------------------------
# 模拟模型（确定性抽取式作答）
# ---------------------------------------------------------------------------

_FALLBACK_ANSWER = "这部分我还需要确认一下材料，先不给你下结论。"


def mock_answer(scenario: Scenario, assembled: AssembledContext) -> tuple[str, list[str], list[str]]:
    """返回 (answer, cited_refs, used_memory_refs)——确定性，无随机源。"""
    clauses: list[str] = []
    cited_refs: list[str] = []
    used_memory_refs: list[str] = []
    query_tokens = overlap_tokens(scenario.query)

    for material in scenario.materials:
        if material.ref not in assembled.seen_material_refs:
            continue
        if query_overlap(scenario.query, material.content) < CITE_THRESHOLD:
            continue
        marker_index = assembled.seen_material_refs.index(material.ref)
        if marker_index >= len(assembled.markers):
            continue
        marker = assembled.markers[marker_index]["marker"]
        clauses.append(f"关于重点：{material.content.split('。')[0]}[{marker}]")
        cited_refs.append(material.ref)

    for memory in scenario.memories:
        if memory.ref not in assembled.seen_memory_refs:
            continue
        if query_overlap(scenario.query, memory.content) < CITE_THRESHOLD:
            continue
        clauses.append(f"结合你的学习记录：{memory.content[:24]}")
        used_memory_refs.append(memory.ref)

    if not clauses:
        return _FALLBACK_ANSWER, cited_refs, used_memory_refs
    return " ".join(clauses), cited_refs, used_memory_refs
