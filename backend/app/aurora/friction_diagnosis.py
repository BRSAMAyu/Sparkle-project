"""A-03 · Friction Diagnosis + Sufficiency / One Best Question（aurora_friction_diagnosis.v1_3）。

**v1_3（V3-FIX-110/111/115 处置，2026-09-26）**：摩擦门语义缺陷族（wt424 审查轮）——

1. **FIX-110 否定感知词牌**：词牌命中若与否定标记（中：并不是/而不是/不是/
   并非/不再是/并没有/没有/不算/不/没；英：词边界 not/no/never/don't/…）
   同句共现且标记位于词牌之前、span 不重叠 → 降为**否定命中**
   （``annotations.utterance_negated_matches``，零证据权重，不进
   ``utterance_matches``）。语义选择 = **降为 unknown 观察档而非硬拦**：
   否定证据是零权重不是否决权（「不是没时间，是太难了」的 difficulty 正向
   证据照常驱动）——与「不假诊断」同律；chat 面出面拦截由 FIX-49 词牌门守
   （否定-only → 正向词牌空 → 门自然静默）。修前「不是没时间，是效率低」
   命中 time:没时间 → act（wt424 探针）。
2. **FIX-111 answer_replay 置信证据面**：``resolve_answer_branch_detail``
   暴露自由文本解析的词面证据强度（命中词牌长度 + 覆盖比 + confident 判定）；
   解析语义不变（v1_1 最长词牌）。接线面据此实施 FIX-49 同构的置信/意图门
   （自由文本不得仅凭词面直出 act；弱命中 pending 保持）。
3. **FIX-115 卡住族词牌**：封闭词表补 chat 面最高频卡点自报
   （卡住/卡住了/进行不下去/stuck，中英，弱权重 0.6 双列 difficulty/energy
   ——与「做不下去」同律，先问不先动）；旅程面 sanctioned 通道不动。
   ``FRICTION_DIAGNOSIS_VERSION`` 与 ``FROZEN_EVIDENCE_FINGERPRINT`` 随词面
   扩展升级。

**v1_2（V3-FIX-50 处置，2026-09-26）**：B1 预算出口的平权 tie 修复——

1. **exact-tie 降级（B3）**：预算尽 best-guess 仅当证据对首要类型有非零区分度
   （``top - runner_up > TIE_DISCRIMINATION_EPSILON``）才按 argmax 行动；
   exact tie（如根分裂宽分支 ``q_direction_vs_push.cant_push`` 10 类支持 × 零
   行为事实 → ``ANSWER_SEED_WEIGHT`` 均摊 → 10 路平权）是「证据对行动零约束」
   ——字母序 argmax 行动纯属偶然（A-08 反例：p06 time 真值段恒落 dependency×3
   纠正环），降级 ``no_action`` + ``insufficient_context``（B2「不假诊断」同律，
   绝不无中生有）。新增封闭 reason 码 ``B3.budget_exhausted_tie_no_action``；
2. **argmax/后验 tie-break 显式契约（字母序）**：``_argmax_type`` /
   ``_posterior_from_scores`` 并列按 ``(−score, type)`` 字典序——跨进程可复现
   （A-08 评估侧曾以 ``PYTHONHASHSEED=0`` 侧写补丁规避，本版起确定性内化为
   引擎契约并有子进程换 seed 测试锁死）。
   ``FRICTION_DIAGNOSIS_VERSION`` 按「扩任何一面需 bump」纪律升级。

**v1_1（WIRING-1 / FIX-43 P2 处置，2026-09-20）**：`resolve_answer_branch`
负向词牌被正向词牌子串遮蔽的语义反转修复——

1. 解析算法改为**最长词牌命中优先**（全分支扫描，最长命中词牌所属分支胜出；
   并列按分支声明序破平）——「不在等/没在等/不等」「不想要了/没那么想要了」
   类反转由算法消解，词面零改动；
2. 唯一词面补充：``tried_unsure`` 增加「不对」——「试过但不对」中单字正向
   词牌「对」的遮蔽无法由最长匹配消解（负向词牌「不对」此前缺席）；
   问题库指纹随之变化（FROZEN_QUESTION_BANK_FINGERPRINT 已同步 bump），
   ``FRICTION_DIAGNOSIS_VERSION`` 按「扩任何一面需 bump」纪律升级。
   生产主路径是 UI branch_key 直传（接线面），自由文本解析是回退层。

产品目标（卡面）：**准确区分卡点并减少问卷式追问**——一次问对，不连环问卷。

机制（卡面 Work 1-3）：

1. **摩擦分类学（friction taxonomy schema + evidence）** —— 15 类封闭词表
   ``FRICTION_TYPES`` 的语义真源是 ``v3/01_product/USER_SEGMENTS_AND_JTBD.md``
   §5「Friction Taxonomy（V3 统一语义）」（entry/clarity/knowledge/skill/
   difficulty/time/energy/dependency/choice/feedback/plan_drift/goal_drift/
   social/tooling/unknown）。本模块零抄写语义判据，词表集 + 证据面（utterance
   封闭词牌 + spine 状态投影 + context 事实规则）逐项 sha256 双钉。分类器是
   **纯规则加权**（真实 LLM 0 次）：同输入 → 同分类（bit-for-bit 确定性，
   测试钉死）。``unknown`` 时**不假诊断**——没有任何正向证据时绝不输出猜测
   标签（卡面 Work 3）。
2. **充分性判定（sufficiency）** —— 现有信号是否足以行动：
   - **置信充分**（``S1``）：top 置信 ≥ 0.55 且领先幅度 ≥ 0.15 → 直出干预提名；
   - **决策等价充分**（``S2``）：竞争带内全部假设的**首要提名相同** → 问了也
     不会改变行动 → 不问（这是「不必要澄清受控」的结构性机制，不是提示词
     约束）；
   - **不足**（``Q1``）： → One Best Question（见 3）；
   - **一次问对闭环**（``S3``）：问 → 用户答（分支键）→ 后验收敛 → 行动
     （``apply_question_answer``）。
3. **One Best Question（信息增益最大化单问）** —— 封闭问题库（6 问 × ≤3
   分支），每个分支携带支持类型集；选择判据 = **期望信息增益**
   （IG = H(P) − Σ_b P(b)·H(P|b)，分支后验按冻结乘子重归一）×**决策敏感**
   过滤（只考虑能把竞争带拆进不同干预路径的问题；拆不动行动的问题不值得
   问）。并列按冻结优先级破平——确定性。问的文本出自封闭模板（锚点 =
   任务/目标名，可空），分支自带建议选项面与**确定性答句解析词牌**（规则
   优先；自由文本→分支的语义解析面留给 E-04 prompt eval 收敛，已登记
   follow-up）。
4. **追问预算（防问卷回潮）** —— per-session/per-day 双上限（缺省 2/5）；
   A-05 clarification patch 的 ``ask_more``/``ask_less`` 偏好（``SURFACE_PAYLOAD_SCHEMES``
   结构派生，零抄写）收紧/放宽预算（ask_less → 1/3，ask_more → 3/8）。
   **超限 → best-guess + 不确定标注**（``B1``：有 argmax 证据则按 argmax 行动
   并标 ``uncertain=True``；无证据则 ``no_action`` + ``insufficient_context``
   不确定类型——绝不无中生有，``B2``）。

与 A 铺链的衔接（不重建既有权威真源）：
- **A-02（下游）**：``FrictionDiagnosis.nominated_interventions`` 是有序提名，
  经 ``policy_factors_patch`` 并入 ``InterventionPolicyFactors.coerce`` 输入
  （``nominated`` 通道）——A-02 管「选哪个干预」，本模块管「卡点是什么 +
  是否需要问」；目录成员集 import 期断言（提名绝无目录外串，R0 面前置）。
- **A-04（兼容）**：本模块产出可并入 ``project_joint_factors`` 的因子面
  （``nominated`` 合并），``decide_joint`` 全链不感知本模块存在也可消费其
  输出——集成测试钉死。
- **A-05（上游信号源）**：``FRICTION_TYPE_TO_LIFECYCLE_TAG`` 把 V3 15 类
  全量投影到 ``INTERVENTION_FRICTION_TAGS``（lifecycle/D-05 切片 + A-05
  ``patched_decision_inputs(friction_tag=...)`` 的 scope 面）；投影 total 且
  值域 import 期断言。A-05 clarification patch 反向作用于本模块的追问预算
  （``clarification_preference`` 入参，调用方从 effective patch 集投影，本
  模块零 IO）。
- **A-01（契约）**：不确定类型用 ``AURORA_UNCERTAINTY_KINDS`` 既有成员
  （``insufficient_context`` 正是 A-01 为 sufficiency 未过预留的档）；
  evidence refs 用既有 scheme（spine 状态 ``signal://``、context 事实
  ``user_state://``），**不新增 ref scheme、不新增词表 39 事件名**。

韧性契约（A-02/A-04 同款）：``diagnose_friction`` 同步、确定性、无 IO、
对任何输入（含脏值）不 raise——内部异常降级 ``no_action`` +
``E1.degraded_to_conservative``。

冻结声明：``FRICTION_TYPES`` / ``FRICTION_INTERVENTION_NOMINATIONS`` /
``FRICTION_UTTERANCE_LEXICON`` / ``SPINE_STATE_EVIDENCE`` /
``CONTEXT_FACT_RULES`` / ``FRICTION_QUESTION_BANK`` /
``FRICTION_DIAGNOSIS_REASONS`` 被 backend/tests/unit/test_a03_friction_diagnosis.py
sha256 双钉；扩任何一面需 bump ``FRICTION_DIAGNOSIS_VERSION`` 并过 reviewer。
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any, Mapping

from loguru import logger

from app.core.aurora_decision import AURORA_INTERVENTION_TYPES
from app.core.intervention_lifecycle import INTERVENTION_FRICTION_TAGS
from app.core.policy_patch import SURFACE_PAYLOAD_SCHEMAS
from app.signals.policy_engine import _RULE_TABLE

#: v1_3：V3-FIX-110/111/115 处置（否定感知词牌 + answer 置信证据面 + 卡住族词牌）。
#: v1_2：V3-FIX-50 处置（B1 exact-tie 降级 B3 + argmax/后验字母序 tie-break 契约）。
#: v1_1：FIX-43 P2 负向反转处置（解析算法最长匹配 + tried_unsure 补「不对」词牌）。
#: 词面/算法变更纪律见模块 docstring 顶部修订记录。
FRICTION_DIAGNOSIS_VERSION = "aurora_friction_diagnosis.v1_3"

# ---------------------------------------------------------------------------
# 封闭词表（冻结；扩展需 bump 版本 + reviewer）
# ---------------------------------------------------------------------------

#: V3 统一摩擦分类学（真源 v3/01_product/USER_SEGMENTS_AND_JTBD.md §5，15 类）。
#: 语义（逐类，真源逐字判据的代码面投影）：
#: - entry：不知道怎么开始；
#: - clarity：任务/成果标准模糊；
#: - knowledge：缺知识/材料；
#: - skill：知道概念但不会做；
#: - difficulty：当前难度过高；
#: - time：可用时间不足/碎片化；
#: - energy：当前认知/情绪负荷不适合；
#: - dependency：等待资源/人/上游；
#: - choice：选项过多；
#: - feedback：不知道自己做得对不对；
#: - plan_drift：原计划已与现实不匹配；
#: - goal_drift：目标本身变化；
#: - social：需要 accountability / feedback / collaborator；
#: - tooling：机械操作/工具摩擦；
#: - unknown：信息不足，必须澄清而不是猜（恒不参与证据加权，只作缺省档）。
FRICTION_TYPES: frozenset[str] = frozenset(
    {
        "entry",
        "clarity",
        "knowledge",
        "skill",
        "difficulty",
        "time",
        "energy",
        "dependency",
        "choice",
        "feedback",
        "plan_drift",
        "goal_drift",
        "social",
        "tooling",
        "unknown",
    }
)

#: 分类面（不含 unknown——unknown 由「无正向证据」结构性导出，不是证据竞争者）。
FRICTION_EVIDENCE_TYPES: tuple[str, ...] = tuple(t for t in sorted(FRICTION_TYPES) if t != "unknown")

#: 摩擦类型 → A-02 目录有序提名（序即优先级；值域 = AURORA_INTERVENTION_TYPES，
#: import 期断言——提名面绝无目录外串）。判据（逐项可评审）：
#: - entry → rescope 先（重建可开始的第一步），split 后；
#: - clarity → clarify（成果标准需要澄清；携带 suggested question）；
#: - knowledge → explain 先（补概念），retrieve 后（召回既有材料）；
#: - skill → practice 先（worked example + drill 是 spine 对 transfer_failure 的
#:   既有策略族），explain 后；
#: - difficulty → split 先（粒度失配先拆小），practice 后；
#: - time → schedule 先（重排时间），split 后（时间盒化更小步）；
#: - energy → pause 先（负荷下调；「状态不好时更克制」是 L2 既有判据），schedule 后；
#: - dependency → remind（到点回访等待项；proactive 面，预算门在 A-02）；
#: - choice → reflect 先（建模会话收敛优先级），rescope 后（收敛后裁剪范围）；
#: - feedback → review（批改产出给外部反馈）；
#: - plan_drift → rescope 先（计划级结构干预 = L2 error_replan_bridge 的目录投影），
#:   schedule 后（重排节奏）；
#: - goal_drift → reflect（目标变化需要重新对齐，不是改计划）；
#: - social → connect_peer；
#: - tooling → delegate 先（机械面代办），co_execute 后（均需 X-02 分配事实，
#:   缺分配时 R4 确定性剔除——正确保守行为，非静默）；
#: - unknown → 空提名（不假诊断：无证据时绝不产出行动提名）。
FRICTION_INTERVENTION_NOMINATIONS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "entry": ("rescope", "split"),
        "clarity": ("clarify",),
        "knowledge": ("explain", "retrieve"),
        "skill": ("practice", "explain"),
        "difficulty": ("split", "practice"),
        "time": ("schedule", "split"),
        "energy": ("pause", "schedule"),
        "dependency": ("remind",),
        "choice": ("reflect", "rescope"),
        "feedback": ("review",),
        "plan_drift": ("rescope", "schedule"),
        "goal_drift": ("reflect",),
        "social": ("connect_peer",),
        "tooling": ("delegate", "co_execute"),
        "unknown": (),
    }
)

# 完整性守卫（import 期 fail-fast）：提名表 key 集 == 分类学；值域 ⊆ A-01 目录。
assert set(FRICTION_INTERVENTION_NOMINATIONS) == set(
    FRICTION_TYPES
), "FRICTION_INTERVENTION_NOMINATIONS must exactly cover FRICTION_TYPES"
for _ftype, _noms in FRICTION_INTERVENTION_NOMINATIONS.items():
    assert (
        set(_noms) <= AURORA_INTERVENTION_TYPES
    ), f"friction {_ftype} nominations out of A-01 catalog: {sorted(set(_noms) - AURORA_INTERVENTION_TYPES)}"

#: V3 15 类 → lifecycle 粗粒度摩擦族（A-05 scope 面 / D-05 切片维度的喂入投影；
#: 与 ``SPINE_STATE_KEY_TO_FRICTION`` 的既有归并语义对齐——本表是细→粗全量
#: 投影，不是第二套粗分类）。判据：粗族语义覆盖细类时取最贴切档；
#: unknown → unattributed（lifecycle 的缺省档，不算分析失败）。
FRICTION_TYPE_TO_LIFECYCLE_TAG: Mapping[str, str] = MappingProxyType(
    {
        "entry": "execution_friction",
        "clarity": "execution_friction",
        "knowledge": "knowledge_bottleneck",
        "skill": "knowledge_bottleneck",
        "difficulty": "execution_friction",
        "time": "deadline_pressure",
        "energy": "affective_pressure",
        "dependency": "material_gap",
        "choice": "engagement_momentum",
        "feedback": "recall_gap",
        "plan_drift": "execution_friction",
        "goal_drift": "engagement_momentum",
        "social": "community_gap",
        "tooling": "execution_friction",
        "unknown": "unattributed",
    }
)

assert set(FRICTION_TYPE_TO_LIFECYCLE_TAG) == set(
    FRICTION_TYPES
), "FRICTION_TYPE_TO_LIFECYCLE_TAG must exactly cover FRICTION_TYPES"
assert (
    set(FRICTION_TYPE_TO_LIFECYCLE_TAG.values()) <= INTERVENTION_FRICTION_TAGS
), "FRICTION_TYPE_TO_LIFECYCLE_TAG values must land in INTERVENTION_FRICTION_TAGS"

# ---------------------------------------------------------------------------
# 证据面 1：utterance 封闭词牌（中英双语；权重冻结）
# ---------------------------------------------------------------------------

#: 权重语义：强词牌（≈2.0）= 措辞无歧义的自我报告；弱词牌（≈0.6）= 高歧义
#: 表达（如「做不下去」横跨 difficulty/energy/goal_drift——本卡验收「同一句
#: 做不下去在不同 Context 产生不同处理」的锚点词牌，只给弱权重，留给 context
#: 证据破局）。词牌匹配 = 归一文本（lower + 空白折叠）子串包含，逐词牌计一次。
FRICTION_UTTERANCE_LEXICON: Mapping[str, Mapping[str, float]] = MappingProxyType(
    {
        "entry": MappingProxyType(
            {
                "不知道怎么开始": 2.0,
                "不知道从哪开始": 2.0,
                "不知道从哪儿开始": 2.0,
                "无从下手": 2.0,
                "不知道第一步": 2.0,
                "不知道先做什么": 1.8,
                "how to start": 1.8,
                "where to start": 1.8,
                "不知道怎么下手": 2.0,
            }
        ),
        "clarity": MappingProxyType(
            {
                "不知道要求": 1.8,
                "不知道要交什么": 2.0,
                "不清楚标准": 2.0,
                "不知道标准": 1.8,
                "做成什么样": 1.6,
                "什么样算好": 1.6,
                "不知道做成什么": 1.8,
                "要求模糊": 1.8,
            }
        ),
        "knowledge": MappingProxyType(
            {
                "看不懂": 1.6,
                "不懂": 1.2,
                "没学过": 2.0,
                "缺基础": 2.0,
                "基础不够": 1.8,
                "理论不懂": 1.8,
                "证明看不懂": 2.0,
                "don't understand": 1.4,
                "do not understand": 1.4,
            }
        ),
        "skill": MappingProxyType(
            {
                "背下来了但不会": 2.2,
                "都会背但不会做": 2.2,
                "看懂了但不会": 2.2,
                "概念都懂但不会做": 2.2,
                "知道概念但不会": 2.2,
                "会背但不会做": 2.2,
                "一做题就不会": 2.0,
                "一动笔就不会": 2.0,
                "自己写就不会": 1.8,
                "不会用": 1.4,
            }
        ),
        "difficulty": MappingProxyType(
            {
                "太难了": 2.0,
                "超出我的水平": 2.0,
                "超纲": 1.6,
                "做不动": 1.2,
                "做不下去": 0.6,
                "推不动": 0.6,
                "搞不定": 1.0,
                "too hard": 1.8,
                # V3-FIX-115 · 卡住族（chat 面最高频卡点自报；弱权重 0.6 双列
                # difficulty/energy——与「做不下去」同律：横跨推不动/状态族的
                # 高歧义表达，先问不先动，context 证据破局）。英文 stuck 子串
                # 匹配（无常见误命中词）。
                "卡住": 0.6,
                "卡住了": 0.6,
                "进行不下去": 0.6,
                "stuck": 0.6,
            }
        ),
        "time": MappingProxyType(
            {
                "没时间": 2.0,
                "时间不够": 2.0,
                "来不及": 2.0,
                "太多课没空": 1.8,
                "时间太碎": 1.8,
                "碎片时间": 1.2,
                "挤不出时间": 2.0,
                "no time": 1.8,
            }
        ),
        "energy": MappingProxyType(
            {
                "累了": 1.8,
                "太累了": 2.0,
                "疲惫": 2.0,
                "状态不好": 2.0,
                "心累": 2.0,
                "emo": 1.4,
                "崩溃": 1.6,
                " burnout": 1.8,
                "脑子转不动": 1.8,
                "学不进去": 1.0,
                "做不下去": 0.6,
                "提不起劲": 1.8,
                # V3-FIX-115 · 卡住族第二列（difficulty 同权重——弱歧义先问）。
                "卡住": 0.6,
                "卡住了": 0.6,
                "进行不下去": 0.6,
                "stuck": 0.6,
            }
        ),
        "dependency": MappingProxyType(
            {
                "在等": 1.6,
                "等他回复": 2.0,
                "等导师": 2.0,
                "等老师": 2.0,
                "还没给我": 1.8,
                "等审批": 2.0,
                "等对方": 1.8,
                "等着他": 1.8,
                "卡在等": 2.0,
                "waiting for": 1.8,
            }
        ),
        "choice": MappingProxyType(
            {
                "不知道选哪个": 2.0,
                "不知道先做哪个": 2.0,
                "太多选择": 1.8,
                "选择太多": 1.8,
                "想做的太多": 2.0,
                "方向太多": 1.8,
                "不知道哪个方向": 2.0,
                "无从选择": 1.8,
            }
        ),
        "feedback": MappingProxyType(
            {
                "不知道对不对": 2.0,
                "不知道做得对": 2.0,
                "做得对吗": 1.8,
                "没人看": 1.8,
                "没人给反馈": 2.0,
                "不知道好不好": 1.8,
                "心里没底": 1.2,
                "没人批改": 2.0,
            }
        ),
        "plan_drift": MappingProxyType(
            {
                "计划赶不上变化": 2.0,
                "原计划不行了": 2.0,
                "计划失效": 2.0,
                "计划全乱了": 1.8,
                "重新弄": 0.8,
                "方案做不了了": 2.0,
                "规则改了": 1.6,
                "得重新规划": 1.8,
                "计划已经不现实": 2.0,
            }
        ),
        "goal_drift": MappingProxyType(
            {
                "目标变了": 2.0,
                "想换方向": 2.0,
                "不想做这个了": 1.8,
                "失去兴趣": 1.8,
                "其实更想": 1.8,
                "当初想做": 1.6,
                "不知道为什么做": 1.4,
                "坚持不下去": 0.6,
            }
        ),
        "social": MappingProxyType(
            {
                "一个人学不下去": 2.2,
                "没有人一起": 2.0,
                "找个搭子": 2.2,
                "没人一起": 2.0,
                "想要有人陪": 1.8,
                "找个伴": 1.8,
                "study buddy": 2.0,
                "学友": 1.6,
            }
        ),
        "tooling": MappingProxyType(
            {
                "环境装不上": 2.2,
                "环境报错": 2.2,
                "环境配不好": 2.2,
                "装了一晚上": 1.8,
                "工具报错": 2.0,
                "一直报错": 1.4,
                "配置搞不定": 2.0,
                "环境问题": 1.8,
                "编译不过": 1.8,
                "跑不起来": 1.6,
            }
        ),
    }
)

assert set(FRICTION_UTTERANCE_LEXICON) == set(
    FRICTION_EVIDENCE_TYPES
), "FRICTION_UTTERANCE_LEXICON must exactly cover the evidence taxonomy (unknown excluded)"

# ---------------------------------------------------------------------------
# V3-FIX-110 · 否定感知词牌匹配（否定式表达 ≠ 正向摩擦自报）
# ---------------------------------------------------------------------------

#: 中文否定标记（子串匹配；降序长度排列便于阅读，命中判定与长度无关——
#: 任一标记在窗口内出现即构成否定）。选词判据：取摩擦自报语域真实出现的
#: 否定形态；不收「别」（别/别人/别的/特别/另外碰撞率过高）、不收「无非/
#: 无需」等书面稀有形。已知残余误报（如实登记）：「不错/没错」与词牌同句
#: 无标点分隔时可能误判否定（如「内容不错就是太难了」）——代价是漏出面
#: （保守方向），与对照侵入（错误出面）相比取轻。
FRICTION_NEGATION_MARKERS_ZH: tuple[str, ...] = (
    "并不是",
    "而不是",
    "不是",
    "并非",
    "不再是",
    "不再",
    "并没有",
    "没有",
    "不算",
    "不",
    "没",
)

#: 英文否定标记（**词边界**正则——防 noted/another/nothing 类子串误伤；
#: 含缩写否定的常见形，撇号/无撇号两形同覆盖——V3-FIX-147：dont/cant/wont
#: 等高频口语拼写与 don't/can't/won't 同判）。与中文标记同窗口语义：位于
#: 词牌之前、span 不重叠才构成否定。
FRICTION_NEGATION_RE_EN = re.compile(
    r"\b(?:not|no|never|without|hardly|(?:do|does|did|is|was|are|were|ca|could|should|wo)n'?t|cannot)\b"
)

#: 子句切分（否定窗口的「同句」边界）：中英标点 + 换行。不按空白切——英文
#: 否定与词牌常隔多词（"I don't think it's too hard"），空白切分会误判。
_FRICTION_CLAUSE_SPLIT_RE = re.compile(r"[，。！？；、,.!?;:：…\n\r\t]+")


def _clause_spans(text: str) -> list[tuple[int, int]]:
    """子句内容 span（分隔符之间的补集段；空段跳过）。"""
    spans: list[tuple[int, int]] = []
    pos = 0
    for match in _FRICTION_CLAUSE_SPLIT_RE.finditer(text):
        if match.start() > pos:
            spans.append((pos, match.start()))
        pos = match.end()
    if pos < len(text):
        spans.append((pos, len(text)))
    return spans


def _negation_spans_in_clause(clause: str, clause_offset: int) -> list[tuple[int, int]]:
    """子句内全部否定标记的全文绝对 span（中：子串；英：词边界正则）。"""
    spans: list[tuple[int, int]] = []
    for marker in FRICTION_NEGATION_MARKERS_ZH:
        start = 0
        while True:
            idx = clause.find(marker, start)
            if idx < 0:
                break
            spans.append((clause_offset + idx, clause_offset + idx + len(marker)))
            start = idx + 1
    for match in FRICTION_NEGATION_RE_EN.finditer(clause):
        spans.append((clause_offset + match.start(), clause_offset + match.end()))
    return spans


def _wordmark_occurrences(text: str) -> list[tuple[int, int]]:
    """全部词牌出现的全文 span（跨类型同形去重；升序）。

    V3-FIX-146 前置：否定作用域按「最近后继词牌」裁决，需要全词牌出现
    布局而非逐词牌孤立判定（否定的最近受害者可能是另一类型的词牌）。
    """
    spans: set[tuple[int, int]] = set()
    for phrases in FRICTION_UTTERANCE_LEXICON.values():
        for phrase in phrases:
            start = 0
            while True:
                idx = text.find(phrase, start)
                if idx < 0:
                    break
                spans.add((idx, idx + len(phrase)))
                start = idx + 1
    return sorted(spans)


def _negated_wordmark_spans(
    text: str, clause_spans: list[tuple[int, int]], occurrences: list[tuple[int, int]]
) -> set[tuple[int, int]]:
    """被否定的词牌出现 span 集（V3-FIX-146 无标点串染修复；子句级裁决）。

    语义（每子句独立、中英同律）：
    - 否定标记只作用于其**最近的一个**后继词牌出现（``neg_end <= occ_start``
      中的最近者）——无标点长句的首个否定标记不再毒化其后全部词牌；
    - 与最近受害 span **重叠**的词牌出现同判否定（嵌套子词牌「看不懂/不懂」
      是同一表面报告，不因作用域收紧而逃逸）；
    - 落在任一词牌出现内部的否定标记是**内容不是算子**（「完全没时间」的
      「没」、「看不懂」的「不」、wordmark-internal "no time" 的 "no"），
      整段出局，亦不得跨词牌外溢；
    - 否定必须前置于被否定对象（span 不重叠结构保证，不变）。
    """
    negated: set[tuple[int, int]] = set()
    for clause_start, clause_end in clause_spans:
        clause_occs = [occ for occ in occurrences if clause_start <= occ[0] < clause_end]
        if not clause_occs:
            continue
        operator_negs = [
            (neg_start, neg_end)
            for neg_start, neg_end in _negation_spans_in_clause(text[clause_start:clause_end], clause_start)
            if not any(neg_start < occ_end and occ_start < neg_end for occ_start, occ_end in clause_occs)
        ]
        for _neg_start, neg_end in operator_negs:
            followers = [occ for occ in clause_occs if occ[0] >= neg_end]
            if not followers:
                continue
            victim = min(followers, key=lambda occ: occ[0])
            negated.update(
                occ for occ in clause_occs if occ[0] < victim[1] and victim[0] < occ[1]
            )
    return negated


def _utterance_wordmark_negated(text: str, phrase: str, negated_spans: set[tuple[int, int]]) -> bool:
    """词牌在文中的**全部**出现均被否定 → True（任一未被否定出现 = 正向命中）。

    ``negated_spans`` 来自 ``_negated_wordmark_spans``（全文一次性裁决，
    V3-FIX-146 作用域语义）。
    """
    start = 0
    occurrences = 0
    while True:
        idx = text.find(phrase, start)
        if idx < 0:
            break
        occurrences += 1
        if (idx, idx + len(phrase)) not in negated_spans:
            return False
        start = idx + 1
    return occurrences > 0

# ---------------------------------------------------------------------------
# 证据面 2：spine 状态投影（state_key → 类型权重；值域覆盖 _RULE_TABLE 全键）
# ---------------------------------------------------------------------------

#: 与 ``SPINE_STATE_KEY_TO_FRICTION``（lifecycle 粗族归并）语义一致的细粒度
#: 加权版：一个 state key 可支持多个 V3 细类（如 cognitive_load 同时压
#: energy/difficulty），权重表达相对强度。key 集 == spine ``_RULE_TABLE``
#: key 集（import 期双向断言，spine 演进即刻暴露）。
SPINE_STATE_EVIDENCE: Mapping[str, Mapping[str, float]] = MappingProxyType(
    {
        "task_granularity_fit": MappingProxyType({"difficulty": 1.2, "entry": 0.6}),
        "knowledge_transfer": MappingProxyType({"skill": 1.4, "knowledge": 0.6}),
        "material_utilization": MappingProxyType({"knowledge": 1.0}),
        "goal_mode": MappingProxyType({"time": 1.4}),
        "crisis_mode": MappingProxyType({"energy": 1.2, "difficulty": 0.4}),
        "cognitive_load": MappingProxyType({"energy": 0.8, "difficulty": 0.8}),
        "affective_pressure": MappingProxyType({"energy": 1.6}),
        "growth_momentum": MappingProxyType({"goal_drift": 0.6, "choice": 0.4}),
        "recall_needed": MappingProxyType({"feedback": 0.6, "knowledge": 0.6}),
        "community_cohort_pattern": MappingProxyType({"social": 1.0}),
        "community_partner_feedback": MappingProxyType({"social": 1.2, "feedback": 0.4}),
        "community_resource_recommendation": MappingProxyType({"social": 0.8, "dependency": 0.4}),
    }
)

assert set(SPINE_STATE_EVIDENCE) == set(
    _RULE_TABLE
), "SPINE_STATE_EVIDENCE must exactly cover the spine _RULE_TABLE state keys"
for _state_key, _weights in SPINE_STATE_EVIDENCE.items():
    assert set(_weights) <= FRICTION_TYPES - {"unknown"}, f"SPINE_STATE_EVIDENCE[{_state_key}] targets out of taxonomy"

# ---------------------------------------------------------------------------
# 证据面 3：context 事实规则（调用方装配的 IO-free 平面事实）
# ---------------------------------------------------------------------------

#: 规则语义（阈值冻结）：
#: - ``days_since_progress ≥ 5``：目标在但迟迟未推进——JTBD 核心摩擦
#:   「知道目标但不知道此刻怎么继续」→ entry 弱证据（2 天内不触发——正常节奏）；
#: - ``recent_failure_count ≥ 3``：连续做错/超时 → skill/difficulty 证据
#:   （spine knowledge_transfer/transfer_failure 的行为面镜像）；
#: - ``blocked_on_external=True``：等待外部（人/资源/环境）→ dependency 强证据；
#: - ``materials_available_unused=True``：材料在库未用 → knowledge 弱证据
#:   （material_utilization 的 context 镜像）；
#: - ``has_active_goal and not has_task_context``：目标层有锚、任务层无锚
#:   → entry 证据（结构性的「不知道怎么开始」）；
#: - ``not has_active_goal and not has_task_context``：无任何锚 → 不加证据
#:   （交给 utterance；全空 → unknown，不假诊断）。
CONTEXT_FACT_RULES_VERSION = "context_fact_rules.v1"

_DAYS_SINCE_PROGRESS_THRESHOLD = 5
_DAYS_SINCE_PROGRESS_WEIGHT = 0.8
_RECENT_FAILURE_THRESHOLD = 3
_RECENT_FAILURE_WEIGHTS: Mapping[str, float] = MappingProxyType({"skill": 1.0, "difficulty": 0.6})
_BLOCKED_ON_EXTERNAL_WEIGHT = 2.0
_MATERIALS_UNUSED_WEIGHT = 0.6
_GOAL_WITHOUT_TASK_WEIGHT = 0.8

# ---------------------------------------------------------------------------
# 充分性参数（冻结）
# ---------------------------------------------------------------------------

#: 置信充分门：top 后验概率下限 + 领先幅度（top - runner-up）下限。
SUFFICIENCY_MIN_CONFIDENCE = 0.55
SUFFICIENCY_MIN_MARGIN = 0.15

#: exact-tie 判别阈（V3-FIX-50）：B1 出口领先幅度 ≤ 此值视为「证据对行动零约束」
#: ——分数来自同一均摊种子的浮点相等（margin 恒 0.0），epsilon 只吸收求和顺序
#: 噪声，不改变任何真实区分度的判定。
TIE_DISCRIMINATION_EPSILON = 1e-9

#: 竞争带：得分 ≥ top 得分 50% 的类型集合（决策等价判定在此带内进行）。
CONTENDER_BAND_RATIO = 0.5

#: 分支后验重加权变换（IG 计算与答案应用**共用同一函数**——选问的假设数学 =
#: 应用数学，不分叉）：支持类型 → ``score×2.0 + 均摊种子``；不支持 →
#: ``score×0.35``。两个不变量：
#: 1. **零先验吸收修复**：答案本身是直接证据，得分表缺席的支持类型经答案
#:    获得种子质量——否则冷启动（unknown 全零分）问询永不收敛；
#: 2. **证据量守恒**：一次答案携带固定证据 ANSWER_SEED_WEIGHT，在支持类型间
#:    **均摊**（``seed/|supports|``）——窄答案锋利、宽答案弱。若按类型全额
#:    注入，宽支持分支（12+ 类）在 IG 假设里熵爆炸，信息增益判据与决策翻转
#:    判据将系统性分歧（选问说没用、翻转说有用——实测踩过）。
BRANCH_SUPPORT_MULTIPLIER = 2.0
BRANCH_DECAY_MULTIPLIER = 0.35
ANSWER_SEED_WEIGHT = 1.0

#: 追问预算缺省（per-session / per-day）与 A-05 clarification 偏好调整表。
DEFAULT_SESSION_QUESTION_LIMIT = 2
DEFAULT_DAY_QUESTION_LIMIT = 5
#: ask_less → 收紧；ask_more → 放宽（值域 = A-05 ``SURFACE_PAYLOAD_SCHEMAS``
#: clarification 面的结构派生，零抄写；漂移即 import 期 fail-fast）。
CLARIFICATION_PREFERENCE_VALUES: frozenset[str] = frozenset(SURFACE_PAYLOAD_SCHEMAS["clarification"])
CLARIFICATION_PREFERENCE_BUDGETS: Mapping[str, tuple[int, int]] = MappingProxyType(
    {
        "ask_less": (1, 3),
        "ask_more": (3, 8),
    }
)

assert set(CLARIFICATION_PREFERENCE_BUDGETS) == set(
    CLARIFICATION_PREFERENCE_VALUES
), "CLARIFICATION_PREFERENCE_BUDGETS must exactly cover A-05 clarification payload values"

# ---------------------------------------------------------------------------
# 决策 reason codes（封闭；前缀语义对齐 A-02/X-02 风格）
# ---------------------------------------------------------------------------

#: S*=充分出口 · Q*=问询出口 · B*=预算出口 · U*=unknown 出口 · E*=降级。
FRICTION_DIAGNOSIS_REASONS: frozenset[str] = frozenset(
    {
        "S1.sufficient_confidence",  # 置信充分 → 直出提名
        "S2.sufficient_decision_equivalence",  # 竞争带同首要提名 → 问了不改变行动 → 不问
        "S3.sufficient_after_question",  # 一次问询后收敛（apply_question_answer 出口）
        "Q1.insufficient_ask_best_question",  # 不足 → One Best Question（预算内）
        "Q2.no_discriminative_question_act_argmax",  # 无决策敏感问题 → 按 argmax 行动（不确定标注）
        "B1.budget_exhausted_best_guess",  # 预算超限 → best-guess + uncertain 标注
        "B2.budget_exhausted_unknown_no_action",  # 预算超限且无证据 → 不假诊断 no_action
        "B3.budget_exhausted_tie_no_action",  # 预算超限且 exact tie（证据对行动零约束）→ 不猜 no_action
        "U1.unknown_ask_entry_question",  # 无正向证据 → unknown，仍可问根分裂问题（预算内）
        "E1.degraded_to_conservative",  # 内部异常 → no_action 保守降级
    }
)

#: 诊断出口（封闭三值：行动 / 问询 / 不行动）。
FRICTION_OUTCOMES: frozenset[str] = frozenset({"act", "ask", "no_action"})


# ---------------------------------------------------------------------------
# One Best Question：封闭问题库（分支支持集 + 确定性答句词牌）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QuestionBranch:
    """问题分支：封闭 answer 键 + 支持类型集 + 建议选项文案 + 答句解析词牌。

    ``match_terms`` 是自由文本答案 → 分支的**规则优先**解析面（确定性第一层；
    语义解析的模型面归 E-04 prompt eval 收敛——本卡 LLM 0 次，follow-up 已登记）。
    """

    key: str
    label: str
    supports: frozenset[str]
    match_terms: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        assert self.supports <= FRICTION_TYPES - {
            "unknown"
        }, f"branch {self.key!r} supports out of taxonomy: {sorted(self.supports)}"


@dataclass(frozen=True)
class QuestionSpec:
    """判别问题：文本模板（``{anchor}`` 占位符可空渲染）+ 有序分支 + 优先级。"""

    question_id: str
    text_template: str
    branches: tuple[QuestionBranch, ...]
    priority: int

    @property
    def supported_types(self) -> frozenset[str]:
        return frozenset().union(*(branch.supports for branch in self.branches))

    def render(self, anchor: str | None) -> str:
        """确定性渲染：锚点存在 → 「{anchor}」嵌入；缺失 → 去锚渲染（占位符
        清空而非残留），统一折叠空白。"""
        anchor_text = f"「{anchor}」" if anchor else ""
        rendered = self.text_template.replace("{anchor}", anchor_text)
        return " ".join(rendered.split())


#: 问题库（冻结 6 问；优先级数值小者先——IG 并列时的确定性破平序）。
#: 每问的分支设计判据（split 语义逐项可评审）：
#: - q_direction_vs_push：根分裂——「不知道做什么」vs「知道但推不动」
#:   （把 entry/clarity/choice/goal_drift 与执行/状态族分开；歧义词牌
#:   「做不下去」场景的最高 IG 首问）；
#: - q_content_vs_state：推不动的内因——内容卡（要学的没掌握）vs 状态卡
#:   （累/时间/情绪），分开 knowledge/skill/difficulty/tooling 与
#:   energy/time/social/plan_drift；
#: - q_standard_clarity：验收标准清楚吗——clarity 的定向判别；
#: - q_external_wait：是否在等外部——dependency 的定向判别；
#: - q_tried_and_checked：做过吗+对不对——skill（没做对过）与 feedback
#:   （做了没把握/没人看）的分离面；「试过且对」→ 难度/节奏族；
#: - q_goal_still_wanted：目标还成立吗——goal_drift 的定向判别。
FRICTION_QUESTION_BANK: tuple[QuestionSpec, ...] = (
    QuestionSpec(
        question_id="q_direction_vs_push",
        text_template="{anchor}这步，是不知道下一步该做什么，还是知道做什么但推不动？",
        branches=(
            QuestionBranch(
                key="no_direction",
                label="不知道下一步做什么",
                supports=frozenset({"entry", "clarity", "choice", "goal_drift"}),
                match_terms=frozenset(
                    {"不知道做什么", "不知道下一步", "不知道该干", "没方向", "不知道怎么开始", "no idea"}
                ),
            ),
            QuestionBranch(
                key="cant_push",
                label="知道做什么，但推不动",
                supports=frozenset(
                    {
                        "difficulty",
                        "skill",
                        "knowledge",
                        "energy",
                        "time",
                        "tooling",
                        "dependency",
                        "feedback",
                        "social",
                        "plan_drift",
                    }
                ),
                match_terms=frozenset({"知道做什么", "推不动", "做不动", "干不下去", "卡住"}),
            ),
        ),
        priority=1,
    ),
    QuestionSpec(
        question_id="q_content_vs_state",
        text_template="推不动主要是内容卡住（要学/要做的没掌握），还是状态卡住（累/没时间/情绪）？",
        branches=(
            QuestionBranch(
                key="content_stuck",
                label="内容卡住",
                supports=frozenset({"knowledge", "skill", "difficulty", "tooling"}),
                match_terms=frozenset({"内容", "不会", "没掌握", "看不懂", "难"}),
            ),
            QuestionBranch(
                key="state_stuck",
                label="状态卡住",
                supports=frozenset({"energy", "time", "social", "plan_drift"}),
                match_terms=frozenset({"状态", "累", "没时间", "情绪", "烦"}),
            ),
        ),
        priority=2,
    ),
    QuestionSpec(
        question_id="q_standard_clarity",
        text_template="{anchor}要交什么、做到什么程度算好，现在清楚吗？",
        branches=(
            QuestionBranch(
                key="standard_unclear",
                label="不清楚",
                supports=frozenset({"clarity", "entry"}),
                match_terms=frozenset({"不清楚", "不知道", "模糊", "没说", "unclear"}),
            ),
            QuestionBranch(
                key="standard_clear",
                label="清楚",
                supports=frozenset(
                    {
                        "difficulty",
                        "skill",
                        "knowledge",
                        "time",
                        "energy",
                        "feedback",
                        "plan_drift",
                        "choice",
                        "goal_drift",
                        "dependency",
                        "social",
                        "tooling",
                    }
                ),
                match_terms=frozenset({"清楚", "明确", "知道", "clear"}),
            ),
        ),
        priority=3,
    ),
    QuestionSpec(
        question_id="q_external_wait",
        text_template="是在等某个外部条件吗（人回复 / 资料到位 / 环境可用）？",
        branches=(
            QuestionBranch(
                key="waiting_external",
                label="在等外部条件",
                supports=frozenset({"dependency"}),
                match_terms=frozenset({"在等", "等", "waiting", "还没回"}),
            ),
            QuestionBranch(
                key="not_waiting",
                label="不在等",
                supports=frozenset(
                    {
                        "entry",
                        "clarity",
                        "knowledge",
                        "skill",
                        "difficulty",
                        "time",
                        "energy",
                        "choice",
                        "feedback",
                        "plan_drift",
                        "goal_drift",
                        "social",
                        "tooling",
                    }
                ),
                match_terms=frozenset({"不等", "没在等", "不在等", "no"}),
            ),
        ),
        priority=4,
    ),
    QuestionSpec(
        question_id="q_tried_and_checked",
        text_template="自己完整试过一遍了吗？做出来的部分，有把握是对的？",
        branches=(
            QuestionBranch(
                key="not_tried",
                label="还没试过",
                supports=frozenset({"entry", "energy"}),
                match_terms=frozenset({"没试", "没做", "还没开始", "not yet"}),
            ),
            QuestionBranch(
                key="tried_unsure",
                label="试过，没把握",
                supports=frozenset({"skill", "feedback"}),
                match_terms=frozenset({"没把握", "不确定", "不知道对不对", "不对", "unsure"}),
            ),
            QuestionBranch(
                key="tried_confident",
                label="试过，也对，就是推进慢",
                supports=frozenset({"difficulty", "plan_drift", "time"}),
                match_terms=frozenset({"有把握", "对", "慢", "confident"}),
            ),
        ),
        priority=5,
    ),
    QuestionSpec(
        question_id="q_goal_still_wanted",
        text_template="{anchor}这个目标，现在还想要吗？",
        branches=(
            QuestionBranch(
                key="goal_still_wanted",
                label="还想要",
                supports=frozenset(
                    {
                        "entry",
                        "clarity",
                        "knowledge",
                        "skill",
                        "difficulty",
                        "time",
                        "energy",
                        "dependency",
                        "choice",
                        "feedback",
                        "plan_drift",
                        "social",
                        "tooling",
                    }
                ),
                match_terms=frozenset({"想要", "要", "还想", "yes"}),
            ),
            QuestionBranch(
                key="goal_shifted",
                label="其实没那么想要了",
                supports=frozenset({"goal_drift"}),
                match_terms=frozenset({"不想要", "没那么想要", "变了", "换"}),
            ),
        ),
        priority=6,
    ),
)

_QUESTION_BANK_INDEX: Mapping[str, QuestionSpec] = MappingProxyType(
    {spec.question_id: spec for spec in FRICTION_QUESTION_BANK}
)
assert len(_QUESTION_BANK_INDEX) == len(FRICTION_QUESTION_BANK), "duplicate question_id in bank"


# ---------------------------------------------------------------------------
# 输入（flat、IO-free 投影；A-02 Factors / A-04 Sources 同款纪律）
# ---------------------------------------------------------------------------


def _normalize_text(raw: Any) -> str:
    if not isinstance(raw, str):
        return ""
    return " ".join(raw.lower().split())


def _norm_state_keys(raw: Any) -> frozenset[str]:
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, (list, tuple, set, frozenset)):
        return frozenset()
    return frozenset(str(entry).strip() for entry in raw if isinstance(entry, str) and str(entry).strip())


def _opt_int(raw: Any, *, minimum: int, maximum: int) -> int | None:
    if isinstance(raw, bool) or not isinstance(raw, int):
        return None
    return raw if minimum <= raw <= maximum else None


def _opt_bool(raw: Any) -> bool | None:
    if raw is True or raw is False:
        return raw
    return None


def _norm_preference(raw: Any) -> str | None:
    if isinstance(raw, str):
        value = raw.strip().lower()
        return value if value in CLARIFICATION_PREFERENCE_VALUES else None
    return None


@dataclass(frozen=True)
class FrictionDiagnosisInput:
    """摩擦诊断输入的 flat 投影（全部可空/缺省；脏值 → 缺省，不 raise）。

    - ``utterance``：用户卡点表达原文（可空——纯行为信号诊断）；
    - ``spine_state_keys``：spine StateRegister 当前活跃 state_key 集
      （值域 = ``_RULE_TABLE`` key；未知键静默忽略并登记 annotations）；
    - ``task_anchor``：任务/目标名（问句锚点渲染；可空）；
    - 行为/结构事实：``days_since_progress`` [0, 365]、``recent_failure_count``
      [0, 100]、``blocked_on_external``、``materials_available_unused``、
      ``has_active_goal``、``has_task_context``；
    - ``answered_branches``：本会话已问问题的 (question_id, branch_key) 序对
      （问→答闭环的累积证据——重放诊断时携带，等价于 apply 链）；
    - 预算事实：``questions_asked_session`` / ``questions_asked_day``（调用方
      从会话/日计数装配；本模块零 IO）；
    - ``clarification_preference``：A-05 clarification patch 的 ask_more/
      ask_less 偏好投影（调用方从 effective patch 集装配）。
    """

    utterance: str = ""
    spine_state_keys: frozenset[str] = frozenset()
    task_anchor: str | None = None
    days_since_progress: int | None = None
    recent_failure_count: int | None = None
    blocked_on_external: bool | None = None
    materials_available_unused: bool | None = None
    has_active_goal: bool | None = None
    has_task_context: bool | None = None
    answered_branches: tuple[tuple[str, str], ...] = ()
    questions_asked_session: int = 0
    questions_asked_day: int = 0
    clarification_preference: str | None = None

    @classmethod
    def coerce(cls, raw: FrictionDiagnosisInput | Mapping[str, Any] | None) -> FrictionDiagnosisInput:
        """防御性归一：脏值 → 缺省（规则核心永不因脏输入炸）。"""
        if raw is None:
            return cls()
        if isinstance(raw, FrictionDiagnosisInput):
            return raw
        if not isinstance(raw, Mapping):
            return cls()
        answered_raw = raw.get("answered_branches") or ()
        answered: list[tuple[str, str]] = []
        if isinstance(answered_raw, (list, tuple)):
            for pair in answered_raw:
                if isinstance(pair, (list, tuple)) and len(pair) == 2:
                    qid = str(pair[0]).strip()
                    bkey = str(pair[1]).strip()
                    if qid in _QUESTION_BANK_INDEX:
                        spec = _QUESTION_BANK_INDEX[qid]
                        if bkey in {branch.key for branch in spec.branches}:
                            answered.append((qid, bkey))
        anchor = raw.get("task_anchor")
        anchor_str = " ".join(str(anchor).split())[:60] if isinstance(anchor, str) and str(anchor).strip() else None
        return cls(
            utterance=_normalize_text(raw.get("utterance")),
            spine_state_keys=_norm_state_keys(raw.get("spine_state_keys")),
            task_anchor=anchor_str,
            days_since_progress=_opt_int(raw.get("days_since_progress"), minimum=0, maximum=365),
            recent_failure_count=_opt_int(raw.get("recent_failure_count"), minimum=0, maximum=100),
            blocked_on_external=_opt_bool(raw.get("blocked_on_external")),
            materials_available_unused=_opt_bool(raw.get("materials_available_unused")),
            has_active_goal=_opt_bool(raw.get("has_active_goal")),
            has_task_context=_opt_bool(raw.get("has_task_context")),
            answered_branches=tuple(answered),
            questions_asked_session=_opt_int(raw.get("questions_asked_session"), minimum=0, maximum=1000) or 0,
            questions_asked_day=_opt_int(raw.get("questions_asked_day"), minimum=0, maximum=10000) or 0,
            clarification_preference=_norm_preference(raw.get("clarification_preference")),
        )


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OneBestQuestion:
    """被选中的单问（封闭库成员的确定性投影：不复制模板文本，携带渲染结果）。

    - ``question_id`` / ``text`` / ``branch_options``：问询面（chat 侧把
      branch_options 渲染为建议选项；answer 由 ``resolve_answer_branch``
      规则解析或 E-04 模型面收敛）；
    - ``information_gain_bits``：选择判据的期望信息增益（可审计：为什么是这
      问）。**可为负**：答案可能诚实地拓宽不确定性（分支把当前证据之外的
      类型引入活假设集）——决策敏感是问询的门，IG 只在敏感集内排序；
    - ``decision_sensitive``：恒 True（非决策敏感问在选择层已被过滤——携带
      该字段是让「为什么问了」在记录面自解释）。
    """

    question_id: str
    text: str
    branch_options: tuple[tuple[str, str], ...]  # (branch_key, label)
    information_gain_bits: float
    decision_sensitive: bool = True
    discriminates: tuple[str, ...] = ()  # 该问正在分离的竞争带类型（保序）

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "text": self.text,
            "branch_options": [{"key": key, "label": label} for key, label in self.branch_options],
            "information_gain_bits": round(self.information_gain_bits, 6),
            "decision_sensitive": self.decision_sensitive,
            "discriminates": list(self.discriminates),
        }


@dataclass(frozen=True)
class FrictionDiagnosis:
    """一次摩擦诊断判定（纯数据；schema version + 封闭 reason 码随行）。

    - ``outcome``：act / ask / no_action（封闭三值）；
    - ``friction_type``：FRICTION_TYPES 成员（unknown = 无正向证据——不假诊断）；
    - ``nominated_interventions``：act/best-guess 出口的 A-02 目录有序提名
      （unknown / no_action 恒空）；竞争带 runner-up 的提名按序垫后
      （错分类代价面：首要路径被守卫剔除时的确定性回退，不是第二诊断）；
    - ``suggested_clarifying_question``：提名含 ``clarify`` 时的问句载体
      （A-01 契约对 clarify 的强制参数；出自封闭问题库模板）；
    - ``uncertain``：best-guess / 低置信行动标注（A-01 ``insufficient_context``
      不确定类型的决策面镜像）；
    - ``evidence_refs``：既有 scheme（signal://<state_key>、
      user_state://<fact>）；utterance 只进 annotations（无合法 scheme，
      不伪造引用）。
    """

    schema_version: str = FRICTION_DIAGNOSIS_VERSION
    outcome: str = "no_action"
    friction_type: str = "unknown"
    runner_up: str | None = None
    confidence: float = 0.0
    margin: float = 0.0
    nominated_interventions: tuple[str, ...] = ()
    suggested_clarifying_question: str | None = None
    question: OneBestQuestion | None = None
    uncertain: bool = False
    budget_exhausted: bool = False
    uncertainty_kinds: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    posterior: tuple[tuple[str, float], ...] = ()
    evidence_scores: tuple[tuple[str, float], ...] = ()
    evidence_refs: tuple[str, ...] = ()
    annotations: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", MappingProxyType(dict(self.annotations)))

    @property
    def lifecycle_tag(self) -> str:
        """V3 细类 → lifecycle 粗族投影（A-05 scope 面 / D-05 切片喂入值）。"""
        return FRICTION_TYPE_TO_LIFECYCLE_TAG.get(self.friction_type, "unattributed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "outcome": self.outcome,
            "friction_type": self.friction_type,
            "lifecycle_tag": self.lifecycle_tag,
            "runner_up": self.runner_up,
            "confidence": round(self.confidence, 6),
            "margin": round(self.margin, 6),
            "nominated_interventions": list(self.nominated_interventions),
            "suggested_clarifying_question": self.suggested_clarifying_question,
            "question": None if self.question is None else self.question.to_dict(),
            "uncertain": self.uncertain,
            "budget_exhausted": self.budget_exhausted,
            "uncertainty_kinds": list(self.uncertainty_kinds),
            "reasons": list(self.reasons),
            "posterior": [[t, round(p, 6)] for t, p in self.posterior],
            "evidence_scores": [[t, round(s, 6)] for t, s in self.evidence_scores],
            "evidence_refs": list(self.evidence_refs),
            "annotations": dict(self.annotations),
        }

    def policy_factors_patch(self) -> dict[str, Any]:
        """A-02 衔接：并入 ``InterventionPolicyFactors.coerce`` 输入的最小 patch。

        调用方约定（与 A-04 ``JointFactorSources`` 的双提名通道并存）：本 patch
        的 ``nominated`` **前置**于既有提名（utterance+context 锚定的卡点证据
        是最新鲜的决策输入；L2 确定性模式命中仍可经 A-04 通道独立进入）。
        unknown / no_action 出口返回空 patch——上游无诊断时不改写下游提名。
        """
        if not self.nominated_interventions:
            return {}
        return {"nominated": self.nominated_interventions}

    def contract_annotations(self) -> dict[str, Any]:
        """A-01 契约 annotations 投影（决策溯源：卡点是什么、为何这么判）。"""
        payload: dict[str, Any] = {
            "friction_type": self.friction_type,
            "friction_confidence": round(self.confidence, 4),
            "friction_diagnosis_version": self.schema_version,
            "friction_uncertain": self.uncertain,
            "friction_reasons": list(self.reasons),
            "friction_lifecycle_tag": self.lifecycle_tag,
        }
        if self.question is not None:
            payload["friction_question_id"] = self.question.question_id
        return payload


# ---------------------------------------------------------------------------
# 规则核心（纯函数；确定性）
# ---------------------------------------------------------------------------


def _utterance_scores(text: str, notes: dict[str, Any]) -> dict[str, float]:
    """词牌证据（V3-FIX-110 否定感知）：命中 = 子串包含且**未被否定**。

    否定命中（同子句否定标记前置于词牌，V3-FIX-146 起按「最近后继词牌」
    作用域裁决）零证据权重，不进 ``utterance_matches``（FIX-49 词牌门的
    正向判据面），只入 ``utterance_negated_matches`` 注记（观察档可审计）。
    """
    scores: dict[str, float] = {}
    if not text:
        return scores
    matched: list[str] = []
    negated: list[str] = []
    clause_spans = _clause_spans(text)
    negated_spans = _negated_wordmark_spans(text, clause_spans, _wordmark_occurrences(text))
    for ftype in sorted(FRICTION_UTTERANCE_LEXICON):
        for phrase, weight in sorted(FRICTION_UTTERANCE_LEXICON[ftype].items()):
            if phrase not in text:
                continue
            if _utterance_wordmark_negated(text, phrase, negated_spans):
                negated.append(f"{ftype}:{phrase}")
                continue
            scores[ftype] = scores.get(ftype, 0.0) + weight
            matched.append(f"{ftype}:{phrase}")
    if matched:
        notes["utterance_matches"] = matched
    if negated:
        notes["utterance_negated_matches"] = negated
    return scores


def _state_scores(state_keys: frozenset[str], notes: dict[str, Any]) -> dict[str, float]:
    scores: dict[str, float] = {}
    recognized: list[str] = []
    unknown_keys: list[str] = []
    for key in sorted(state_keys):
        weights = SPINE_STATE_EVIDENCE.get(key)
        if weights is None:
            unknown_keys.append(key)
            continue
        recognized.append(key)
        for ftype in sorted(weights):
            scores[ftype] = scores.get(ftype, 0.0) + weights[ftype]
    if recognized:
        notes["matched_state_keys"] = recognized
    if unknown_keys:
        notes["ignored_state_keys"] = unknown_keys
    return scores


def _context_scores(inp: FrictionDiagnosisInput, notes: dict[str, Any]) -> dict[str, float]:
    scores: dict[str, float] = {}
    refs: list[str] = []
    if inp.days_since_progress is not None and inp.days_since_progress >= _DAYS_SINCE_PROGRESS_THRESHOLD:
        scores["entry"] = scores.get("entry", 0.0) + _DAYS_SINCE_PROGRESS_WEIGHT
        refs.append("user_state://days_since_progress")
    if inp.recent_failure_count is not None and inp.recent_failure_count >= _RECENT_FAILURE_THRESHOLD:
        for ftype in sorted(_RECENT_FAILURE_WEIGHTS):
            scores[ftype] = scores.get(ftype, 0.0) + _RECENT_FAILURE_WEIGHTS[ftype]
        refs.append("user_state://recent_failure_count")
    if inp.blocked_on_external is True:
        scores["dependency"] = scores.get("dependency", 0.0) + _BLOCKED_ON_EXTERNAL_WEIGHT
        refs.append("user_state://blocked_on_external")
    if inp.materials_available_unused is True:
        scores["knowledge"] = scores.get("knowledge", 0.0) + _MATERIALS_UNUSED_WEIGHT
        refs.append("user_state://materials_available_unused")
    if inp.has_active_goal is True and inp.has_task_context is False:
        scores["entry"] = scores.get("entry", 0.0) + _GOAL_WITHOUT_TASK_WEIGHT
        refs.append("user_state://goal_without_task_anchor")
    if refs:
        notes["context_refs"] = refs
    return scores


def _apply_branch_transform(scores: Mapping[str, float], branch: QuestionBranch) -> dict[str, float]:
    """分支变换（IG 假设与答案应用共用的唯一实现；不变量见 ANSWER_SEED_WEIGHT）：

    支持类型 → ``score × 2.0 + seed/|supports|``；**不在得分表的支持类型 →
    纯均摊种子**（零先验吸收修复）；不支持 → ``score × 0.35``。输入零分
    类型不进输出（后验只对正向质量定义）。
    """
    seed_per_type = ANSWER_SEED_WEIGHT / len(branch.supports) if branch.supports else 0.0
    transformed: dict[str, float] = {}
    for ftype, score in scores.items():
        if ftype in branch.supports:
            value = score * BRANCH_SUPPORT_MULTIPLIER + seed_per_type
        else:
            value = score * BRANCH_DECAY_MULTIPLIER
        if value > 0:
            transformed[ftype] = value
    for ftype in branch.supports:
        if ftype not in transformed and ftype in FRICTION_TYPES:
            transformed[ftype] = seed_per_type
    return transformed


def _apply_answer_branches(
    scores: dict[str, float],
    answered: tuple[tuple[str, str], ...],
    notes: dict[str, Any],
) -> dict[str, float]:
    """问→答闭环：已答分支按冻结变换重加权（与 IG 假设同一函数）。"""
    adjusted = dict(scores)
    applied: list[str] = []
    for question_id, branch_key in answered:
        spec = _QUESTION_BANK_INDEX.get(question_id)
        if spec is None:
            continue
        branch = next((b for b in spec.branches if b.key == branch_key), None)
        if branch is None:
            continue
        adjusted = _apply_branch_transform(adjusted, branch)
        applied.append(f"{question_id}:{branch_key}")
    if applied:
        notes["applied_answers"] = applied
    return adjusted


def _merge_scores(*score_maps: dict[str, float]) -> dict[str, float]:
    merged: dict[str, float] = {}
    for score_map in score_maps:
        for ftype, value in score_map.items():
            if value > 0:
                merged[ftype] = merged.get(ftype, 0.0) + value
    return merged


def _entropy(distribution: Mapping[str, float]) -> float:
    total = sum(distribution.values())
    if total <= 0:
        return 0.0
    entropy = 0.0
    for value in sorted(distribution):
        p = distribution[value] / total
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy


def _posterior_from_scores(scores: Mapping[str, float]) -> tuple[tuple[str, float], ...]:
    """得分 → 后验分布（V3-FIX-50③ 显式契约：类型按 ``(−score, type)`` 字典序
    输出——同输入同输出 bit-for-bit，并列按字母序破平，跨进程可复现）。"""
    positive = {t: s for t, s in scores.items() if s > 0}
    total = sum(positive.values())
    if total <= 0:
        return ()
    ordered = sorted(positive, key=lambda t: (-positive[t], t))
    return tuple((t, positive[t] / total) for t in ordered)


def _expected_entropy_after(
    posterior: tuple[tuple[str, float], ...], spec: QuestionSpec, scores: Mapping[str, float]
) -> float:
    """IG 的期望后验熵：Σ_b P(b)·H(P|b)。

    P(b)（用户落入分支的概率）取当前后验的支持类质量和；分支后验按
    ``_apply_branch_transform``（与答案应用同一函数）在**得分空间**重归一——
    选问的假设数学 = 闭环的应用数学，二者不可能分叉（同一实现）。
    """
    expected = 0.0
    for branch in spec.branches:
        p_branch = sum(p for t, p in posterior if t in branch.supports)
        if p_branch <= 0:
            continue
        branch_post = _apply_branch_transform(scores, branch)
        expected += p_branch * _entropy(branch_post)
    return expected


def _primary_nomination(friction_type: str) -> str | None:
    nominations = FRICTION_INTERVENTION_NOMINATIONS.get(friction_type) or ()
    return nominations[0] if nominations else None


def _argmax_type(scores: Mapping[str, float]) -> str | None:
    """得分 argmax（V3-FIX-50③ 显式契约：并列按 ``(−score, type)`` 字典序
    破平——字母序，跨进程可复现；消费方含问询决策敏感判定与 B1 出口）。"""
    positive = {t: s for t, s in scores.items() if s > 0}
    if not positive:
        return None
    return sorted(positive, key=lambda t: (-positive[t], t))[0]


def _flip_changes_primary(
    spec: QuestionSpec, posterior: tuple[tuple[str, float], ...], scores: Mapping[str, float]
) -> bool:
    """决策敏感的精确判据：存在**有概率发生**的分支，其变换后 argmax 的首要
    提名 ≠ 当前 argmax 首要提名。

    这是「问能否改变行动」（decision sensitivity）的封闭形式——不只看竞争带
    内部（带外类型经支持性答案的种子注入同样可能翻转 argmax）。P(branch)=0
    的分支不可能发生，不构成敏感性。
    """
    current_primary = _primary_nomination(posterior[0][0]) if posterior else None
    if current_primary is None:
        return False
    for branch in spec.branches:
        p_branch = sum(p for _t, p in posterior if _t in branch.supports)
        if p_branch <= 0:
            continue
        argmax = _argmax_type(_apply_branch_transform(scores, branch))
        if argmax is not None and _primary_nomination(argmax) != current_primary:
            return True
    return False


def _contender_band(posterior: tuple[tuple[str, float], ...]) -> tuple[str, ...]:
    """竞争带：后验 ≥ top 后验 50% 的类型（决策等价判定域）。"""
    if not posterior:
        return ()
    top_p = posterior[0][1]
    cutoff = top_p * CONTENDER_BAND_RATIO
    return tuple(t for t, p in posterior if p >= cutoff)


def _is_decision_sensitive(
    spec: QuestionSpec, posterior: tuple[tuple[str, float], ...], scores: Mapping[str, float]
) -> bool:
    """决策敏感（``_flip_changes_primary`` 的别名语义）：问可能改变行动才值得问。

    拆不动行动的问题不值得问（「不必要澄清受控」的 IG 前置过滤）。
    """
    return _flip_changes_primary(spec, posterior, scores)


def _select_question(
    posterior: tuple[tuple[str, float], ...],
    contenders: tuple[str, ...],
    answered_question_ids: frozenset[str],
    anchor: str | None,
    scores: Mapping[str, float] | None = None,
) -> OneBestQuestion | None:
    """One Best Question 选择：决策敏感过滤 → 最大期望信息增益 → 冻结优先级破平。

    已问过的问题不再选（一次问对；重复问同一问 = 问卷回潮的面源之一）。
    空后验（unknown）时不过 IG（无分布可算）——取冻结优先级最高的根分裂问。
    """
    candidates: list[tuple[float, int, QuestionSpec]] = []
    if posterior:
        baseline_entropy = _entropy(dict(posterior))
        for spec in FRICTION_QUESTION_BANK:
            if spec.question_id in answered_question_ids:
                continue
            if not _is_decision_sensitive(spec, posterior, scores or {}):
                continue
            # 决策敏感是**门**，IG 是**排序**——不以 IG>0 为入选条件：答案可能
            # 诚实地拓宽不确定性（分支把当前证据之外的类型引入活假设集，种子
            # 质量使期望熵上升），但只要存在可达行动翻转，问仍值得问（问的
            # 目的是选对行动，不是最小化不确定性）。负 IG 照常参与排序与审计。
            ig = baseline_entropy - _expected_entropy_after(posterior, spec, scores or {})
            candidates.append((-ig, spec.priority, spec))
    if not candidates and not posterior:
        for spec in FRICTION_QUESTION_BANK:
            if spec.question_id in answered_question_ids:
                continue
            candidates.append((0.0, spec.priority, spec))
    if not candidates:
        return None
    candidates.sort(key=lambda entry: (entry[0], entry[1]))
    _ig_neg, _prio, best = candidates[0]
    information_gain = -_ig_neg if posterior else 0.0
    return OneBestQuestion(
        question_id=best.question_id,
        text=best.render(anchor),
        branch_options=tuple((branch.key, branch.label) for branch in best.branches),
        information_gain_bits=information_gain,
        discriminates=contenders,
    )


#: V3-FIX-111 · answer_replay 自由文本回退的**置信面**（接线门的判据常量；
#: 判据语义与 FIX-49 出口门同构——「用户在回答」的前提需证据支持）：
#: - 命中词牌长度 ≥ ``FREE_TEXT_ANSWER_MIN_TERM_LENGTH`` 且覆盖比
#:   （命中字符数 / 归一消息长度，含标点）≥ ``FREE_TEXT_ANSWER_MIN_COVERAGE``
#:   → 置信回答；
#: - 整条消息 ≤ 1 字时的单字命中（「对」「慢」式直答）→ 置信；
#: - 其余（单字话语标记「对了」、长消息低覆盖词面擦碰）→ 低置信：调用方
#:   **不得 apply、不得 act**，pending 保持（可点选或改述）。
FREE_TEXT_ANSWER_MIN_TERM_LENGTH = 2
FREE_TEXT_ANSWER_MIN_COVERAGE = 0.25


@dataclass(frozen=True)
class AnswerResolution:
    """自由文本答案解析结果 + 词面证据强度（解析语义 = resolve_answer_branch 不变）。"""

    branch_key: str
    matched_term: str
    matched_length: int
    coverage: float
    confident: bool


def resolve_answer_branch_detail(question_id: str, answer_text: str) -> AnswerResolution | None:
    """``resolve_answer_branch`` 的证据面版本（同解析、附置信判定；FIX-111）。

    ``resolve_answer_branch`` 是本函数的键面投影（既有调用方/测试契约不变）。
    """
    spec = _QUESTION_BANK_INDEX.get(str(question_id).strip())
    if spec is None:
        return None
    text = _normalize_text(answer_text)
    if not text:
        return None
    best: tuple[int, int, str, str] | None = None  # (-词牌长, 分支序, 词牌, 分支键)
    for branch_index, branch in enumerate(spec.branches):
        for term in sorted(branch.match_terms):
            if term in text:
                candidate = (-len(term), branch_index, term, branch.key)
                if best is None or candidate < best:
                    best = candidate
    if best is None:
        return None
    matched_term, branch_key = best[2], best[3]
    coverage = len(matched_term) / len(text)
    if len(text) <= 1 and len(matched_term) == 1:
        confident = True
    else:
        confident = len(matched_term) >= FREE_TEXT_ANSWER_MIN_TERM_LENGTH and (
            coverage >= FREE_TEXT_ANSWER_MIN_COVERAGE
        )
    return AnswerResolution(
        branch_key=branch_key,
        matched_term=matched_term,
        matched_length=len(matched_term),
        coverage=coverage,
        confident=confident,
    )


def resolve_answer_branch(question_id: str, answer_text: str) -> str | None:
    """自由文本答案 → 分支键的规则优先解析（确定性第一层；模型面归 E-04）。

    解析纪律（v1_1 / FIX-43 P2 修订）：

    - **最长词牌命中优先**：全分支扫描收集全部 (分支, 命中词牌)，取**最长**
      命中词牌所属分支——正向词牌是负向词牌真子串时（「在等」⊂「不在等」、
      「想要」⊂「不想要」），短词牌的先行命中不再遮蔽长词牌（语义反转的
      算法面修复，词面除「不对」外零改动）；
    - 并列（跨分支同长）按分支声明序、再按词牌字典序破平——确定性；
    - 无命中 → None（调用方保持追问预算不变并走 best-guess，绝不猜分支
      ——与「UNKNOWN 不假诊断」同律）。

    生产主路径是 UI branch_key 直传（接线面 ``FrictionChatWiringService``），
    自由文本解析只服务无结构回退；两路共用 ``apply_question_answer`` 的
    (question_id, branch_key) 应用面。
    """
    resolution = resolve_answer_branch_detail(question_id, answer_text)
    return resolution.branch_key if resolution is not None else None


def apply_question_answer(
    diagnosis: FrictionDiagnosis,
    question_id: str,
    branch_key: str,
    *,
    questions_asked_session: int = 1,
    questions_asked_day: int = 1,
    clarification_preference: str | None = None,
    extra_input: Mapping[str, Any] | None = None,
) -> FrictionDiagnosis:
    """问→答闭环：把已答分支累积进证据并重放诊断（一次问对的机制出口）。

    答案以 (question_id, branch_key) 携带于 ``answered_branches`` 重放——
    诊断是输入的纯函数，闭环不引入第二状态源。预算计数由调用方递增后传入
    （该问本身已消耗 1 问预算）。``extra_input``：等待答案期间新装配到的
    平面事实（如 goal/task 锚点、行为计数）——显式并入重放输入，保持纯度。
    """
    source_input = dict(diagnosis.annotations.get("input_snapshot") or {})
    answered = list(source_input.get("answered_branches") or [])
    answered.append([question_id, branch_key])
    source_input["answered_branches"] = answered
    source_input["questions_asked_session"] = questions_asked_session
    source_input["questions_asked_day"] = questions_asked_day
    if clarification_preference is not None:
        source_input["clarification_preference"] = clarification_preference
    if extra_input:
        for key, value in dict(extra_input).items():
            if key not in ("answered_branches",):
                source_input[key] = value
    return diagnose_friction(source_input)


def _question_budget(inp: FrictionDiagnosisInput) -> tuple[int, int, bool]:
    """有效预算（session, day, exhausted)。A-05 clarification 偏好在此收效。"""
    session_limit, day_limit = DEFAULT_SESSION_QUESTION_LIMIT, DEFAULT_DAY_QUESTION_LIMIT
    if inp.clarification_preference in CLARIFICATION_PREFERENCE_BUDGETS:
        session_limit, day_limit = CLARIFICATION_PREFERENCE_BUDGETS[inp.clarification_preference]
    exhausted = inp.questions_asked_session >= session_limit or inp.questions_asked_day >= day_limit
    return session_limit, day_limit, exhausted


def _build_diagnosis(
    inp: FrictionDiagnosisInput,
    scores: dict[str, float],
    posterior: tuple[tuple[str, float], ...],
    notes: dict[str, Any],
    budget_exhausted: bool,
) -> FrictionDiagnosis:
    """后验 → 出口裁决（置信/决策等价/问询/预算四路的确定性阶梯）。"""
    reasons: list[str] = []
    evidence_refs: list[str] = [f"signal://{key}" for key in notes.get("matched_state_keys", [])]
    evidence_refs.extend(notes.get("context_refs", []))

    # 无正向证据 → unknown（不假诊断）：预算内问根分裂问；超限 no_action。
    if not posterior:
        if budget_exhausted:
            return FrictionDiagnosis(
                outcome="no_action",
                friction_type="unknown",
                reasons=("B2.budget_exhausted_unknown_no_action",),
                uncertainty_kinds=("insufficient_context",),
                budget_exhausted=True,
                evidence_refs=tuple(dict.fromkeys(evidence_refs)),
                annotations={**notes, "input_snapshot": _input_snapshot(inp)},
            )
        question = _select_question((), (), frozenset(q for q, _b in inp.answered_branches), inp.task_anchor)
        reasons.append("U1.unknown_ask_entry_question")
        return FrictionDiagnosis(
            outcome="ask" if question is not None else "no_action",
            friction_type="unknown",
            question=question,
            reasons=tuple(reasons if question is not None else ["B2.budget_exhausted_unknown_no_action"]),
            uncertainty_kinds=("insufficient_context",),
            budget_exhausted=False,
            evidence_refs=tuple(dict.fromkeys(evidence_refs)),
            annotations={**notes, "input_snapshot": _input_snapshot(inp)},
        )

    top_type, top_p = posterior[0]
    runner_up = posterior[1][0] if len(posterior) > 1 else None
    runner_up_p = posterior[1][1] if len(posterior) > 1 else 0.0
    margin = top_p - runner_up_p
    contenders = _contender_band(posterior)

    # 充分路 1：置信充分（含问后收敛——answered_branches 非空即 S3 标注）。
    sufficient_confidence = top_p >= SUFFICIENCY_MIN_CONFIDENCE and margin >= SUFFICIENCY_MIN_MARGIN

    def _act(reason: str, *, uncertain: bool) -> FrictionDiagnosis:
        nominations = list(FRICTION_INTERVENTION_NOMINATIONS.get(top_type) or ())
        # 错分类代价面：竞争带 runner-up 的提名按序垫后（首要路径被 A-02 守卫
        # 剔除时的确定性回退——不是第二诊断，只是回退面）。
        for contender in contenders:
            if contender == top_type:
                continue
            for nomination in FRICTION_INTERVENTION_NOMINATIONS.get(contender) or ():
                if nomination not in nominations:
                    nominations.append(nomination)
        suggested: str | None = None
        if "clarify" in nominations:
            clarity_spec = _QUESTION_BANK_INDEX["q_standard_clarity"]
            suggested = clarity_spec.render(inp.task_anchor)
        uncertainty_kinds = ("insufficient_context",) if uncertain else ()
        return FrictionDiagnosis(
            outcome="act",
            friction_type=top_type,
            runner_up=runner_up,
            confidence=top_p,
            margin=margin,
            nominated_interventions=tuple(nominations),
            suggested_clarifying_question=suggested,
            uncertain=uncertain,
            uncertainty_kinds=uncertainty_kinds,
            reasons=(reason,),
            posterior=posterior,
            evidence_scores=tuple(sorted(scores.items())),
            evidence_refs=tuple(dict.fromkeys(evidence_refs)),
            annotations={**notes, "contenders": list(contenders), "input_snapshot": _input_snapshot(inp)},
        )

    if sufficient_confidence:
        if inp.answered_branches:
            return _act("S3.sufficient_after_question", uncertain=False)
        return _act("S1.sufficient_confidence", uncertain=False)

    # 充分路 2 与问询路的统一判据：**问能否改变行动**（decision sensitivity
    # 的封闭形式，见 ``_flip_changes_primary``）——没有任何有概率发生的分支
    # 能翻转 argmax 首要提名时，问是纯官僚，不问：
    # - 竞争带内首要提名一致（S2，可解释的常见形态）：行动有据，非不确定；
    # - 带内也不一致但无可达翻转（Q2）：真歧义且问询无用 → argmax + 不确定标注。
    answered_ids = frozenset(q for q, _b in inp.answered_branches)
    question = _select_question(posterior, contenders, answered_ids, inp.task_anchor, scores=scores)
    if question is None:
        contender_primaries = {_primary_nomination(t) for t in contenders}
        band_coincides = len(contenders) > 1 and None not in contender_primaries and len(contender_primaries) == 1
        if band_coincides:
            return _act("S2.sufficient_decision_equivalence", uncertain=False)
        return _act("Q2.no_discriminative_question_act_argmax", uncertain=True)

    # 不足路：预算超限 → best-guess（argmax + 不确定标注；有证据故可猜）。
    # V3-FIX-50①：exact tie（领先幅度无区分度）不在此列——宽分支答案种子均摊
    # 造成的平权（如 q_direction_vs_push.cant_push 10 类支持 × 零行为事实）下
    # argmax 是字母序偶然，按它行动必然产生「纠正逐类试错环」（A-08 p06/p02
    # 反例）。降级 no_action + insufficient_context（B2「不假诊断」同律）。
    if budget_exhausted:
        if margin <= TIE_DISCRIMINATION_EPSILON:
            return FrictionDiagnosis(
                outcome="no_action",
                friction_type=top_type,
                runner_up=runner_up,
                confidence=top_p,
                margin=margin,
                nominated_interventions=(),
                uncertain=True,
                budget_exhausted=True,
                uncertainty_kinds=("insufficient_context",),
                reasons=("B3.budget_exhausted_tie_no_action",),
                posterior=posterior,
                evidence_scores=tuple(sorted(scores.items())),
                evidence_refs=tuple(dict.fromkeys(evidence_refs)),
                annotations={
                    **notes,
                    "contenders": list(contenders),
                    "tie_degraded": True,
                    "input_snapshot": _input_snapshot(inp),
                },
            )
        return replace(
            _act("B1.budget_exhausted_best_guess", uncertain=True),
            budget_exhausted=True,
        )

    # 不足路：预算内 → One Best Question（最大期望信息增益 × 决策敏感）。
    return FrictionDiagnosis(
        outcome="ask",
        friction_type=top_type,
        runner_up=runner_up,
        confidence=top_p,
        margin=margin,
        question=question,
        uncertainty_kinds=("insufficient_context",),
        reasons=("Q1.insufficient_ask_best_question",),
        posterior=posterior,
        evidence_scores=tuple(sorted(scores.items())),
        evidence_refs=tuple(dict.fromkeys(evidence_refs)),
        annotations={**notes, "contenders": list(contenders), "input_snapshot": _input_snapshot(inp)},
    )


def _input_snapshot(inp: FrictionDiagnosisInput) -> dict[str, Any]:
    """闭环节点的输入快照（apply_question_answer 重放源；只携可序列化平面值）。"""
    return {
        "utterance": inp.utterance,
        "spine_state_keys": sorted(inp.spine_state_keys),
        "task_anchor": inp.task_anchor,
        "days_since_progress": inp.days_since_progress,
        "recent_failure_count": inp.recent_failure_count,
        "blocked_on_external": inp.blocked_on_external,
        "materials_available_unused": inp.materials_available_unused,
        "has_active_goal": inp.has_active_goal,
        "has_task_context": inp.has_task_context,
        "answered_branches": [list(pair) for pair in inp.answered_branches],
        "questions_asked_session": inp.questions_asked_session,
        "questions_asked_day": inp.questions_asked_day,
        "clarification_preference": inp.clarification_preference,
    }


def diagnose_friction(
    factors: FrictionDiagnosisInput | Mapping[str, Any] | None,
) -> FrictionDiagnosis:
    """摩擦诊断决策核心：输入投影 → {分类, 充分性裁决, 提名/单问}。

    纯函数：同步、确定性、无 IO；任何输入不 raise——内部异常降级
    ``no_action`` + ``E1.degraded_to_conservative``（韧性契约）。
    """
    try:
        inp = FrictionDiagnosisInput.coerce(factors)
        notes: dict[str, Any] = {}
        scores = _merge_scores(
            _utterance_scores(inp.utterance, notes),
            _state_scores(inp.spine_state_keys, notes),
            _context_scores(inp, notes),
        )
        scores = _apply_answer_branches(scores, inp.answered_branches, notes)
        posterior = _posterior_from_scores(scores)
        _session_limit, _day_limit, exhausted = _question_budget(inp)
        if exhausted:
            notes["budget"] = {
                "session_limit": _session_limit,
                "day_limit": _day_limit,
                "asked_session": inp.questions_asked_session,
                "asked_day": inp.questions_asked_day,
            }
        return _build_diagnosis(inp, scores, posterior, notes, exhausted)
    except Exception as exc:  # noqa: BLE001 — resilience contract
        logger.warning("Friction diagnosis internal error, degrading to no_action+log: {}", exc)
        return FrictionDiagnosis(
            outcome="no_action",
            friction_type="unknown",
            reasons=("E1.degraded_to_conservative",),
            uncertainty_kinds=("insufficient_context",),
            annotations={"degraded": True},
        )


# ---------------------------------------------------------------------------
# 指纹（词表/证据面/问题库的 sha256——测试双钉用）
# ---------------------------------------------------------------------------


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def friction_taxonomy_fingerprint() -> str:
    """分类学 + 提名表 + lifecycle 投影的指纹。"""
    payload = {
        "types": sorted(FRICTION_TYPES),
        "nominations": {k: list(v) for k, v in sorted(FRICTION_INTERVENTION_NOMINATIONS.items())},
        "lifecycle": dict(sorted(FRICTION_TYPE_TO_LIFECYCLE_TAG.items())),
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def friction_evidence_fingerprint() -> str:
    """证据面（词牌 + spine 投影 + context 规则参数）的指纹。"""
    payload = {
        "utterance_lexicon": {k: dict(sorted(v.items())) for k, v in sorted(FRICTION_UTTERANCE_LEXICON.items())},
        "spine_state_evidence": {k: dict(sorted(v.items())) for k, v in sorted(SPINE_STATE_EVIDENCE.items())},
        "context_rules": {
            "days_since_progress_threshold": _DAYS_SINCE_PROGRESS_THRESHOLD,
            "days_since_progress_weight": _DAYS_SINCE_PROGRESS_WEIGHT,
            "recent_failure_threshold": _RECENT_FAILURE_THRESHOLD,
            "recent_failure_weights": dict(sorted(_RECENT_FAILURE_WEIGHTS.items())),
            "blocked_on_external_weight": _BLOCKED_ON_EXTERNAL_WEIGHT,
            "materials_unused_weight": _MATERIALS_UNUSED_WEIGHT,
            "goal_without_task_weight": _GOAL_WITHOUT_TASK_WEIGHT,
        },
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def friction_question_bank_fingerprint() -> str:
    """问题库（含分支支持集与答句词牌）的指纹。"""
    payload = [
        {
            "question_id": spec.question_id,
            "text_template": spec.text_template,
            "priority": spec.priority,
            "branches": [
                {
                    "key": branch.key,
                    "label": branch.label,
                    "supports": sorted(branch.supports),
                    "match_terms": sorted(branch.match_terms),
                }
                for branch in spec.branches
            ],
        }
        for spec in FRICTION_QUESTION_BANK
    ]
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def friction_sufficiency_fingerprint() -> str:
    """充分性/预算参数的指纹。"""
    payload = {
        "min_confidence": SUFFICIENCY_MIN_CONFIDENCE,
        "min_margin": SUFFICIENCY_MIN_MARGIN,
        "contender_band_ratio": CONTENDER_BAND_RATIO,
        "branch_support_multiplier": BRANCH_SUPPORT_MULTIPLIER,
        "branch_decay_multiplier": BRANCH_DECAY_MULTIPLIER,
        "answer_seed_weight": ANSWER_SEED_WEIGHT,
        "tie_discrimination_epsilon": TIE_DISCRIMINATION_EPSILON,
        "default_session_limit": DEFAULT_SESSION_QUESTION_LIMIT,
        "default_day_limit": DEFAULT_DAY_QUESTION_LIMIT,
        "preference_budgets": dict(sorted(CLARIFICATION_PREFERENCE_BUDGETS.items())),
        "reasons": sorted(FRICTION_DIAGNOSIS_REASONS),
        "outcomes": sorted(FRICTION_OUTCOMES),
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
