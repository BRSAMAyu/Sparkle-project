"""C-08 · 确定性场景集生成器（c08-context-eval.v1）。

56 个合成场景，四个维度 × 四个设计族；`random.Random(20260921)` 固定种子
排列，无任何真实用户数据。设计族让四臂消融**可解释**：

- `baseline`：满上下文应通过（体验基线）；
- `crowd_out_rag`：中性干扰记忆挤掉低分金标材料 → full 失败、no_memory 通过；
- `outcome_crowd`：带 outcome 的干扰记忆挤掉中性金标记忆 → full 失败、no_outcome 通过；
- `outcome_utility`：金标记忆本身带 outcome（正/负结果证据）→ no_outcome 失败；
- `outcome_harmful`：带 outcome 的干扰记忆会误导 → no_outcome 通过、full 失败；
- `near_distractor`：近邻干扰（一次函数 vs 二次函数）被擦边引用 → harmful context；
- `adversarial`：纯干扰 → 正确行为是「什么都不引」。

token 重叠校准（hanzi bigram + ascii 词，与 C-04 同粒度）：金标内容含查询
主题词（≥3 个 bigram 命中，overlap ≈ 0.25），异主题干扰 ≈ 0，近邻干扰
（一次函数 vs 二次函数）≈ 0.17（故意越过引用阈 0.15 —— 这类「擦边材料
被引用」正是 harmful context 的真实形态，必须被测量而非回避）。
"""

from __future__ import annotations

import random

from .context_eval_schema import (
    DIM_ADVERSARIAL,
    DIM_MEMORY,
    DIM_MIXED,
    DIM_RAG,
    MemoryItem,
    Material,
    OUTCOME_NEGATIVE,
    OUTCOME_NONE,
    OUTCOME_POSITIVE,
    Scenario,
)

_SEED = 20260921

#: (topic, related_topic, fact, related_fact)——related 与 topic 共享部分
#: bigram（真实检索里最危险的近邻干扰）。
TOPICS: list[tuple[str, str, str, str]] = [
    ("二次函数", "一次函数", "顶点式与对称轴求法", "斜率与截距的图象意义"),
    ("光合作用", "呼吸作用", "光反应与暗反应的物质转化", "线粒体中丙酮酸的氧化分解"),
    ("牛顿第二定律", "牛顿第一定律", "合外力与加速度的瞬时关系", "惯性定律的适用条件"),
    ("氧化还原反应", "置换反应", "电子转移与化合价升降守恒", "单质与化合物生成新单质和化合物"),
    ("元代行省制度", "唐代节度使", "中书省派出机构与中央集权", "藩镇割据的军政合一"),
    ("三角函数诱导公式", "和差角公式", "奇变偶不变符号看象限", "两角和的展开与逆用"),
    ("细胞有丝分裂", "细胞减数分裂", "染色体复制后均分到两个子细胞", "同源染色体分离染色体数目减半"),
    ("电磁感应定律", "楞次定律", "磁通量变化率决定感应电动势", "感应电流阻碍磁通量变化"),
    ("化学平衡移动", "电离平衡", "勒夏特列原理对温度压强的判据", "弱电解质部分电离的动态平衡"),
    ("辛亥革命", "戊戌变法", "推翻帝制建立民国的历史意义", "自上而下的改良运动失败原因"),
    ("数列通项公式", "数列求和", "由递推式构造等比或等差形式", "裂项相消与分组求和技巧"),
    ("生态系统能量流动", "物质循环", "营养级间传递效率逐级递减", "碳元素在生物群落与无机环境间循环"),
    ("摩擦力做功", "重力做功", "滑动摩擦力与相对位移的乘积", "只与初末位置高度差有关"),
    ("摩尔质量计算", "气体摩尔体积", "质量与物质的量之间的换算桥梁", "标准状况下气体体积的换算"),
]

_FILLER = "本页整理了章节学习的通用方法与注意事项，适合考前回顾与查漏补缺。"
_FILLER_ALT = "这一部分汇总了典型例题的解题步骤规范与常见易错点提醒。"

#: 记忆模板（gold：与主题相关的学习史；harmful：同主题但误导性建议）。
_MEM_GOLD_POSITIVE = "你在{topic}上用错题本整理过易错点，之后两周正确率明显上升"
_MEM_GOLD_NEGATIVE = "你在{topic}的限时练习中曾因跳步丢分，之后按分步书写订正后恢复"
_MEM_GOLD_NONE = "你曾提问过{topic}的章节测试时间安排，并把它加入了复习计划"
_MEM_HARMFUL = "你上次{topic}测验失利后决定放弃这一章，只复习其他章节"
_MEM_DISTRACTOR = "你偏好用思维导图整理{other}章节的笔记，并保持每周复盘"

_N_RAG = 24
_N_MEMORY = 16
_N_MIXED = 8
_N_ADVERSARIAL = 8


def _material(ref: str, topic: tuple[str, str, str, str], relevant: bool, score: float, *, near: bool = False) -> Material:
    if near:
        # 同主题、错误事实的误导材料——harmful context 的经典形态：与查询
        # 重叠同金标一样高（必然被引用），但内容张冠李戴。
        return Material(ref=ref, content=f"{topic[0]}的易错辨析：{topic[3]}。{_FILLER_ALT}", relevant=relevant, relevance_score=score)
    if relevant:
        return Material(ref=ref, content=f"{topic[0]}的核心要点：{topic[2]}。{_FILLER}", relevant=True, relevance_score=score)
    return Material(ref=ref, content=f"{topic[0]}的核心要点：{topic[2]}。{_FILLER_ALT}", relevant=False, relevance_score=score)


def _other_material(ref: str, other: tuple[str, str, str, str], score: float) -> Material:
    return Material(ref=ref, content=f"{other[0]}的核心要点：{other[2]}。{_FILLER}", relevant=False, relevance_score=score)


def build_scenarios() -> list[Scenario]:
    """确定性构建 56 个场景（同种子重跑逐字节一致）。"""
    rng = random.Random(_SEED)
    scenarios: list[Scenario] = []

    # --- RAG × 24：baseline 12 + crowd_out_rag 6 + near-distractor 6 ---------
    for idx in range(_N_RAG):
        topic = TOPICS[idx % len(TOPICS)]
        family = "baseline"
        if idx % 4 == 1:
            family = "crowd_out_rag"
        elif idx % 4 == 3:
            family = "near_distractor"
        materials: list[Material] = []
        memories: tuple[MemoryItem, ...] = ()
        # 金标材料：crowd_out_rag 族给低分（rerank 靠后），baseline 给高分。
        gold_score = 0.55 if family == "crowd_out_rag" else 0.9
        materials.append(_material(f"doc:g{idx}:1", topic, True, gold_score))
        n_distractors = rng.choice([2, 3]) if family == "crowd_out_rag" else rng.choice([1, 2])
        for k in range(n_distractors):
            other = TOPICS[(idx + k + 1) % len(TOPICS)]
            # 干扰材料拿高分（把低分金标推出注意力窗）。
            materials.append(_other_material(f"doc:d{idx}:{k}", other, 0.85 if family == "crowd_out_rag" else 0.4))
        if family == "near_distractor":
            materials.append(_material(f"doc:n{idx}:1", topic, False, 0.8, near=True))
        if family == "crowd_out_rag":
            # 3 条中性干扰记忆先入窗（prompt 前段）——「记忆体量淹没检索材料」
            # 的挤占效应：full 臂金标材料被挤出 4 槽窗，no_memory 臂 rescued。
            # C-08 N5：TOPICS 是 (title, desc) tuple，format 取 [0]（标题），
            # 否则合成材料里混入 tuple repr（cosmetic）。
            other2 = TOPICS[(idx + 4) % len(TOPICS)]
            memories = tuple(
                MemoryItem(
                    ref=f"mem:c{idx}:{k}",
                    content=_MEM_DISTRACTOR.format(other=other[0] if k == 0 else other2[0]),
                    relevant=False,
                    outcome=OUTCOME_NONE,
                )
                for k in range(3)
            )
        rng.shuffle(materials)
        # 修正：shuffle 后把金标的 score 语义保持（score 排序在 assembly 内做）。
        materials = [
            Material(ref=m.ref, content=m.content, relevant=m.relevant, relevance_score=gold_score if m.relevant else m.relevance_score)
            for m in materials
        ]
        scenarios.append(
            Scenario(
                scenario_id=f"rag-{idx:03d}",
                dimension=DIM_RAG,
                query=f"{topic[0]}这部分的考试重点是什么？",
                materials=tuple(materials),
                memories=memories,
            )
        )

    # --- Memory × 16：outcome_utility 8 + outcome_crowd 4 + harmful 4 --------
    for idx in range(_N_MEMORY):
        topic = TOPICS[(idx + 5) % len(TOPICS)]
        other = TOPICS[(idx + 9) % len(TOPICS)]
        family = ("outcome_utility", "outcome_crowd", "outcome_utility", "outcome_harmful")[idx % 4]
        memories: list[MemoryItem] = []
        if family == "outcome_utility":
            outcome = OUTCOME_POSITIVE if idx % 2 == 0 else OUTCOME_NEGATIVE
            template = _MEM_GOLD_POSITIVE if outcome == OUTCOME_POSITIVE else _MEM_GOLD_NEGATIVE
            memories.append(MemoryItem(ref=f"mem:g{idx}:1", content=f"{template.format(topic=topic[0])}。", relevant=True, outcome=outcome))
            memories.append(MemoryItem(ref=f"mem:d{idx}:1", content=_MEM_DISTRACTOR.format(other=other[0]), relevant=False, outcome=OUTCOME_NONE))
        elif family == "outcome_crowd":
            # 4 条带 outcome 的干扰记忆先入窗、把中性金标记忆挤出 4 槽窗：
            # 「outcome 记忆风暴淹没真正有用的记忆」——no_outcome 臂救回。
            memories.extend(
                MemoryItem(ref=f"mem:c{idx}:{k}", content=_MEM_DISTRACTOR.format(other=TOPICS[(idx + k) % len(TOPICS)][0]), relevant=False, outcome=OUTCOME_NEGATIVE)
                for k in range(4)
            )
            memories.append(MemoryItem(ref=f"mem:g{idx}:1", content=f"{_MEM_GOLD_NONE.format(topic=topic[0])}。", relevant=True, outcome=OUTCOME_NONE))
        else:  # outcome_harmful：金标记忆（无 outcome）+ 带 outcome 的误导记忆
            memories.append(MemoryItem(ref=f"mem:g{idx}:1", content=f"{_MEM_GOLD_NONE.format(topic=topic[0])}。", relevant=True, outcome=OUTCOME_NONE))
            memories.append(MemoryItem(ref=f"mem:h{idx}:1", content=f"{_MEM_HARMFUL.format(topic=topic[0])}。", relevant=False, outcome=OUTCOME_NEGATIVE))
            memories.append(MemoryItem(ref=f"mem:d{idx}:1", content=_MEM_DISTRACTOR.format(other=other[0]), relevant=False, outcome=OUTCOME_NONE))
        # 少量陪衬材料（不改变家族语义；outcome_crowd 族不放材料以隔离变量）。
        materials: list[Material] = []
        if family != "outcome_crowd":
            n_materials = rng.choice([1, 2])
            for k in range(n_materials):
                src = TOPICS[(idx + k + 2) % len(TOPICS)]
                materials.append(_other_material(f"doc:d{idx}:m{k}", src, 0.5))
        scenarios.append(
            Scenario(
                scenario_id=f"mem-{idx:03d}",
                dimension=DIM_MEMORY,
                query=f"{topic[0]}这部分的考试重点是什么？",
                materials=tuple(materials),
                memories=tuple(memories),
            )
        )

    # --- Mixed × 8：金标材料 + 金标记忆（半数带 outcome）---------------------
    for idx in range(_N_MIXED):
        topic = TOPICS[(idx + 2) % len(TOPICS)]
        other = TOPICS[(idx + 7) % len(TOPICS)]
        with_outcome = idx % 2 == 0
        outcome = OUTCOME_POSITIVE if with_outcome else OUTCOME_NONE
        template = _MEM_GOLD_POSITIVE if with_outcome else _MEM_GOLD_NONE
        materials = [
            _material(f"doc:g{idx}:1", topic, True, 0.9),
            _other_material(f"doc:d{idx}:1", other, 0.45),
        ]
        memories = [
            MemoryItem(
                ref=f"mem:g{idx}:1",
                content=f"{template.format(topic=topic[0])}。",
                relevant=True,
                outcome=outcome,
            ),
            MemoryItem(ref=f"mem:d{idx}:1", content=_MEM_DISTRACTOR.format(other=other[0]), relevant=False, outcome=OUTCOME_NONE),
        ]
        scenarios.append(
            Scenario(
                scenario_id=f"mix-{idx:03d}",
                dimension=DIM_MIXED,
                query=f"{topic[0]}这部分的考试重点是什么？",
                materials=tuple(materials),
                memories=tuple(memories),
            )
        )

    # --- Adversarial × 8：纯干扰（半数含近邻干扰 / harmful 记忆）-------------
    for idx in range(_N_ADVERSARIAL):
        topic = TOPICS[(idx + 11) % len(TOPICS)]
        other = TOPICS[(idx + 3) % len(TOPICS)]
        near = idx % 2 == 0
        materials = [
            _other_material(f"doc:d{idx}:1", other, 0.6),
            _other_material(f"doc:d{idx}:2", TOPICS[(idx + 6) % len(TOPICS)], 0.55),
        ]
        if near:
            materials.append(_material(f"doc:n{idx}:1", topic, False, 0.82, near=True))
        memories = ()
        if idx % 4 == 1:
            memories = (
                MemoryItem(ref=f"mem:h{idx}:1", content=f"{_MEM_HARMFUL.format(topic=topic[0])}。", relevant=False, outcome=OUTCOME_NEGATIVE),
            )
        scenarios.append(
            Scenario(
                scenario_id=f"adv-{idx:03d}",
                dimension=DIM_ADVERSARIAL,
                query=f"{topic[0]}这部分的考试重点是什么？",
                materials=tuple(materials),
                memories=memories,
            )
        )

    scenarios.sort(key=lambda scenario: scenario.scenario_id)
    return scenarios
