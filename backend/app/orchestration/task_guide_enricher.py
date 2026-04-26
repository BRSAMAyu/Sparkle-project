from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger

from app.orchestration.task_card_generator import TaskCardGenerator


def _strip(value: Any) -> str:
    return str(value or "").strip()


class TaskGuideEnricher:
    """
    为已生成的 task guide_json 添加 if_stuck、prerequisite_check 和 why_now。

    设计原则：
    - if_stuck 必须是行动导向的，不能是"去问老师"这类空洞建议
    - prerequisite_check 必须具体，基于当前任务的实际前置知识
    - why_now 必须是一句话解释为什么这个时机做这个任务，不写方法论
    - 有LLM时生成个性化内容，无LLM时用规则模板
    """

    RULE_BASED_IF_STUCK: dict[str, list[str]] = {
        "retrieval_drill": [
            "先不看答案，用关键词把能想到的内容写出来（哪怕只有几个字）",
            "翻到相关章节的标题层级，用标题触发记忆，而不是阅读正文",
            "把卡住的点写下来：'我不知道XXX'，明确化卡点比硬想更有效",
            "切换到更小的单位：如果整章卡住，先只做第一节的一道题",
            "标记为'需要补'，先跳过，继续今天其他部分，最后再回来",
        ],
        "concept_review": [
            "找到这个概念的定义，抄写一遍（不是阅读，是抄写）",
            "举一个你能理解的例子，哪怕例子很简单",
            "找一个对比概念：'这个概念和XXX有什么不同？'",
            "先跳过细节，只理解'这个概念用来解决什么问题'",
        ],
        "diagnostic_triage": [
            "先做最小探针：闭卷写 5 个关键词或做 3 道代表题，不查资料",
            "把不会的内容直接分到'补强'或'defer_or_skip'，不要在原地反复读",
            "只保留一个今天最可能提分的主线，其他内容先写进清单",
            "如果分类困难，按'会做题/只认识/完全陌生'三档先粗分",
        ],
        "retrieval_triage": [
            "先闭卷写概念卡的标题和关键词，空白处用问号占位",
            "打开资料只补问号位置，不顺手展开新章节",
            "把最危险的两个空白改成今天的补强条目",
            "用一道代表题确认这个概念能不能转成判断动作",
        ],
        "retrieval_repair": [
            "只挑一个最高频错误，不同时修多个漏洞",
            "把错因写成'我在XXX条件下会误判YYY'",
            "先重做一道同型题，再决定是否继续补资料",
            "如果仍不会，把题目拆成审题、公式/规则、计算/表达三个小点定位",
        ],
        "mock_review": [
            "先停止翻资料，保留限时节奏完成当前小节",
            "把卡住题标成'不会/会但慢/审题错'三类，不现场深挖",
            "做完后只复盘前三个失分来源，其他错题先放入待补清单",
            "如果时间不足，改做 15 分钟压缩自测并留下失分归因",
        ],
        "diagnostic_map": [
            "先闭卷画三条主线，想不起细节就用空框占位",
            "对照资料只修主线连接，不抄完整正文",
            "用 3 道探针题验证地图里最不确定的节点",
            "把暴露出的薄弱点标成后续 deep learn 或保底处理对象",
        ],
        "closed_book_map": [
            "先重画主链，细枝末节用问号占位",
            "只打开资料补两个最影响理解的空白",
            "用标题和小节名触发记忆，不从正文重新读起",
            "最后闭卷复述一遍主链，确认不是刚看完才认识",
        ],
        "deep_learn_retrieval": [
            "如果旧点复测不过，先取消新增难点，只修旧点",
            "把新难点改写成'它解决什么问题/适用条件是什么'",
            "找一个例题或反例验证理解，不停留在看懂定义",
            "卡住超过 5 分钟就只记录关键疑问，回到今天的最小产出",
        ],
        "spaced_retrieval": [
            "先复测旧点，空白处直接标记，不马上翻资料",
            "打开资料只补复测失败的旧点，不追加新范围",
            "把今天新增内容写成 2 个下一轮可复测的问题",
            "如果时间不足，保留旧点复测和下一轮复测名单",
        ],
        "integration_retrieval": [
            "先做跨章节题，用题目暴露连接点，不先重读章节",
            "把卡住点定位成概念混淆、条件误判或步骤断裂",
            "只补最影响整合题的一个连接点，再做一道小题回测",
            "把跨章节混淆点写入下一轮 spaced retrieval 名单",
        ],
        "stage_mock": [
            "先按正式节奏完成当前轮次，卡题先标记后跳过",
            "做完后把失分分成知识漏洞、提取失败、审题判断三类",
            "只处理 Top 3 失分来源，不把复盘扩成全范围重学",
            "如果时间不足，保留压缩模拟结果和下一轮 5 个复测点",
        ],
        "default": [
            "把卡住的具体位置写下来（越具体越好）",
            "换一个更小的子问题：把当前任务拆成更小的步骤",
            "先完成任务中你确实会的部分，建立动力后再回来",
            "给自己限时5分钟：只要还有努力就算推进",
        ],
    }

    def enrich_sync(
        self,
        *,
        guide_json: dict[str, Any],
        task_kind: str,
        subject: str,
        focus: str,
        bottlenecks: list[dict] | None = None,
        knowledge_state: dict[str, Any] | None = None,
        aurora_control_signal: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """同步规则版 enrichment，用于规划流程里的 task guide_json 初始生成。"""
        enriched = dict(guide_json or {})
        enriched.update(
            TaskCardGenerator().generate(
                guide_json=enriched,
                task_kind=task_kind,
                subject=subject,
                focus=focus,
                knowledge_state=knowledge_state,
                aurora_control_signal=aurora_control_signal,
            )
        )
        enriched["if_stuck"] = self.RULE_BASED_IF_STUCK.get(task_kind, self.RULE_BASED_IF_STUCK["default"])
        enriched["prerequisite_check"] = self._build_prerequisite_check(task_kind, subject, enriched)
        enriched["focus_cue"] = self._build_focus_cue(focus=focus, guide_json=enriched)
        enriched["why_now"] = self._build_why_now(
            task_kind=task_kind,
            subject=subject,
            focus=focus,
            guide_json=enriched,
            bottlenecks=bottlenecks,
        )
        return enriched

    async def enrich_with_llm(
        self,
        *,
        guide_json: dict[str, Any],
        task_kind: str,
        subject: str,
        focus: str,
        bottlenecks: list[dict] | None,
        knowledge_state: dict[str, Any] | None = None,
        aurora_control_signal: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """异步 LLM 版 enrichment，供任务创建后的后台补充流程调用。"""
        return await self.enrich(
            guide_json=guide_json,
            task_kind=task_kind,
            subject=subject,
            focus=focus,
            bottlenecks=bottlenecks,
            knowledge_state=knowledge_state,
            aurora_control_signal=aurora_control_signal,
            use_llm=True,
        )

    async def enrich(
        self,
        *,
        guide_json: dict[str, Any],
        task_kind: str,
        subject: str,
        focus: str,
        bottlenecks: list[dict] | None,
        knowledge_state: dict[str, Any] | None = None,
        aurora_control_signal: dict[str, Any] | None = None,
        use_llm: bool = True,
    ) -> dict[str, Any]:
        """
        返回enriched guide_json，新增：
        - if_stuck: list[str]  (3-5条行动建议)
        - prerequisite_check: list[str] (2-3条"开始前确认")
        - focus_cue: str ("今天最核心的一件事：...")
        - why_now: str (一句话说明为什么现在做)
        """
        enriched = dict(guide_json or {})
        enriched.update(
            TaskCardGenerator().generate(
                guide_json=enriched,
                task_kind=task_kind,
                subject=subject,
                focus=focus,
                knowledge_state=knowledge_state,
                aurora_control_signal=aurora_control_signal,
            )
        )

        if use_llm:
            try:
                llm_additions = await self._llm_enrich(
                    task_kind=task_kind,
                    subject=subject,
                    focus=focus,
                    bottlenecks=bottlenecks,
                    existing_guide=guide_json,
                )
                enriched.update(
                    self._validate_llm_additions(
                        llm_additions=llm_additions,
                        task_kind=task_kind,
                        subject=subject,
                        focus=focus,
                        guide_json=guide_json,
                    )
                )
                return enriched
            except Exception as exc:
                logger.warning("TaskGuideEnricher LLM failed: {}", exc)

        return self.enrich_sync(
            guide_json=enriched,
            task_kind=task_kind,
            subject=subject,
            focus=focus,
            bottlenecks=bottlenecks,
            knowledge_state=knowledge_state,
            aurora_control_signal=aurora_control_signal,
        )

    async def _llm_enrich(
        self,
        *,
        task_kind: str,
        subject: str,
        focus: str,
        bottlenecks: list[dict] | None,
        existing_guide: dict[str, Any],
    ) -> dict[str, Any]:
        """
        LLM prompt：
        - 扮演学习教练
        - 知道任务类型、科目、焦点、今日指南内容
        - 生成：if_stuck(3-5条具体行动，不是笼统建议)、prerequisite_check(2-3条)、focus_cue(1句)
        - 输出JSON
        - temperature=0.3
        """
        from app.services.llm_service import llm_service

        payload = {
            "task_kind": task_kind,
            "subject": subject,
            "focus": focus,
            "bottlenecks": bottlenecks or [],
            "existing_guide": existing_guide or {},
        }
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个务实的学习教练。你的输出必须是可执行的学习指南补充，"
                    "不要给'去问老师'、'多努力'、'保持信心'这类笼统建议。只输出JSON。"
                ),
            },
            {
                "role": "user",
                "content": (
                    "请基于以下任务信息生成 JSON：\n"
                    "{\n"
                    '  "if_stuck": ["3-5条具体行动建议"],\n'
                    '  "prerequisite_check": ["2-3条开始前确认"],\n'
                    '  "focus_cue": "今天最核心的一件事：...",\n'
                    '  "why_now": "一句话解释为什么这个时机做这个任务，不要讲方法论"\n'
                    "}\n\n"
                    f"任务信息：{json.dumps(payload, ensure_ascii=False)}"
                ),
            },
        ]
        result = await llm_service.reason_json(messages=messages, temperature=0.3)
        if not isinstance(result, dict):
            raise ValueError(f"Invalid LLM enrich response type: {type(result)}")
        return result

    def _build_prerequisite_check(
        self,
        task_kind: str,
        subject: str,
        guide_json: dict[str, Any],
    ) -> list[str]:
        subject_label = _strip(subject) or "当前科目"
        topic = self._topic_label(guide_json)
        output_action = _strip(guide_json.get("output_action")) or "今天的明确输出"
        minimum_output = _strip(guide_json.get("minimum_output")) or "闭卷复述或小测"

        if task_kind in {"diagnostic_triage", "retrieval_triage", "diagnostic_map"}:
            return [
                f"确认你已经知道 {subject_label} 这次任务的大致范围：{topic}",
                "准备好纸笔或错题记录位置，用来留下探针结果和三栏清单",
                "能接受先暴露不会的点，而不是一开始就追求完整复习",
            ]

        if task_kind in {"retrieval_drill", "retrieval_repair"}:
            return [
                f"确认你能定位 {topic} 对应的章节、题组或错题来源",
                "准备至少 2-3 道代表题或同型题，不能只靠阅读完成任务",
                f"开始前明确今天的验收方式：{minimum_output}",
            ]

        if task_kind == "concept_review":
            return [
                f"确认你能找到 {topic} 的定义、适用条件或核心公式",
                "准备一个例子和一个容易混淆的对比概念",
                f"知道复习结束时要产出的动作：{output_action}",
            ]

        if task_kind in {"mock_review", "stage_mock"}:
            return [
                "确认计时工具、题目来源和记录错因的位置已经准备好",
                f"确认这次模拟只围绕 {topic} 的阶段验收，不边做边查资料",
                "开始前先接受跳题规则：卡住题先标记，做完后统一复盘",
            ]

        if task_kind in {"closed_book_map", "deep_learn_retrieval", "spaced_retrieval", "integration_retrieval"}:
            return [
                f"确认你能说出 {subject_label} 当前主线中至少 2 个关键词或旧点",
                "准备一个空白页用于闭卷提取、框架重画或复测记录",
                f"确认今天的产出不是泛读，而是：{output_action}",
            ]

        return [
            f"确认你知道今天要处理的具体范围：{topic}",
            "准备好可留下输出痕迹的纸笔、题目或记录工具",
            f"开始前明确完成标准：{_strip(guide_json.get('success_criteria')) or output_action}",
        ]

    def _build_focus_cue(self, *, focus: str, guide_json: dict[str, Any]) -> str:
        cue = _strip(focus) or _strip(guide_json.get("output_action")) or "完成当日任务"
        return f"今天最核心的一件事：{cue}"

    def _build_why_now(
        self,
        *,
        task_kind: str,
        subject: str,
        focus: str,
        guide_json: dict[str, Any],
        bottlenecks: list[dict] | None,
    ) -> str:
        subject_label = _strip(subject) or "这门课"
        focus_label = _strip(focus) or self._topic_label(guide_json)
        bottleneck = ""
        for item in bottlenecks or []:
            bottleneck = _strip(item.get("description") or item.get("specific_risk"))
            if bottleneck:
                break

        if task_kind == "diagnostic_triage":
            return f"现在先分清保底和补强范围，能把{subject_label}的压力变成今天抓得住的第一步。"
        if task_kind == "retrieval_triage":
            return "现在先抓高频概念，能最快看见哪些基础分可以稳住。"
        if task_kind == "retrieval_drill":
            return "今天做代表题，是为了把刚整理的概念立刻变成可判断的题感。"
        if task_kind == "retrieval_repair":
            return "这个时候只修一类错因，能避免最后阶段被一整片漏洞拖住。"
        if task_kind == "mock_review":
            return "现在做限时自测，可以提前暴露最后一天最值得补的失分点。"
        if task_kind == "diagnostic_map":
            return f"现在先搭出{subject_label}的主线，后面的复习才不会变成盲目补洞。"
        if task_kind == "closed_book_map":
            return "现在闭卷重画框架，能判断你是真的会提取，还是刚看完才眼熟。"
        if task_kind == "deep_learn_retrieval":
            return "这个时机只深学一个难点，能让新内容接上旧点，而不是继续堆输入。"
        if task_kind == "spaced_retrieval":
            return "现在先复测旧点，能防止前一天的内容在进入新任务前悄悄掉线。"
        if task_kind == "integration_retrieval":
            return "现在做整合题，能把分散知识点连成考试里真正会用的判断链。"
        if task_kind == "stage_mock":
            return "现在做阶段模拟，能把最后一轮复习的优先级提前排清楚。"
        if bottleneck:
            return f"现在处理{focus_label}，是因为它正卡在{bottleneck}上。"
        return f"现在处理{focus_label}，是为了先拿到一个清楚的推进证据。"

    def build_rule_based_why_now(
        self,
        *,
        task_kind: str,
        subject: str,
        focus: str,
        guide_json: dict[str, Any],
        bottlenecks: list[dict] | None = None,
    ) -> str:
        return self._build_why_now(
            task_kind=task_kind,
            subject=subject,
            focus=focus,
            guide_json=guide_json,
            bottlenecks=bottlenecks,
        )

    def _validate_llm_additions(
        self,
        *,
        llm_additions: dict[str, Any],
        task_kind: str,
        subject: str,
        focus: str,
        guide_json: dict[str, Any],
    ) -> dict[str, Any]:
        if_stuck = self._clean_string_list(llm_additions.get("if_stuck"), min_items=3, max_items=5)
        prerequisite_check = self._clean_string_list(
            llm_additions.get("prerequisite_check"),
            min_items=2,
            max_items=3,
        )
        focus_cue = _strip(llm_additions.get("focus_cue")) or self._build_focus_cue(
            focus=focus,
            guide_json=guide_json,
        )
        if not focus_cue.startswith("今天最核心的一件事："):
            focus_cue = f"今天最核心的一件事：{focus_cue}"
        why_now = self._clean_sentence(llm_additions.get("why_now")) or self._build_why_now(
            task_kind=task_kind,
            subject=subject,
            focus=focus,
            guide_json=guide_json,
            bottlenecks=None,
        )

        return {
            "if_stuck": if_stuck or self.RULE_BASED_IF_STUCK.get(task_kind, self.RULE_BASED_IF_STUCK["default"]),
            "prerequisite_check": prerequisite_check or self._build_prerequisite_check(task_kind, subject, guide_json),
            "focus_cue": focus_cue,
            "why_now": why_now,
        }

    @staticmethod
    def _clean_string_list(value: Any, *, min_items: int, max_items: int) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("Expected a list")
        cleaned = [_strip(item) for item in value if _strip(item)]
        if len(cleaned) < min_items:
            raise ValueError(f"Expected at least {min_items} non-empty items")
        return cleaned[:max_items]

    @staticmethod
    def _clean_sentence(value: Any) -> str:
        text = _strip(value)
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text)
        first_sentence = re.split(r"(?<=[。！？!?])", text, maxsplit=1)[0].strip()
        if first_sentence:
            text = first_sentence
        if len(text) > 90:
            text = text[:90].rstrip("，,；;：: ") + "。"
        if text[-1] not in "。！？!?":
            text = f"{text}。"
        return text

    @staticmethod
    def _topic_label(guide_json: dict[str, Any]) -> str:
        key_points = guide_json.get("key_points")
        if isinstance(key_points, list):
            for item in key_points:
                text = _strip(item)
                if text:
                    return text
        return _strip(guide_json.get("objective")) or _strip(guide_json.get("output_action")) or "今天的任务重点"
