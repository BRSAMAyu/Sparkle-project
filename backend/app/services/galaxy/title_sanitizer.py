"""用户可见命名清洗：剥离评测 harness 拼进任务标题/计划科目的内部唯一性 token。

F-2（v3-output/WT324-SIMEVIDENCE/REPORT.md §四）：northstar_eval feature_tour
S7 攒光子阶段以「TOUR 专题{d}-{run}: 真题演练与错因回看」造任务（run =
{run_id}-{冲刺序}-{uuid6}，run_id=uuid4 hex8——subject 全局唯一、重跑安全的
评测用途 token）。任务完成走 DF-5 → ``GalaxyService.ensure_task_node`` 时，
内部标识被原样拷进知识节点 name/description/keywords，星图详情页大标题直接
呈现「TOUR 专题7-d91d5df0-10-5dc70d: 真题演练与错因回看」。

WT334 补充（plan 科目链路）：同一阶段以 ``f"TOUR科目-{run}"`` 填计划 subject
（subject 参与 ``uq_plans_user_sprint_goal_active`` 唯一键，token 是评测合法
去重手段，不从源头删除）。plan 详情 ``subject`` 字段、day_highlights 推荐文案、
任务 why_now、Aurora 每日简报等展示面原样透出 token——由
:func:`clean_display_subject` / :func:`strip_internal_tokens` 的科目形态剥离
兜底（读取侧，只清展示面，不改库）。形态与任务标题不同：TAG 直接贴
「科目/Subject」（无空白），后跟唯一性 token 段，无语义尾。

本模块是纯函数、无 IO，两处接入：
- 生成侧：``GalaxyService.ensure_task_node`` / ``task_node_uuid`` 用
  :func:`clean_display_title` 产出干净人类可读名，内部标识只留在 id /
  source_task_id 等非展示字段；
- 读取侧兜底：schemas/galaxy.py 投影、REST/gRPC 响应组装层用
  :func:`strip_internal_tokens` / :func:`clean_display_title` 清洗存量脏
  标题（只清展示面，不做破坏性改库）。

清洗纪律：不含内部 token 形态的输入必须零改写（byte 级原样返回）；
「数据结构复习 — 二叉树专题」「导数应用专题练习」这类含"专题"二字的正常
标题不受影响——模式只在「专题/Topic + 序号 + 连字符段 + 冒号」的完整
内部命名形态上触发。科目形态同理：「AI科目-期末」「CS科目-exam1」
「IT科目-2024-2025」这类正常命名零改写——科目模式只在「TAG贴科目 +
≥2 段含数字 token 段且至少一段 ≥6 位」的完整 harness 形态上触发。
"""

from __future__ import annotations

import re

__all__ = ["clean_display_subject", "clean_display_title", "strip_internal_tokens"]

# harness 命名空间 tag：TOUR / EVAL / SIM 等 2-12 位大写字母数字，后跟空白。
_TAG = r"[A-Z][A-Z0-9]{1,11}\s+"
# 主题词 + 序号：专题7 / Topic 3 / topic 12。
_TOPIC_AND_NUM = r"(?:专题|[Tt]opic)\s*(?P<num>0*[1-9]\d*)"
# 唯一性 token 段：-d91d5df0-10-5dc70d（1..6 段 1+ 位字母数字，连字符/下划线相连；
# 冲刺序号可为个位数，段长下限取 1）。
_TOKEN_RUN = r"(?:\s*[-_]\s*[0-9A-Za-z]+){1,6}"

# 完整内部命名块（带语义尾分隔冒号）：匹配即整体删除、保留冒号后的语义尾。
# 例：「TOUR 专题7-d91d5df0-10-5dc70d: 真题演练与错因回看」→「真题演练与错因回看」；
# 嵌入形态「来自任务的学习主题：TOUR 专题…: 尾」→「来自任务的学习主题：尾」。
_INTERNAL_TOKEN_BLOCK_RE = re.compile(rf"(?:{_TAG})?{_TOPIC_AND_NUM}{_TOKEN_RUN}\s*[:：]\s*")

# 裸 token 整串（无语义尾）：「TOUR 专题7-d91d5df0-10-5dc70d」——用于 fallback 命名。
_BARE_TOKEN_RE = re.compile(rf"^(?:{_TAG})?{_TOPIC_AND_NUM}{_TOKEN_RUN}\s*$")

# plan 科目 token 形态（WT334）：「TOUR科目-d91d5df0-10-5dc70d」——TAG 直接贴
# 「科目/Subject」（无空白），后跟唯一性 token 段。每段必须含数字、至少 2 段，
# 且至少一段 ≥6 位（run_id/uuid6 形态）——「AI科目-期末」「CS科目-exam1」
# 「IT科目-2024-2025」这类正常命名不满足，零改写。
_SUBJECT_NS = r"[A-Z][A-Z0-9]{1,11}(?:科目|[Ss]ubject)"
_SUBJECT_RUN = r"(?:\s*[-_]\s*[0-9A-Za-z]*[0-9][0-9A-Za-z]*){2,}"
_SUBJECT_TOKEN_RE = re.compile(rf"(?P<ns>{_SUBJECT_NS})(?P<run>{_SUBJECT_RUN})")

# 删除块后残留的悬挂分隔符（仅当删除发生过才做此清理，正常标题零改写）。
_DANGLING_SEP_RE = re.compile(r"^\s*[:：\-—–_]\s*|\s*[:：]\s*$")


def _find_topic_number(text: str) -> int | None:
    match = re.search(rf"(?:{_TAG})?{_TOPIC_AND_NUM}{_TOKEN_RUN}", text)
    if match is None:
        return None
    try:
        return int(match.group("num"))
    except (KeyError, ValueError):  # pragma: no cover - group 恒存在，int 恒可解析
        return None


def _qualifying_subject_spans(text: str) -> list[tuple[int, int]]:
    """科目 token 的合格匹配区间：至少一段 ≥6 位（hex 形态）才认定内部 token。"""
    spans: list[tuple[int, int]] = []
    for match in _SUBJECT_TOKEN_RE.finditer(text):
        segments = [seg for seg in re.split(r"[-_\s]+", match.group("run").strip()) if seg]
        if any(len(seg) >= 6 for seg in segments):
            spans.append(match.span())
    return spans


def _strip_subject_tokens(text: str) -> tuple[str, int]:
    """剥离字符串内所有「TAG科目-token」内部科目 token，返回 (结果, 删除次数)。"""
    if not text or ("科目" not in text and "ubject" not in text):
        return text, 0
    spans = _qualifying_subject_spans(text)
    if not spans:
        return text, 0
    parts: list[str] = []
    last = 0
    for start, end in spans:
        parts.append(text[last:start])
        last = end
    parts.append(text[last:])
    return "".join(parts), len(spans)


def strip_internal_tokens(text: str) -> str:
    """剥离字符串内所有「专题N-…:」与「TAG科目-token」内部命名块，保留语义。

    正常（不含该形态）输入零改写原样返回；空串返回空串。纯 token 科目剥除后
    即空串。删除后仅清理悬挂分隔符与多余空白——此清理只在确有删除发生时执行。
    """
    if not text:
        return text
    cleaned, count = _INTERNAL_TOKEN_BLOCK_RE.subn("", text)
    cleaned, subject_count = _strip_subject_tokens(cleaned)
    if count == 0 and subject_count == 0:
        return text
    cleaned = _DANGLING_SEP_RE.sub("", cleaned)
    return re.sub(r"\s{2,}", " ", cleaned).strip()


def clean_display_subject(subject: str | None) -> str:
    """plan subject → 干净展示名（科目链路展示面与生成侧共用）。

    - 纯内部 token 科目：「TOUR科目-d91d5df0-10-5dc70d」→ 空串
      （调用方走既有「无科目」文案兜底，如「你已经走在正确路上了」）；
    - 嵌入形态：剥 token、保留其余语义；
    - 正常科目（含「AI科目-期末」这类合法命名）零改写；None/空 → 空串。
    """
    if not subject:
        return ""
    return strip_internal_tokens(subject)


def clean_display_title(title: str) -> str:
    """任务标题 → 干净人类可读节点名（生成侧与标题兜底共用）。

    - 有语义尾：「TOUR 专题7-d91d5df0-10-5dc70d: 真题演练与错因回看」
      →「真题演练与错因回看」。
    - 全内部 token（无语义尾）：「TOUR 专题7-d91d5df0-10-5dc70d」→「专题 7」
      （保留唯一可读语义：序号）。
    - 正常标题（含"专题"二字的合法命名）零改写；空串返回空串。
    """
    if not title:
        return title
    stripped = strip_internal_tokens(title)
    if stripped != title:
        return stripped
    if _BARE_TOKEN_RE.match(title.strip()):
        number = _find_topic_number(title)
        if number is not None:
            return f"专题 {number}"
    return stripped
