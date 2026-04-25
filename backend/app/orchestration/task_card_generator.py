from __future__ import annotations

from typing import Any

from app.sprint_packs.sprint_pack_loader import load_pack


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    if value in (None, "", (), []):
        return []
    return [value]


def _safe_int(value: Any) -> int | None:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _split_lines(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list | tuple | set):
        return [_strip(item) for item in value if _strip(item)]
    text = _strip(value)
    if not text:
        return []
    return [
        item.strip()
        for item in text.replace("；", "\n").replace(";", "\n").splitlines()
        if item.strip()
    ]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        normalized = _strip(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


class TaskCardGenerator:
    """Build a structured task card contract from pack data or existing guide fields."""

    _TASK_KIND_TEMPLATE_HINTS: dict[str, dict[str, float]] = {
        "diagnostic_triage": {
            "comparison_table_card": 1.3,
            "concept_recall_card": 1.2,
        },
        "retrieval_triage": {
            "concept_recall_card": 1.5,
            "comparison_table_card": 1.1,
        },
        "retrieval_drill": {
            "calculation_drill_card": 1.4,
            "process_trace_card": 1.25,
        },
        "retrieval_repair": {
            "calculation_drill_card": 1.3,
            "comparison_table_card": 1.1,
        },
        "mock_review": {
            "integrated_scenario_card": 1.4,
            "process_trace_card": 1.1,
        },
        "diagnostic_map": {
            "integrated_scenario_card": 1.4,
            "comparison_table_card": 1.0,
        },
        "closed_book_map": {
            "concept_recall_card": 1.4,
            "process_trace_card": 1.15,
        },
        "deep_learn_retrieval": {
            "concept_recall_card": 1.2,
            "comparison_table_card": 1.2,
            "process_trace_card": 1.0,
        },
        "spaced_retrieval": {
            "concept_recall_card": 1.4,
            "comparison_table_card": 1.05,
        },
        "integration_retrieval": {
            "integrated_scenario_card": 1.5,
            "process_trace_card": 1.25,
        },
        "stage_mock": {
            "integrated_scenario_card": 1.55,
            "calculation_drill_card": 1.1,
        },
    }

    _TEMPLATE_KEYWORDS: dict[str, tuple[str, ...]] = {
        "concept_recall_card": ("概念", "定义", "原理", "基础", "闭卷", "复述", "记忆"),
        "calculation_drill_card": ("计算", "子网", "掩码", "时延", "吞吐", "序号", "窗口", "数值"),
        "process_trace_card": ("流程", "时序", "握手", "挥手", "状态", "报文", "ack", "syn"),
        "comparison_table_card": ("对比", "区别", "vs", "优缺点", "rip", "ospf", "tcp", "udp"),
        "integrated_scenario_card": ("综合", "场景", "端到端", "dns", "http", "浏览器", "链路", "路由"),
    }

    _STRATEGY_TEMPLATE_GROUPS: dict[str, tuple[str, ...]] = {
        "concept_first": ("concept_recall_card", "comparison_table_card"),
        "problem_first": (
            "calculation_drill_card",
            "process_trace_card",
            "integrated_scenario_card",
        ),
    }

    _TEMPLATE_OUTPUTS: dict[str, tuple[str, ...]] = {
        "concept_recall_card": (
            "留下这一轮闭卷提取要覆盖的关键词清单。",
            "写出一版不看资料的核心概念骨架。",
            "标出遗漏项和最容易混淆的地方。",
            "完成一次回写后的闭卷复述或最小小测。",
        ),
        "calculation_drill_card": (
            "写清已知条件、目标量和要用的公式。",
            "独立做完本轮代表题，不先看答案。",
            "定位错误步骤并补一句错因提醒。",
            "重做错题或同型题，确认流程跑通。",
        ),
        "process_trace_card": (
            "写出这条流程的起点、终点和关键状态。",
            "画出第一版时序或步骤链路。",
            "对照标准流程补关键报文、标志位或条件。",
            "闭卷重画一遍，确认不是刚看完才会。",
        ),
        "comparison_table_card": (
            "列出要对比的两个对象和比较维度。",
            "先闭卷填出你确定的差异点。",
            "只补最关键的缺口，不展开到整章重读。",
            "用一句话收口核心区别并做最小检查。",
        ),
        "integrated_scenario_card": (
            "标出场景起点、终点和中间关键层次。",
            "先独立串起端到端的数据流或协议链。",
            "定位断链的位置，只补最影响整合的缺口。",
            "用一题或一次复述验证整条链能说清。",
        ),
    }

    _GENERIC_OUTPUTS: tuple[str, ...] = (
        "写下这一轮的起手框架或关键词。",
        "完成一次独立输出，不先查答案。",
        "补齐最关键的缺口并记录错因。",
        "做一个最小检查，确认不是只看懂。",
    )

    _DEFAULT_AURORA_TRIGGERS: tuple[dict[str, str], ...] = (
        {
            "code": "accuracy_below_0.5",
            "description": "小测正确率低于 50% 时，建议把下一次任务降到更小、更基础的版本。",
            "suggested_action": "reduce_next_task_difficulty",
        },
        {
            "code": "time_overrun_above_0.4",
            "description": "实际耗时超出预估 40% 时，建议缩短步骤并优先保留最小产出。",
            "suggested_action": "shrink_scope_and_keep_minimum_output",
        },
        {
            "code": "same_mistake_repeated",
            "description": "同类错误连续重复时，建议切回概念框架或错因修复模式。",
            "suggested_action": "switch_to_scaffold_or_error_repair",
        },
    )

    def generate(
        self,
        *,
        guide_json: dict[str, Any],
        task_kind: str,
        subject: str,
        focus: str,
        knowledge_state: dict[str, Any] | None = None,
        aurora_control_signal: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        guide = dict(guide_json or {})
        knowledge_state = dict(knowledge_state or {})
        aurora_control_signal = dict(aurora_control_signal or {})
        pack = load_pack(subject) if _strip(subject) else None
        template = self._select_template(
            pack=pack,
            task_kind=task_kind,
            focus=focus,
            guide_json=guide,
            knowledge_state=knowledge_state,
            aurora_control_signal=aurora_control_signal,
        )

        steps = self._normalize_existing_steps(guide.get("steps"))
        if not steps:
            step_names = self._select_step_names(template=template, guide_json=guide)
            steps = self._build_steps(
                step_names=step_names,
                template_id=_strip((template or {}).get("template_id")).lower(),
                guide_json=guide,
                focus=focus,
                task_kind=task_kind,
            )

        done_criteria = _split_lines(guide.get("done_criteria"))
        if not done_criteria:
            done_criteria = self._build_done_criteria(
                guide_json=guide,
                template=template,
                focus=focus,
                knowledge_state=knowledge_state,
            )

        mini_quiz = self._normalize_existing_mini_quiz(guide.get("mini_quiz"))
        if not mini_quiz:
            mini_quiz = self._build_mini_quiz(
                guide_json=guide,
                focus=focus,
                knowledge_state=knowledge_state,
                aurora_control_signal=aurora_control_signal,
            )

        fallback_if_stuck = self._normalize_existing_fallback(guide.get("fallback_if_stuck"))
        if not fallback_if_stuck:
            fallback_if_stuck = self._build_fallback_if_stuck(
                steps=steps,
                template=template,
                guide_json=guide,
                focus=focus,
                knowledge_state=knowledge_state,
            )

        stuck_help = self._normalize_existing_stuck_help(
            guide.get("stuck_help")
            or guide.get("aurora_stuck_help")
            or guide.get("stuck_micro_teaching")
            or guide.get("micro_teaching")
            or guide.get("diagnostic_help")
        )
        if not stuck_help:
            stuck_help = self._build_stuck_help(
                template=template,
                guide_json=guide,
                focus=focus,
                knowledge_state=knowledge_state,
            )

        aurora_triggers = self._normalize_existing_aurora_triggers(guide.get("aurora_triggers"))
        if not aurora_triggers:
            aurora_triggers = self._build_aurora_triggers(
                pack=pack,
                knowledge_state=knowledge_state,
            )

        structured = {
            "steps": steps,
            "done_criteria": done_criteria,
            "mini_quiz": mini_quiz,
            "fallback_if_stuck": fallback_if_stuck,
            "stuck_help": stuck_help,
            "aurora_triggers": aurora_triggers,
        }
        if template:
            structured["task_card_template_id"] = _strip(template.get("template_id"))
        if pack and _strip(pack.get("id")):
            structured["task_card_pack_id"] = _strip(pack.get("id"))
        return structured

    def _select_template(
        self,
        *,
        pack: dict[str, Any] | None,
        task_kind: str,
        focus: str,
        guide_json: dict[str, Any],
        knowledge_state: dict[str, Any],
        aurora_control_signal: dict[str, Any],
    ) -> dict[str, Any] | None:
        templates = [item for item in list((pack or {}).get("task_card_templates") or []) if isinstance(item, dict)]
        if not templates:
            return None

        strategy = self._extract_strategy(aurora_control_signal)
        haystack = " ".join(
            [
                _strip(focus),
                _strip(guide_json.get("objective")),
                _strip(guide_json.get("output_action")),
                " ".join(self._weak_node_names(knowledge_state)),
            ]
        ).lower()

        def score(template: dict[str, Any]) -> float:
            template_id = _strip(template.get("template_id")).lower()
            total = float(self._TASK_KIND_TEMPLATE_HINTS.get(task_kind, {}).get(template_id, 0.0))
            for keyword in self._TEMPLATE_KEYWORDS.get(template_id, ()):
                if keyword.lower() in haystack:
                    total += 0.22
            for strategy_key, template_ids in self._STRATEGY_TEMPLATE_GROUPS.items():
                if strategy.get(strategy_key) and template_id in template_ids:
                    total += 0.35
            expected_duration = _safe_int(template.get("duration_minutes"))
            actual_duration = _safe_int(guide_json.get("time_estimate_minutes"))
            if expected_duration and actual_duration and abs(expected_duration - actual_duration) <= 15:
                total += 0.1
            return total

        ranked = sorted(templates, key=score, reverse=True)
        return ranked[0] if ranked else None

    def _extract_strategy(self, aurora_control_signal: dict[str, Any]) -> dict[str, Any]:
        strategy = _as_dict(aurora_control_signal.get("strategy"))
        if strategy:
            return strategy
        return {
            key: value
            for key, value in aurora_control_signal.items()
            if key in {"concept_first", "problem_first", "worked_example_first"}
        }

    def _select_step_names(
        self,
        *,
        template: dict[str, Any] | None,
        guide_json: dict[str, Any],
    ) -> list[str]:
        template_steps = _split_lines((template or {}).get("steps"))
        if template_steps:
            return self._normalize_step_names(template_steps, guide_json)

        method_steps = _split_lines(guide_json.get("method_steps"))
        if method_steps:
            return self._normalize_step_names(method_steps, guide_json)

        output_action = _strip(guide_json.get("output_action")) or "完成一轮明确输出"
        minimum_output = _strip(guide_json.get("minimum_output")) or "做 3 道小测"
        return [
            "先把今天的范围和关键点压缩成一个起手框架。",
            f"围绕这一个动作开始动手：{output_action}",
            "对照资料只补最关键的缺口，顺手写一句错因或提醒。",
            f"最后用最小检查收口：{minimum_output}。",
        ]

    def _normalize_step_names(self, source: list[str], guide_json: dict[str, Any]) -> list[str]:
        steps = [_strip(item) for item in source if _strip(item)]
        if len(steps) >= 4:
            return steps[:4]

        minimum_output = _strip(guide_json.get("minimum_output")) or "做 3 道小测"
        fillers = [
            "先把你已经确定的部分写出来，不要求一上来就完整。",
            "拿一个最小例子或最小题目开始验证，不先查答案。",
            "对照资料只补最影响正确率的缺口。",
            f"最后用 {minimum_output} 收口，确认今天真的有检索输出。",
        ]
        for filler in fillers:
            if len(steps) >= 4:
                break
            steps.append(filler)
        return steps[:4]

    def _build_steps(
        self,
        *,
        step_names: list[str],
        template_id: str,
        guide_json: dict[str, Any],
        focus: str,
        task_kind: str,
    ) -> list[dict[str, Any]]:
        total_minutes = _safe_int(guide_json.get("time_estimate_minutes")) or 30
        durations = self._distribute_minutes(total_minutes, len(step_names))
        outputs = self._step_outputs(
            template_id=template_id,
            focus=focus,
            guide_json=guide_json,
            task_kind=task_kind,
        )
        return [
            {
                "name": step_names[index],
                "duration_min": durations[index],
                "output": outputs[index],
            }
            for index in range(len(step_names))
        ]

    def _step_outputs(
        self,
        *,
        template_id: str,
        focus: str,
        guide_json: dict[str, Any],
        task_kind: str,
    ) -> list[str]:
        minimum_output = _strip(guide_json.get("minimum_output")) or "做 3 道小测"
        outputs = list(self._TEMPLATE_OUTPUTS.get(template_id, self._GENERIC_OUTPUTS))
        topic = _strip(focus) or _strip(guide_json.get("objective")) or "当前重点"
        if outputs:
            outputs[0] = outputs[0].replace("这一轮", topic if "当前重点" not in topic else "这一轮")
            outputs[-1] = f"{outputs[-1].rstrip('。')}：{minimum_output}。"
        if task_kind in {"mock_review", "stage_mock"}:
            outputs[-1] = "留下这一轮结果、Top 失分点和下一次要先补的对象。"
        return outputs[:4]

    def _distribute_minutes(self, total_minutes: int, count: int) -> list[int]:
        if count <= 0:
            return []
        weights = [0.18, 0.27, 0.33, 0.22][:count]
        if len(weights) < count:
            remaining = count - len(weights)
            weights.extend([1 / count] * remaining)
        scaled = [max(3, int(total_minutes * weight)) for weight in weights]
        diff = total_minutes - sum(scaled)
        index = 0
        while diff != 0 and scaled:
            target = index % len(scaled)
            if diff > 0:
                scaled[target] += 1
                diff -= 1
            elif scaled[target] > 3:
                scaled[target] -= 1
                diff += 1
            index += 1
            if index > 200:
                break
        return scaled

    def _build_done_criteria(
        self,
        *,
        guide_json: dict[str, Any],
        template: dict[str, Any] | None,
        focus: str,
        knowledge_state: dict[str, Any],
    ) -> list[str]:
        weak_node = self._weak_node_names(knowledge_state)[:1]
        items = _dedupe(
            [
                *_split_lines(guide_json.get("success_checklist")),
                *_split_lines(guide_json.get("success_criteria")),
                *_split_lines((template or {}).get("done_criteria")),
            ]
        )
        if weak_node:
            items.insert(0, f"能独立完成一个和「{weak_node[0]}」相关的最小判断、复述或例题。")
        minimum_output = _strip(guide_json.get("minimum_output")) or "完成 3 道小测"
        items.append(f"最后留下可复盘的明确产出：{minimum_output}。")
        items.append("完成内嵌 mini quiz，正确率至少达到 50%。")
        return _dedupe(items)[:4]

    def _build_mini_quiz(
        self,
        *,
        guide_json: dict[str, Any],
        focus: str,
        knowledge_state: dict[str, Any],
        aurora_control_signal: dict[str, Any],
    ) -> dict[str, Any]:
        weak_node = self._weak_node_names(knowledge_state)[:1]
        topic = weak_node[0] if weak_node else (_strip(focus) or _strip(guide_json.get("objective")) or "今天的重点")
        common_mistake = _split_lines(guide_json.get("common_mistakes"))
        strategy = self._extract_strategy(aurora_control_signal)
        route = "先概念骨架，再上题" if strategy.get("concept_first") else "先做最小题，再回看概念"
        return {
            "pass_threshold": 0.5,
            "retry_threshold": 0.5,
            "items": [
                {
                    "question": f"不用看资料，先说出「{topic}」最关键的定义、判断条件或关键词。",
                    "answer": f"至少说出 {topic} 的核心定义 / 触发条件 / 1 个典型信号。",
                    "explanation": "先测能不能提取骨架，而不是只凭刚看完的熟悉感判断自己会了。",
                },
                {
                    "question": f"如果现在遇到一道和「{topic}」相关的题，你第一步会先检查什么？",
                    "answer": "先看题干条件、关键词和已知量，再决定规则、公式或流程。",
                    "explanation": "很多错误不是不会，而是没有先定位触发条件，导致直接跳到后面。",
                },
                {
                    "question": "今天最容易重复的错误是什么？你准备怎么提醒自己别再踩一次？",
                    "answer": (
                        f"{common_mistake[0]}；执行时先走“{route}”。"
                        if common_mistake
                        else f"不要只看懂不自测；执行时先走“{route}”。"
                    ),
                    "explanation": "把常犯错误转成一句可执行提醒，下一轮才更容易真正降错。",
                },
            ],
        }

    def _build_fallback_if_stuck(
        self,
        *,
        steps: list[dict[str, Any]],
        template: dict[str, Any] | None,
        guide_json: dict[str, Any],
        focus: str,
        knowledge_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        weakest = self._weak_node_names(knowledge_state)[:1]
        topic = weakest[0] if weakest else (_strip(focus) or _strip(guide_json.get("objective")) or "当前卡点")
        template_id = _strip((template or {}).get("template_id")).lower()
        scaffold = {
            "concept_recall_card": "定义：___ | 条件：___ | 易混点：___ | 例子：___",
            "calculation_drill_card": "已知：___ | 目标：___ | 公式/规则：___ | 检查：___",
            "process_trace_card": "起点：___ | 关键报文：___ | 状态变化：___ | 结果：___",
            "comparison_table_card": "维度 | A | B | 一句话区别",
            "integrated_scenario_card": "场景起点 -> 应用层 -> 传输层 -> 网络层 -> 链路层",
        }.get(template_id, "题目要求：___ | 已知条件：___ | 下一步：___ | 最小检查：___")
        step_names = [_strip(item.get("name")) for item in steps if _strip(item.get("name"))]
        return [
            {
                "level": 1,
                "title": "先给半成品框架",
                "guidance": [
                    f"先把 {topic} 的骨架写成：{scaffold}",
                    "只填你现在确定的部分，哪怕只有 30%，先不要追完整答案。",
                ],
            },
            {
                "level": 2,
                "title": "再给关键步骤",
                "guidance": step_names[:3]
                or [
                    "先写出你已经知道的条件和关键词。",
                    "只补最关键的缺口，不把任务扩成重读整章。",
                ],
            },
            {
                "level": 3,
                "title": "最后给完整走法",
                "guidance": [
                    f"按这个顺序完整走一遍：{' -> '.join(step_names[:4])}"
                    if step_names
                    else "按“起手框架 -> 独立输出 -> 补关键缺口 -> 最小检查”完整走一遍。"
                ],
            },
        ]

    def _build_stuck_help(
        self,
        *,
        template: dict[str, Any] | None,
        guide_json: dict[str, Any],
        focus: str,
        knowledge_state: dict[str, Any],
    ) -> dict[str, Any]:
        template_id = _strip((template or {}).get("template_id")).lower()
        focus_label = _strip(focus) or _strip(guide_json.get("objective")) or "这一块内容"
        weak_nodes = self._weak_node_names(knowledge_state)
        weak_label = _strip(weak_nodes[0] if weak_nodes else "")
        common_mistakes = _split_lines(guide_json.get("common_mistakes"))
        common_mistake = _strip(common_mistakes[0] if common_mistakes else "")
        check_subject = weak_label or focus_label

        if template_id == "process_trace_card" or any(
            token in focus_label.lower() for token in ("状态", "握手", "挥手", "流程", "时序")
        ):
            diagnosis_question = (
                f"{focus_label}这里你更像卡在“哪些状态/步骤要连起来”，"
                "还是“每一步是在什么条件下触发”的判断？"
            )
            targeted_fix = (
                f"先只修这个断点：{common_mistake}"
                if common_mistake
                else f"先只盯一条关键迁移：写出 {focus_label} 的起点、触发条件和终点，再把这条边接回全流程。"
            )
            check_question = f"小检查：不看资料，试着说出 {check_subject} 里下一步是怎么触发的。"
            options = ["状态/步骤连线", "触发条件判断"]
        elif template_id == "comparison_table_card":
            diagnosis_question = f"{focus_label}这里你更像卡在“对比维度记不住”，还是“题目里不会拿维度去判断”？"
            targeted_fix = (
                f"先把 {common_mistake} 改写成一个对比维度，再只补这一行。"
                if common_mistake
                else f"先只列出 {focus_label} 的 2 个最关键对比维度，再用维度回看一道题。"
            )
            check_question = f"小检查：{check_subject} 至少说出一个最容易混淆的对比点。"
            options = ["对比维度记不住", "不会拿维度判断"]
        else:
            diagnosis_question = f"{focus_label}这里你更像卡在“概念没钉稳”，还是“会概念但落不到题目步骤”？"
            targeted_fix = (
                f"先只修这个高频误区：{common_mistake}"
                if common_mistake
                else f"先用一句话说清 {focus_label} 要解决什么问题，再拿一题只验证这一个判断点。"
            )
            check_question = f"小检查：不用看资料，先说出 {check_subject} 的一个关键判断点。"
            options = ["概念没钉稳", "步骤落不到题目"]

        return {
            "diagnosis_question": diagnosis_question,
            "diagnosis_options": options,
            "targeted_fix": targeted_fix,
            "check_question": check_question,
        }

    def _build_aurora_triggers(
        self,
        *,
        pack: dict[str, Any] | None,
        knowledge_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        triggers = [dict(item) for item in self._DEFAULT_AURORA_TRIGGERS]
        overall_mastery = self._normalized_mastery(knowledge_state.get("overall_mastery"))
        if overall_mastery is not None and overall_mastery < 0.4:
            triggers.append(
                {
                    "code": "overall_mastery_below_0.4",
                    "description": "整体掌握度低于 40% 时，建议 Aurora 退回更稳的保底路线。",
                    "suggested_action": "fallback_to_minimum_pass_path",
                }
            )
        aurora_rules = _as_dict((pack or {}).get("aurora_rules"))
        for rule_name, rule in aurora_rules.items():
            if not isinstance(rule, dict):
                continue
            conditions = _split_lines(rule.get("trigger_conditions") or rule.get("trigger_condition"))
            if not conditions:
                continue
            triggers.append(
                {
                    "code": f"pack_rule_{_strip(rule_name)}",
                    "description": conditions[0],
                    "suggested_action": "follow_pack_aurora_rule",
                }
            )
        return triggers[:5]

    def _weak_node_names(self, knowledge_state: dict[str, Any]) -> list[str]:
        names: list[str] = []
        for item in _as_list(knowledge_state.get("weak_nodes")):
            if isinstance(item, dict):
                name = _strip(item.get("node_name") or item.get("name") or item.get("node"))
            else:
                name = _strip(item)
            if name:
                names.append(name)
        return _dedupe(names)

    def _normalized_mastery(self, value: Any) -> float | None:
        mastery = _safe_float(value)
        if mastery is None:
            return None
        if mastery > 1.0:
            mastery = mastery / 100.0
        return max(0.0, min(1.0, mastery))

    def _normalize_existing_steps(self, value: Any) -> list[dict[str, Any]]:
        steps: list[dict[str, Any]] = []
        for item in _as_list(value):
            if isinstance(item, dict):
                name = _strip(item.get("name"))
                duration = _safe_int(item.get("duration_min")) or 5
                output = _strip(item.get("output"))
            else:
                name = _strip(item)
                duration = 5
                output = ""
            if not name:
                continue
            steps.append(
                {
                    "name": name,
                    "duration_min": duration,
                    "output": output,
                }
            )
        return steps[:4]

    def _normalize_existing_mini_quiz(self, value: Any) -> dict[str, Any] | None:
        quiz = _as_dict(value)
        items = []
        for item in _as_list(quiz.get("items") or quiz.get("questions")):
            if not isinstance(item, dict):
                continue
            question = _strip(item.get("question"))
            answer = _strip(item.get("answer"))
            explanation = _strip(item.get("explanation"))
            if question and answer and explanation:
                items.append(
                    {
                        "question": question,
                        "answer": answer,
                        "explanation": explanation,
                    }
                )
        if len(items) < 3:
            return None
        return {
            "pass_threshold": float(quiz.get("pass_threshold") or 0.5),
            "retry_threshold": float(quiz.get("retry_threshold") or 0.5),
            "items": items[:5],
        }

    def _normalize_existing_fallback(self, value: Any) -> list[dict[str, Any]]:
        fallback: list[dict[str, Any]] = []
        for item in _as_list(value):
            if not isinstance(item, dict):
                continue
            title = _strip(item.get("title") or item.get("label"))
            guidance = _split_lines(item.get("guidance") or item.get("content"))
            level = _safe_int(item.get("level")) or len(fallback) + 1
            if title and guidance:
                fallback.append(
                    {
                        "level": level,
                        "title": title,
                        "guidance": guidance,
                    }
                )
        return fallback

    def _normalize_existing_stuck_help(self, value: Any) -> dict[str, Any]:
        source = _as_dict(value)
        if not source:
            return {}

        diagnosis_question = _strip(
            source.get("diagnosis_question")
            or source.get("diagnostic_question")
            or source.get("question")
            or source.get("step_1")
        )
        targeted_fix = _strip(
            source.get("targeted_fix")
            or source.get("one_targeted_fix")
            or source.get("fix")
            or source.get("step_2")
        )
        if not diagnosis_question or not targeted_fix:
            return {}

        options = _dedupe(_split_lines(source.get("diagnosis_options") or source.get("options")))
        check_question = _strip(
            source.get("check_question")
            or source.get("practice_question")
            or source.get("confirmation_question")
        )
        payload = {
            "diagnosis_question": diagnosis_question,
            "diagnosis_options": options[:2],
            "targeted_fix": targeted_fix,
        }
        if check_question:
            payload["check_question"] = check_question
        return payload

    def _normalize_existing_aurora_triggers(self, value: Any) -> list[dict[str, Any]]:
        triggers: list[dict[str, Any]] = []
        for item in _as_list(value):
            if isinstance(item, dict):
                code = _strip(item.get("code"))
                description = _strip(item.get("description"))
                suggested_action = _strip(item.get("suggested_action"))
                if code and description:
                    triggers.append(
                        {
                            "code": code,
                            "description": description,
                            "suggested_action": suggested_action or "observe",
                        }
                    )
            else:
                code = _strip(item)
                if code:
                    triggers.append(
                        {
                            "code": code,
                            "description": code,
                            "suggested_action": "observe",
                        }
                    )
        return triggers
