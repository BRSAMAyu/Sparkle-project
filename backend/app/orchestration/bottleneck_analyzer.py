from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.core.agent_profiles import AgentRole, TaskType
from app.services.llm_service import get_configured_llm_service


@dataclass
class BottleneckItem:
    id: str = field()
    description: str = field()
    severity: str = field()
    specific_risk: str = field()
    affected_concepts: list[str] = field()
    recommendation: str = field()


@dataclass
class BottleneckAnalysis:
    bottlenecks: list[BottleneckItem] = field()
    analysis_method: str = field()
    confidence: float = field()


class BottleneckAnalyzer:
    """
    LLM驱动的个性化瓶颈分析器。

    接收用户状态（掌握度、薄弱节点、时间约束），
    输出具体的、个性化的学习瓶颈（不是通用建议）。
    """

    async def analyze(
        self,
        *,
        subject: str,
        knowledge_baseline: str,
        time_constraint_days: int,
        daily_available_hours: float,
        galaxy_weak_nodes: list[dict],
        available_materials: list[str],
        blocked_days: list[str],
        open_tensions: list[str],
    ) -> BottleneckAnalysis:
        """主入口：尝试LLM分析，失败时降级到规则模板"""
        try:
            return await self._llm_analysis(
                subject=subject,
                knowledge_baseline=knowledge_baseline,
                time_constraint_days=time_constraint_days,
                daily_available_hours=daily_available_hours,
                galaxy_weak_nodes=galaxy_weak_nodes,
                available_materials=available_materials,
                blocked_days=blocked_days,
                open_tensions=open_tensions,
            )
        except Exception as exc:
            logger.warning("BottleneckAnalyzer LLM failed, using rule fallback: {}", exc)
            return self._rule_fallback(
                subject=subject,
                knowledge_baseline=knowledge_baseline,
                time_constraint_days=time_constraint_days,
                daily_available_hours=daily_available_hours,
                galaxy_weak_nodes=galaxy_weak_nodes,
                available_materials=available_materials,
                blocked_days=blocked_days,
                open_tensions=open_tensions,
            )

    async def _llm_analysis(
        self,
        *,
        subject: str,
        knowledge_baseline: str,
        time_constraint_days: int,
        daily_available_hours: float,
        galaxy_weak_nodes: list[dict],
        available_materials: list[str],
        blocked_days: list[str],
        open_tensions: list[str],
    ) -> BottleneckAnalysis:
        """
        LLM prompt设计要求：
        1. 让LLM扮演"学习诊断专家"
        2. 输入：学科、基础描述、时间、weak_nodes列表（含掌握度分数）
        3. 输出：JSON，包含2-4个bottleneck，每个有description/severity/specific_risk/affected_concepts/recommendation
        4. 要求：必须具体（不能只说"基础不好"），必须基于weak_nodes数据
        5. 示例：如果weak_nodes有"热力学第一定律:25分"，bottleneck要提到这个具体节点
        6. temperature=0.2（稳定输出）
        """
        subject = self._strip(subject) or "当前科目"
        baseline = self._strip(knowledge_baseline) or "基础不稳"
        days = self._positive_int(time_constraint_days, default=7)
        hours = self._positive_float(daily_available_hours, default=2.0)
        weak_nodes = self._normalize_weak_nodes(galaxy_weak_nodes)
        materials = self._clean_str_list(available_materials)
        blocked = self._clean_str_list(blocked_days)
        tensions = self._clean_str_list(open_tensions)

        llm = await get_configured_llm_service(AgentRole.STUDY_PLANNER, TaskType.ERROR_DIAGNOSIS)
        messages = self._build_messages(
            subject=subject,
            knowledge_baseline=baseline,
            time_constraint_days=days,
            daily_available_hours=hours,
            galaxy_weak_nodes=weak_nodes,
            available_materials=materials,
            blocked_days=blocked,
            open_tensions=tensions,
        )
        payload = await llm.chat_json(messages=messages, temperature=0.2)
        if not payload:
            raise ValueError("empty bottleneck analysis payload")

        bottlenecks, confidence = self._parse_llm_payload(
            payload=payload,
            subject=subject,
            knowledge_baseline=baseline,
            time_constraint_days=days,
            daily_available_hours=hours,
            galaxy_weak_nodes=weak_nodes,
            available_materials=materials,
            blocked_days=blocked,
            open_tensions=tensions,
        )
        return BottleneckAnalysis(
            bottlenecks=bottlenecks,
            analysis_method="llm",
            confidence=confidence,
        )

    def _rule_fallback(
        self,
        *,
        subject: str,
        knowledge_baseline: str,
        time_constraint_days: int,
        daily_available_hours: float,
        galaxy_weak_nodes: list[dict],
        available_materials: list[str],
        blocked_days: list[str],
        open_tensions: list[str],
    ) -> BottleneckAnalysis:
        """
        保留现有V1规则模板逻辑（从planning_workflow.py _build_bottlenecks复制过来），
        作为LLM失败时的降级。
        analysis_method="rule_fallback"
        """
        subject = self._strip(subject) or "这门课"
        baseline = self._strip(knowledge_baseline) or "基础不稳"
        days = self._positive_int(time_constraint_days, default=7)
        hours = self._positive_float(daily_available_hours, default=2.0)
        hours_text = self._format_hours(hours)
        weak_nodes = self._normalize_weak_nodes(galaxy_weak_nodes)
        blocked = self._clean_str_list(blocked_days)
        materials = self._clean_str_list(available_materials)
        tensions = self._clean_str_list(open_tensions)
        primary_weak = weak_nodes[0] if weak_nodes else None
        primary_name = self._strip(primary_weak.get("name")) if primary_weak else ""
        primary_score = primary_weak.get("mastery_score") if primary_weak else None
        score_text = f"（掌握度约 {self._format_score(primary_score)}）" if primary_score is not None else ""

        bottlenecks = [
            BottleneckItem(
                id="b1",
                description=(
                    f"知识覆盖率不足：{subject} 需要在 {days} 天内完成压缩复习，但你当前只有每天约 {hours_text} 小时的有效时间。"
                    if not blocked
                    else f"知识覆盖率不足：{subject} 需要在 {days} 天内完成压缩复习，而你这几天还夹着忙碌时段（{'；'.join(blocked[:2])}）。"
                ),
                severity="high",
                specific_risk="如果前两天没有快速建立章节框架，后半程很容易只顾着赶进度，留不出完整模拟的时间。",
                affected_concepts=[node["name"] for node in weak_nodes[:3]],
                recommendation=f"先把 {subject} 切成高频保底、必须补强、可以暂缓三类。",
            ),
            BottleneckItem(
                id="b2",
                description=(
                    f"核心概念断点：{primary_name}{score_text} 会拖慢后续题型判断，需要先补这个具体节点，而不是泛泛重学整章。"
                    if primary_name
                    else f"理解成本偏高：你目前属于“{baseline}”状态，说明核心概念需要先用框架化方式补起来，而不能直接堆题。"
                ),
                severity="high",
                specific_risk=(
                    f"如果 {primary_name} 这个断点不先处理，后续遇到综合题时会反复卡在同一个前置概念上。"
                    if primary_name
                    else f"像 {subject} 这类概念多、易混淆的科目，如果不先拉出对比框架，考试时会出现‘看着眼熟但不会判断’的问题。"
                ),
                affected_concepts=[node["name"] for node in weak_nodes[:3]] or [subject],
                recommendation=(
                    f"先用 20 分钟闭卷复述 {primary_name}，再做 3 道同型检查题。"
                    if primary_name
                    else "先做一页核心概念对比表，再进入题目练习。"
                ),
            ),
            BottleneckItem(
                id="b3",
                description=(
                    "题感不足：当前信息里还没有看到你做过稳定的真题或自测，这意味着知识点可能学过却不会落到题型上。"
                    if not materials
                    else f"题感转化压力：你手头已经有 {'、'.join(materials[:2])}，但如果这些材料没被尽快转成自测回路，后面还是会只顾输入不顾检验。"
                ),
                severity="medium",
                specific_risk=(
                    "后两天如果才第一次接触题目，会来不及暴露高频错误类型，冲刺效率会明显下降。"
                    if not tensions
                    else f"目前还有 {len(tensions)} 块信息缺口没完全闭合，如果不尽早用题目和资料一起校准，计划会越来越像按假设推进。"
                ),
                affected_concepts=[node["name"] for node in weak_nodes[:2]] or [subject],
                recommendation="每天至少保留一次闭卷输出或限时小测，把输入材料立刻转成可检验结果。",
            ),
        ]
        return BottleneckAnalysis(
            bottlenecks=bottlenecks,
            analysis_method="rule_fallback",
            confidence=0.55,
        )

    def _build_messages(
        self,
        *,
        subject: str,
        knowledge_baseline: str,
        time_constraint_days: int,
        daily_available_hours: float,
        galaxy_weak_nodes: list[dict[str, Any]],
        available_materials: list[str],
        blocked_days: list[str],
        open_tensions: list[str],
    ) -> list[dict[str, str]]:
        weak_node_lines = [
            {
                "name": node["name"],
                "mastery_score": node.get("mastery_score"),
                "node_type": node.get("node_type"),
            }
            for node in galaxy_weak_nodes[:8]
        ]
        payload = {
            "subject": subject,
            "knowledge_baseline": knowledge_baseline,
            "time_constraint_days": time_constraint_days,
            "daily_available_hours": daily_available_hours,
            "galaxy_weak_nodes": weak_node_lines,
            "available_materials": available_materials[:6],
            "blocked_days": blocked_days[:6],
            "open_tensions": open_tensions[:6],
        }
        system_prompt = (
            "你是 Sparkle 的学习诊断专家，擅长根据知识星图和时间约束定位个性化学习瓶颈。"
            "你必须给出具体、可执行、基于数据的诊断，不能只说“基础不好”“多刷题”这类通用建议。"
        )
        user_prompt = (
            "请基于下面的 JSON 诊断 2-4 个学习瓶颈。\n"
            "要求：\n"
            "1. 每个瓶颈必须具体说明卡在哪里，以及如果不解决会怎样。\n"
            "2. 如果 galaxy_weak_nodes 非空，description 或 affected_concepts 必须点名其中的具体节点。"
            "3. severity 只能是 high、medium、low。\n"
            "4. recommendation 只写一句具体建议。\n"
            "5. 示例：如果 weak_nodes 里有“热力学第一定律:25分”，瓶颈要明确提到“热力学第一定律”，而不是只说“物理基础弱”。\n"
            "只返回 JSON，不要 Markdown。JSON 格式如下：\n"
            '{"bottlenecks":[{"description":"...","severity":"high","specific_risk":"...",'
            '"affected_concepts":["..."],"recommendation":"..."}],"confidence":0.0}\n\n'
            f"输入：\n{json.dumps(payload, ensure_ascii=False)}"
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _parse_llm_payload(
        self,
        *,
        payload: Any,
        subject: str,
        knowledge_baseline: str,
        time_constraint_days: int,
        daily_available_hours: float,
        galaxy_weak_nodes: list[dict],
        available_materials: list[str],
        blocked_days: list[str],
        open_tensions: list[str],
    ) -> tuple[list[BottleneckItem], float]:
        if isinstance(payload, str):
            cleaned = payload.replace("```json", "").replace("```", "").strip()
            try:
                payload = json.loads(cleaned)
            except json.JSONDecodeError as exc:
                raise ValueError("bottleneck analysis string payload is not valid JSON") from exc

        if isinstance(payload, list):
            raw_items = payload
            raw_confidence = None
        elif isinstance(payload, dict):
            raw_items = payload.get("bottlenecks") or payload.get("items") or []
            raw_confidence = payload.get("confidence")
        else:
            raise ValueError("unexpected bottleneck analysis payload type")

        if not isinstance(raw_items, list):
            raise ValueError("bottleneck analysis payload missing list")

        items: list[BottleneckItem] = []
        for raw in raw_items[:4]:
            if not isinstance(raw, dict):
                continue
            description = self._strip(raw.get("description"))
            if not description:
                continue
            affected = self._coerce_concepts(raw.get("affected_concepts") or raw.get("concepts"))
            recommendation = self._strip(raw.get("recommendation") or raw.get("suggestion"))
            risk = self._strip(raw.get("specific_risk") or raw.get("risk"))
            items.append(
                BottleneckItem(
                    id=f"b{len(items) + 1}",
                    description=description,
                    severity=self._normalize_severity(raw.get("severity")),
                    specific_risk=risk or "如果不及时处理，这个问题会持续拖慢后续复习和做题验证。",
                    affected_concepts=affected or [subject],
                    recommendation=recommendation or "先把这个瓶颈转成一个可闭卷检查的小任务。",
                )
            )

        if not items:
            raise ValueError("bottleneck analysis payload produced no valid items")

        items = self._ensure_weak_node_grounding(items, galaxy_weak_nodes)
        if len(items) < 2:
            fallback = self._rule_fallback(
                subject=subject,
                knowledge_baseline=knowledge_baseline,
                time_constraint_days=time_constraint_days,
                daily_available_hours=daily_available_hours,
                galaxy_weak_nodes=galaxy_weak_nodes,
                available_materials=available_materials,
                blocked_days=blocked_days,
                open_tensions=open_tensions,
            ).bottlenecks
            existing = {item.description for item in items}
            items.extend(item for item in fallback if item.description not in existing)

        items = self._renumber(items[:4])
        confidence = self._positive_float(raw_confidence, default=0.82)
        return items, max(0.0, min(confidence, 1.0))

    def _ensure_weak_node_grounding(
        self,
        items: list[BottleneckItem],
        weak_nodes: list[dict[str, Any]],
    ) -> list[BottleneckItem]:
        node_names = [node["name"] for node in self._normalize_weak_nodes(weak_nodes) if node.get("name")]
        if not node_names or not items:
            return items

        def _mentions_node(item: BottleneckItem) -> bool:
            haystack = " ".join(
                [
                    item.description,
                    item.specific_risk,
                    item.recommendation,
                    " ".join(item.affected_concepts),
                ]
            )
            return any(name in haystack for name in node_names)

        if any(_mentions_node(item) for item in items):
            return items

        primary = node_names[0]
        first = items[0]
        concepts = [primary, *[concept for concept in first.affected_concepts if concept != primary]]
        items[0] = BottleneckItem(
            id=first.id,
            description=f"{primary} 是当前最需要先处理的断点：{first.description}",
            severity=first.severity,
            specific_risk=first.specific_risk,
            affected_concepts=concepts[:4],
            recommendation=first.recommendation,
        )
        return items

    def _normalize_weak_nodes(self, raw_nodes: Any) -> list[dict[str, Any]]:
        if not raw_nodes:
            return []
        source = raw_nodes if isinstance(raw_nodes, list) else [raw_nodes]
        normalized: list[dict[str, Any]] = []
        for raw in source:
            if isinstance(raw, dict):
                name = self._strip(
                    raw.get("name") or raw.get("node_name") or raw.get("title") or raw.get("label") or raw.get("id")
                )
                score = self._first_present(raw, ("mastery_score", "mastery", "score", "avg_mastery"))
                node_type = self._strip(raw.get("node_type") or raw.get("type"))
            else:
                name = self._strip(raw)
                score = None
                node_type = ""
            if not name:
                continue
            normalized.append(
                {
                    "name": name,
                    "mastery_score": self._optional_float(score),
                    "node_type": node_type,
                }
            )
        return normalized

    def _coerce_concepts(self, value: Any) -> list[str]:
        if isinstance(value, str):
            pieces = value.replace("，", ",").replace("、", ",").split(",")
            return self._clean_str_list(pieces)
        if isinstance(value, list | tuple | set):
            return self._clean_str_list(list(value))
        return []

    def _clean_str_list(self, value: Any) -> list[str]:
        if not value:
            return []
        source = value if isinstance(value, list | tuple | set) else [value]
        cleaned = [self._strip(item) for item in source if self._strip(item)]
        return cleaned

    def _renumber(self, items: list[BottleneckItem]) -> list[BottleneckItem]:
        return [
            BottleneckItem(
                id=f"b{index + 1}",
                description=item.description,
                severity=item.severity,
                specific_risk=item.specific_risk,
                affected_concepts=item.affected_concepts,
                recommendation=item.recommendation,
            )
            for index, item in enumerate(items)
        ]

    def _normalize_severity(self, value: Any) -> str:
        text = self._strip(value).lower()
        if text in {"high", "高", "严重"}:
            return "high"
        if text in {"low", "低", "轻微"}:
            return "low"
        return "medium"

    def _positive_int(self, value: Any, *, default: int) -> int:
        try:
            parsed = int(float(value))
        except (TypeError, ValueError):
            return default
        return parsed if parsed > 0 else default

    def _positive_float(self, value: Any, *, default: float) -> float:
        parsed = self._optional_float(value)
        return parsed if parsed is not None and parsed > 0 else default

    def _optional_float(self, value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _format_hours(self, value: float) -> str:
        return str(int(value)) if float(value).is_integer() else f"{value:.1f}"

    def _format_score(self, value: Any) -> str:
        parsed = self._optional_float(value)
        if parsed is None:
            return self._strip(value)
        return f"{int(parsed)}分" if parsed.is_integer() else f"{parsed:.1f}分"

    def _first_present(self, payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
        for key in keys:
            if key in payload and payload[key] is not None:
                return payload[key]
        return None

    def _strip(self, value: Any) -> str:
        return str(value or "").strip()


bottleneck_analyzer = BottleneckAnalyzer()
