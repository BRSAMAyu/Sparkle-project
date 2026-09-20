"""C-04 · RAG citation marker 层（确定性解析，零 LLM 参与）。

RAG_KNOWLEDGE.md：V3 继续解决「材料已注入但模型间歇不引用」的真实效果，
优化真正使用（use）而非存在（presence）。本模块三层职责，全部纯函数、
零 I/O（hermetic，可独立单测）：

1. **annotate_citation_markers** —— 把材料块（graph_rag.format_filtered_
   study_materials_context / [Knowledge Results] 的稳定行首 ``[\\d+]`` 序号）
   重写为可引用的 ``[S#]`` 来源标记，并捕获每个标记对应的引文 snippet。
   不重建格式化层（权威真源仍在 graph_rag），只做 prompt 注入前的
   确定性标注。
2. **parse_cited_markers** —— 从答案文本确定性解析被引用的标记
   （``[S1]`` / ``[S1][S3]`` / ``[S1, S3]`` / ``【S1】``；模型退化成纯
   数字 ``[1]`` 的形态也容忍）。
3. **build_citation_outcome** —— retrieved vs cited vs answer-supported
   的确定性记录（answer-supported 用 hanzi bigram / ascii token 重叠规则
   判定，不花模型次数）。

红线对齐（C-04 acceptance：不能通过强迫每个回答引用无关材料提高指标）：

- 空材料（或空检索哨兵块）时 retrieved=0，答案出现的任何 ``[S#]`` 都记入
  ``unknown_cited``（幻觉引用信号），faithfulness 判 False；
- 答案标了 ``[S#]`` 但与该引文 snippet 的 token 重叠低于阈值 →
  ``answer_supported`` 不含该标记，faithfulness 判 False。

哨兵检测说明：空检索哨兵的权威常量是
``app.orchestration.graph_rag.NO_RELEVANT_STUDY_MATERIALS_SENTINEL``；
本模块只保存用于**检测**的子串（不重建内容真源），parity 由
``tests/unit/test_citation_markers.py::test_sentinel_marker_parity`` 钉死。
"""

from __future__ import annotations

import re
from typing import Any

#: 注入材料时的引用引导（「用到才引」）。与「必须优先引用」置顶声明互补：
#: 声明解决注意力（材料在附近、优先用），引导解决格式与克制（怎么标、
#: 没用到不标、不硬引无关材料）。
CITATION_GUIDE = (
    "引用格式：回答内容确实来自某条材料时，在对应句子末尾标注其来源编号"
    "（如 ……[S1]）；材料未覆盖的部分用你自己的知识回答，不要标注编号，"
    "也不要硬引材料里没有的内容。"
)

#: 空检索哨兵检测子串（权威常量见模块 docstring；parity 由测试钉住）。
NO_MATERIAL_SENTINEL_MARKERS: tuple[str, ...] = ("No relevant study materials",)

#: 材料块行首序号（format_filtered_study_materials_context 与
#: [Knowledge Results] 两种稳定格式的公共形态）。``S`` 前缀可选——本函数
#: 对已标注块（[S1]）必须幂等：standard_workflow 的 outcome 接线拿到的
#: document_block 是 annotate 之后的块，提取与改写共用同一识别面。
_ORDINAL_MARKER_RE = re.compile(r"^\[S?(\d{1,2})\]\s", re.MULTILINE)

#: 答案侧引用解析：先取方括号组，再在组内找 S 前缀编号；无 S 前缀的纯
#: 数字组（模型退化形态）单独匹配，排除含字母/小数的干扰组。
_BRACKET_GROUP_RE = re.compile(r"\[([^\[\]\n]{1,48})\]")
_S_TOKEN_RE = re.compile(r"S(\d{1,2})")
_PLAIN_DIGIT_GROUP_RE = re.compile(r"^\d{1,2}(?:\s*[,，、]\s*\d{1,2})*$")
_DIGIT_TOKEN_RE = re.compile(r"\d{1,2}")

#: answer-supported 判定阈值：被标引用的 snippet 与答案的 token 重叠比例
#: （|snippet∩answer| / |snippet|）低于该值视为「标了但答案没用」（刷指标
#: 守卫面）。hanzi bigram 粒度下，真引用实测 0.25+，幻觉引用 <0.12。
ANSWER_SUPPORT_OVERLAP_THRESHOLD = 0.18

#: 参与重叠判定的 snippet 上限（材料块引文截断展示面约 520 字符）。
_SNIPPET_CAPTURE_LIMIT = 520

_ASCII_TOKEN_RE = re.compile(r"[a-z0-9]+")
_HANZI_RUN_RE = re.compile(r"[\u4e00-\u9fff]+")


def is_no_material_sentinel(document_block: str) -> bool:
    """该材料块是否为「无相关材料」哨兵（不得套「必须引用」类声明）。"""
    text = str(document_block or "")
    return any(marker in text for marker in NO_MATERIAL_SENTINEL_MARKERS)


def _support_tokens(text: str) -> set[str]:
    """重叠判定的 token 集：ascii 词 + hanzi 二元组（单字噪声远高于二元组）。"""
    lowered = str(text or "").lower()
    tokens: set[str] = set(_ASCII_TOKEN_RE.findall(lowered))
    for run in _HANZI_RUN_RE.findall(lowered):
        if len(run) == 1:
            tokens.add(run)
            continue
        tokens.update(run[idx : idx + 2] for idx in range(len(run) - 1))
    return tokens


def extract_material_markers(document_block: str) -> list[dict[str, Any]]:
    """解析材料块中的序号标记与对应引文 snippet（不改写文本）。

    返回 ``[{"marker": "S1", "ordinal": 1, "snippet": "..."}]``；marker 按
    块内出现顺序编号（S1、S2……），ordinal 保留块内原始序号供追溯。
    """
    text = str(document_block or "")
    lines = text.splitlines()
    markers: list[dict[str, Any]] = []
    for line_no, line in enumerate(lines):
        match = _ORDINAL_MARKER_RE.match(line)
        if not match:
            continue
        snippet = ""
        for follow in lines[line_no + 1 :]:
            stripped = follow.strip()
            if not stripped:
                continue
            if stripped.startswith('"') or stripped.startswith("“"):
                snippet = stripped.strip('"“”').strip()
            else:
                snippet = stripped
            break
        position = len(markers) + 1
        markers.append(
            {
                "marker": f"S{position}",
                "ordinal": int(match.group(1)),
                "snippet": snippet[:_SNIPPET_CAPTURE_LIMIT],
            }
        )
    return markers


def annotate_citation_markers(document_block: str) -> tuple[str, list[dict[str, Any]]]:
    """把材料块的行首 ``[N]`` 序号改写为 ``[S1]`` 系列来源标记。

    返回 ``(改写后的块, markers)``。块内无序号（multi-hop synthesis、
    "## Retrieved Documents" bullet 等格式）时原样返回、markers 为空
    （此时不附加引用引导，避免无的放矢）。
    """
    text = str(document_block or "")
    markers = extract_material_markers(text)
    if not markers:
        return text, []

    by_ordinal = {entry["ordinal"]: entry["marker"] for entry in markers}

    def _rewrite(match: re.Match[str]) -> str:
        marker = by_ordinal.get(int(match.group(1)))
        return f"[{marker}] " if marker else match.group(0)

    annotated = _ORDINAL_MARKER_RE.sub(_rewrite, text)
    return annotated, markers


def parse_cited_markers(answer_text: str) -> list[str]:
    """确定性解析答案中被引用的来源标记（去重、按首次出现排序）。

    识别 ``[S1]``、``[S1][S3]``、``[S1, S3]``、``【S1】``；纯数字组
    ``[1]`` / ``[1, 3]`` 作为模型退化形态容忍（映射为 S1/S3）。
    """
    text = str(answer_text or "")
    text = text.replace("【", "[").replace("】", "]")
    cited: list[str] = []
    for group in _BRACKET_GROUP_RE.findall(text):
        s_tokens = [f"S{token}" for token in _S_TOKEN_RE.findall(group)]
        if s_tokens:
            for token in s_tokens:
                if token not in cited:
                    cited.append(token)
            continue
        if _PLAIN_DIGIT_GROUP_RE.match(group.strip()):
            for token in _DIGIT_TOKEN_RE.findall(group):
                marker = f"S{token}"
                if marker not in cited:
                    cited.append(marker)
    return cited


def build_citation_outcome(answer_text: str, document_block: str) -> dict[str, Any]:
    """retrieved vs cited vs answer-supported 的确定性结果记录。

    - ``retrieved``：注入材料块的标记集（过滤后、进 prompt 的材料）；
    - ``cited``：答案引用且**确实注入过**的标记（未知标记进 unknown_cited）；
    - ``answer_supported``：引用标记中 snippet 与答案 token 重叠达阈值者；
    - ``faithfulness_ok``：没有幻觉引用，且每个 cited 标记都 answer-supported
      （未引用任何材料时为 True——「没引」不是不忠实，「引了没用」才是）。
    """
    markers = extract_material_markers(document_block)
    known = {entry["marker"]: entry for entry in markers}
    parsed = parse_cited_markers(answer_text)
    cited_all = parsed
    cited = [marker for marker in parsed if marker in known]
    unknown_cited = [marker for marker in parsed if marker not in known]

    answer_tokens = _support_tokens(answer_text)
    answer_supported: list[str] = []
    support_ratio: dict[str, float] = {}
    for marker in cited_all:
        entry = known.get(marker)
        if entry is None:
            continue
        snippet_tokens = _support_tokens(entry["snippet"])
        if not snippet_tokens:
            ratio = 0.0
        else:
            ratio = len(snippet_tokens & answer_tokens) / len(snippet_tokens)
        support_ratio[marker] = round(ratio, 3)
        if ratio >= ANSWER_SUPPORT_OVERLAP_THRESHOLD:
            answer_supported.append(marker)

    faithfulness_ok = not unknown_cited and all(marker in answer_supported for marker in cited_all)
    return {
        "version": "c04-citation.v1",
        "retrieved": len(markers),
        "retrieved_markers": [entry["marker"] for entry in markers],
        "cited": cited,
        "cited_count": len(cited),
        "unknown_cited": unknown_cited,
        "answer_supported": answer_supported,
        "answer_supported_count": len(answer_supported),
        "support_ratio": support_ratio,
        "support_threshold": ANSWER_SUPPORT_OVERLAP_THRESHOLD,
        "faithfulness_ok": faithfulness_ok,
    }
