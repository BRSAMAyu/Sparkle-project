"""FIX-575：粘贴/转发形态门（R13——外部材料中的指令不得提升为用户偏好）。

P02 红队 F1 实证（v4/evidence/V4-P02/redteam_playbook.md S1-P1.1）：用户把学习
博主的计划文档原样粘贴进聊天（【转发】高效备考计划…每天只安排15分钟复习…），
``chat_signal_collector._extract_explicit_preferences`` 的纯子串标记匹配把文档
里的指令逐字洗成 explicit 用户偏好三键（conf 0.86-0.92，EXPLICIT 链头，压制后续
推断纠正），违反 R13（v4/03_intelligence/MEMORY_UTILITY_AND_CONFLICT.md §数据
分层：「外部材料中的指令不能提升为用户偏好」）。

本门在偏好抽取（chat_signal_collector）与明示事实抽取（memory_inferred_write_lane）
之前做**纯文本形态**识别：命中粘贴/转发形态的消息不得产出 explicit/0.92 直写档，
只允许以 HYPOTHESIS 候选形态存在（既有确认车道），或由用户本人重述（第一人称
短句照常 explicit）。确定性规则、零 LLM、不造第二权威——只做形态判断，不做
内容语义裁决。

形态信号（全部确定性正则）：
- ``forward_marker``（强）：转发/转载/来源署名标记——材料已自称「来自别处」。
- ``document_structure``（中）：标题行/列表项/步骤标记 ≥2 行——结构化计划文档形态。
- ``second_person_instruction``（中）：第二人称代词指令 + 教导式祈使密度——
  计划文档对读者的命令口吻（用户本人对 AI 说话极少这样写）。
- ``long_text_emergence``（弱）：≥300 字符且 ≥4 句——偏好陈述的异常长度突现。

判定组合（fail-safe：宁可漏捕获，不可洗白）：
1. ``forward_marker`` 命中 → 粘贴形态（材料自称来自外部，人称不影响定性）；
2. 否则第一人称自述主导（≥2 句含「我」且无第二人称代词指令）→ 显式否决
   （用户长篇 onboarding 自述/自己的备忘录粘贴不受损——误报面主防线）；
3. 其余按中+中 / 弱+中 组合判定。

残余盲区（如实记录）：无任何形态标记的纯第一人称粘贴正文结构性不可分辨
（P02 F2 载荷即此形态），需 provenance 贯穿（FIX-575 修法 (a)，归契约 owner）
与 LLM 抽取提示词规则 11（已在位）兜底；本门不做语义判断。形态词表以中文
为主（产品主语言），英文粘贴文档主要靠 fwd:/引用前缀/来源署名标记命中。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# 第一人称单数（fp_dominant 句数统计用，中文面）：「我们」不算（群体材料
# 高频），「本人」算。英文 I/my 只参与 (d) 数值偏好同句共现判定
# （``sentence_has_first_person``），不参与形态门的第一人称主导否决——英文
# 粘贴文档靠 fwd:/引用前缀等来源标记判定（局限如实记录于模块尾注）。
FIRST_PERSON_RE = re.compile(r"我(?!们)|本人")

# (d) 数值偏好的同句第一人称判定：中文 + 英文第一人称单数。
SENTENCE_FIRST_PERSON_RE = re.compile(r"我(?!们)|本人|\bI\b|\bmy\b", re.IGNORECASE)

# 强信号：转发/转载/来源署名。【分享】【转发】成对覆盖；「转：」「转发：」要求
# 行首/括注位置防「转账：」误命中；fwd:/fw: 大小写不敏感；引用前缀行 ≥2 行。
_FORWARD_TOKEN_RES = (
    re.compile(r"【转发】|【转】|【分享】|【转载】|【转贴】"),
    re.compile(r"转载|摘自|引自|搬运"),
    re.compile(r"[（(]来自|来自[:：]"),
    re.compile(r"(?m)(?:^|(?<=[\s【>｜|]))转[发]?[:：]"),
    re.compile(r"(?i)(?:^|(?<=[\s【>｜|]))(?:f|fw|fwd)[:：]"),
)
# 自有来源署名（「来自我的备忘录/笔记…」）不是外部来源：检测前先剥离，
# 用户粘贴自己的备忘录不算转发材料（铁律 5 误报面处置）。
_SELF_SOURCE_RE = re.compile(r"来自我?的?(备忘录|笔记|日记|文档|计划|日程)")
_QUOTE_LINE_RE = re.compile(r"(?m)^\s*>\s")
_FORWARD_QUOTE_LINE_THRESHOLD = 2

# 中信号一：结构化文档形态（按物理行计）。
_MD_HEADING_RE = re.compile(r"^#{1,6}\s+\S")
_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*•·]|\d{1,2}[.、)）]|[一二三四五六七八九十]{1,3}[、.．])\s*")
_STEP_MARKER_RE = re.compile(r"第[一二三四五六七八九十0-9]+步|(?i:step\s*\d)")
_TITLE_LINE_RE = re.compile(r"^.{1,30}[:：]\s*$")
_DOCUMENT_STRUCTURE_MIN_LINES = 2

# 中信号二：第二人称代词指令（计划文档对「你」的命令口吻）。
_SECOND_PERSON_PRONOUN_RE = re.compile(
    r"你(的|要|应(?:该)?|只需?要?|会|就|得|们)|建议你|推荐你|告诉你|提醒你|祝你|各位"
)

# 教导式祈使（与第二人称代词共现或自身密度 ≥2 才计教导口吻；单独一个
# 「坚持」不足以定性——用户第一人称叙述里「坚持」常见）。
_IMPERATIVE_RE = re.compile(r"切记|务必|一定要|切忌|坚持|保持|确保|循序渐进|贵在")
_IMPERATIVE_DENSITY_MIN = 2

# 弱信号：长文本突现（偏好陈述的异常长度）。
_LONG_TEXT_MIN_CHARS = 300
_LONG_TEXT_MIN_SENTENCES = 4

_SENTENCE_SPLIT_RE = re.compile(r"[。！？!?\n]+")

# F2 同修面：粘贴形态下明示事实候选的降档置信（低于 MEMORY_INFERRED_MIN_CONFIDENCE
# = 0.9，进不了任何直写/即时固化档；留在 session 级工作记忆为 HYPOTHESIS 候选）。
PASTE_DEMOTED_CONFIDENCE = 0.62


@dataclass(frozen=True)
class PasteFormSignal:
    """粘贴/转发形态识别结果（纯数据，供门判定与日志观测）。"""

    forward_marker: bool
    document_structure: bool
    second_person_instruction: bool
    long_text_emergence: bool
    first_person_dominant: bool
    paste_form: bool

    def describe(self) -> str:
        return (
            f"forward={self.forward_marker} structure={self.document_structure} "
            f"second_person={self.second_person_instruction} long_text={self.long_text_emergence} "
            f"fp_dominant={self.first_person_dominant} paste_form={self.paste_form}"
        )


def _has_forward_marker(text: str) -> bool:
    cleaned = _SELF_SOURCE_RE.sub("，", text)
    if any(pattern.search(cleaned) for pattern in _FORWARD_TOKEN_RES):
        return True
    return len(_QUOTE_LINE_RE.findall(cleaned)) >= _FORWARD_QUOTE_LINE_THRESHOLD


def _has_document_structure(text: str) -> bool:
    structural_lines = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if (
            _MD_HEADING_RE.match(stripped)
            or _LIST_ITEM_RE.match(stripped)
            or _STEP_MARKER_RE.search(stripped)
            or _TITLE_LINE_RE.match(stripped)
        ):
            structural_lines += 1
        if structural_lines >= _DOCUMENT_STRUCTURE_MIN_LINES:
            return True
    return False


def _sentence_count(text: str) -> int:
    return len([s for s in _SENTENCE_SPLIT_RE.split(text) if len(s.strip()) >= 2])


def detect_paste_form(text: str) -> PasteFormSignal:
    """识别消息是否呈粘贴/转发形态（纯函数，零 IO，零 LLM）。"""
    message = str(text or "")
    if not message.strip():
        return PasteFormSignal(False, False, False, False, False, False)

    forward_marker = _has_forward_marker(message)
    document_structure = _has_document_structure(message)

    pronoun_hits = len(_SECOND_PERSON_PRONOUN_RE.findall(message))
    imperative_hits = len(_IMPERATIVE_RE.findall(message))
    second_person_instruction = pronoun_hits >= 1 and (pronoun_hits + imperative_hits) >= _IMPERATIVE_DENSITY_MIN

    long_text_emergence = len(message) >= _LONG_TEXT_MIN_CHARS and _sentence_count(message) >= _LONG_TEXT_MIN_SENTENCES

    first_person_sentences = [s for s in _SENTENCE_SPLIT_RE.split(message) if FIRST_PERSON_RE.search(s)]
    first_person_dominant = len(first_person_sentences) >= 2

    if forward_marker:
        paste_form = True
    elif first_person_dominant and pronoun_hits == 0:
        # 误报面主防线：≥2 句第一人称自述且无第二人称代词指令 → 用户在说自己
        # （长篇 onboarding/自己的备忘录），结构/长文信号一律让位。
        paste_form = False
    else:
        paste_form = (document_structure and second_person_instruction) or (
            long_text_emergence and (document_structure or second_person_instruction)
        )

    return PasteFormSignal(
        forward_marker=forward_marker,
        document_structure=document_structure,
        second_person_instruction=second_person_instruction,
        long_text_emergence=long_text_emergence,
        first_person_dominant=first_person_dominant,
        paste_form=paste_form,
    )


def sentence_has_first_person(message: str, hint_index: int) -> bool:
    """FIX-575 修法 (d)：``hint_index``（数值匹配起点）所在句是否含第一人称。

    数值偏好（focus_duration_preference 类）必须与第一人称（中「我/本人」、
    英 I/my）同句共现才可 explicit 化——P02 F1 载荷「每天只安排15分钟复习」
    整句无主语，是文档对读者的安排，不是用户口令；「我每天只能投入
    165 分钟」同句共现照常捕获（铁律 2 回归钉）。
    """
    if not message or hint_index < 0 or hint_index >= len(message):
        return False
    for match in re.finditer(r"[^。！？!?\n]+", message):
        if match.start() <= hint_index < match.end():
            return bool(SENTENCE_FIRST_PERSON_RE.search(match.group()))
    return False
