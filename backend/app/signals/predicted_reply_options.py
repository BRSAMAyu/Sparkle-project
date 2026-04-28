"""
Core: execution
Phase: clarify→plan
Stage: Signal-to-Action Spine P1-3 PredictedReplyOption Engine

预测回答选项引擎 — 为 Aurora 确认问题生成语义快捷回答。

核心原则：
- 不是表单选择器，是建模问题的语义快捷回答
- 每组选项必须包含"都不对，我解释一下"
- 每个选项带语义值和状态补丁效果
- 4 类选项：事实确认 / 假设确认 / 策略选择 / 关系边界
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.signals.types import ActionableSignal, _uid


@dataclass
class PredictedReplyOption:
    """单个预测回答选项。"""
    option_id: str
    label: str                       # 用户看到的文字
    semantic_value: str              # 语义标识
    confidence: float                # 系统预估这个答案的概率
    is_disconfirming: bool           # 是否反驳系统假设
    is_freeform: bool                # 是否是自由输入
    state_patch: dict[str, Any]      # 选择后的状态补丁
    telemetry_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "option_id": self.option_id,
            "label": self.label,
            "semantic_value": self.semantic_value,
            "confidence": self.confidence,
            "is_disconfirming": self.is_disconfirming,
            "is_freeform": self.is_freeform,
            "state_patch": self.state_patch,
            "telemetry_id": self.telemetry_id,
        }


@dataclass
class PredictedReplyQuestion:
    """一组预测回答选项。"""
    question_id: str
    question_type: str               # "fact_confirm" | "hypothesis_confirm" | "strategy_choice" | "relationship"
    prompt_text: str                 # Aurora 的问题文本
    state_key: str                   # 关联的状态键
    options: list[PredictedReplyOption]
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "question_type": self.question_type,
            "prompt_text": self.prompt_text,
            "state_key": self.state_key,
            "options": [o.to_dict() for o in self.options],
        }


# ── 固定选项模板 ──────────────────────────────────────────────────
# 按 state_key 映射到标准问题模板。

_QUESTION_TEMPLATES: dict[str, dict[str, Any]] = {
    "task_granularity_fit": {
        "question_type": "hypothesis_confirm",
        "prompt_template": "我目前判断：任务可能排大了。依据是最近两张任务都明显超时。但这也可能只是你这两天临时忙。你觉得更接近哪种？",
        "state_key": "task_granularity_fit",
        "options": [
            {
                "label": "确实排大了",
                "semantic_value": "task_too_large",
                "confidence": 0.42,
                "is_disconfirming": False,
                "state_patch": {"task_granularity_fit": "too_large"},
            },
            {
                "label": "只是今天临时忙",
                "semantic_value": "temporary_time_conflict",
                "confidence": 0.26,
                "is_disconfirming": True,
                "state_patch": {"task_granularity_fit": "unknown", "situation_constraint": "temporary_busy"},
            },
            {
                "label": "不是任务大，是我不会做",
                "semantic_value": "knowledge_blocker",
                "confidence": 0.22,
                "is_disconfirming": True,
                "state_patch": {"knowledge_bottleneck": "stronger"},
            },
        ],
    },
    "knowledge_transfer": {
        "question_type": "hypothesis_confirm",
        "prompt_template": "我发现你在同一个知识点上连续出错了。我判断是概念迁移还没建立起来。对吗？",
        "state_key": "knowledge_transfer",
        "options": [
            {
                "label": "对，我做题时总搞混",
                "semantic_value": "concept_confusion",
                "confidence": 0.45,
                "is_disconfirming": False,
                "state_patch": {"transfer_failure": "confirmed"},
            },
            {
                "label": "不是不会，是粗心了",
                "semantic_value": "carelessness",
                "confidence": 0.20,
                "is_disconfirming": True,
                "state_patch": {"transfer_failure": "not_confirmed", "mistake_type": "careless"},
            },
            {
                "label": "题目本身有歧义",
                "semantic_value": "ambiguous_question",
                "confidence": 0.15,
                "is_disconfirming": True,
                "state_patch": {"transfer_failure": "not_confirmed", "mistake_type": "ambiguous"},
            },
        ],
    },
    "material_utilization": {
        "question_type": "strategy_choice",
        "prompt_template": "你上传的课件最近几轮没有被用到。要按课件内容回答吗？",
        "state_key": "material_utilization",
        "options": [
            {
                "label": "按课件讲",
                "semantic_value": "use_material",
                "confidence": 0.50,
                "is_disconfirming": False,
                "state_patch": {"retrieval_mode": "targeted_source_rag"},
            },
            {
                "label": "不用课件也行",
                "semantic_value": "skip_material",
                "confidence": 0.25,
                "is_disconfirming": True,
                "state_patch": {"retrieval_mode": "graph_only"},
            },
        ],
    },
    "goal_mode": {
        "question_type": "fact_confirm",
        "prompt_template": "我判断你现在是考试抢救模式。你的目标是先过线还是冲高分？",
        "state_key": "goal_mode",
        "options": [
            {
                "label": "我只想先过线",
                "semantic_value": "minimum_pass",
                "confidence": 0.50,
                "is_disconfirming": False,
                "state_patch": {"path_mode": "minimum_pass"},
            },
            {
                "label": "我想冲高分",
                "semantic_value": "high_score",
                "confidence": 0.20,
                "is_disconfirming": False,
                "state_patch": {"path_mode": "high_score"},
            },
            {
                "label": "我想扎实学",
                "semantic_value": "deep_mastery",
                "confidence": 0.15,
                "is_disconfirming": True,
                "state_patch": {"path_mode": "solid_pass"},
            },
        ],
    },
}

# 必须追加到每组选项末尾
_FREEFORM_OPTION = {
    "label": "都不对，我解释一下",
    "semantic_value": "freeform_correction",
    "confidence": 0.10,
    "is_disconfirming": True,
    "is_freeform": True,
    "state_patch": {"open_free_input": True},
}


class SpineReplyOptionEngine:
    """
    P1-3: Spine 管线专用的预测回答选项引擎。

    与 aurora/predicted_reply_engine.py 的 PredictedReplyOptionEngine 不同，
    本引擎面向 Signal-to-Action Spine 的 ActionableSignal 生成语义快捷回答。

    核心原则：
    - 每组选项必须包含"都不对，我解释一下"
    - 选项带语义值和状态补丁效果
    - 选项不是表单，是建模快捷方式
    """

    def generate_options(
        self,
        signal: ActionableSignal,
    ) -> PredictedReplyQuestion | None:
        """
        根据信号生成预测回答选项。

        Returns:
            PredictedReplyQuestion if template exists, None otherwise.
        """
        template = _QUESTION_TEMPLATES.get(signal.state_key)
        if not template:
            logger.debug("no reply option template for state_key={}", signal.state_key)
            return None

        options: list[PredictedReplyOption] = []

        for i, opt_data in enumerate(template["options"]):
            opt = PredictedReplyOption(
                option_id=_uid(f"opt_{i}"),
                label=opt_data["label"],
                semantic_value=opt_data["semantic_value"],
                confidence=opt_data["confidence"],
                is_disconfirming=opt_data["is_disconfirming"],
                is_freeform=False,
                state_patch=dict(opt_data["state_patch"]),
                telemetry_id=f"opt_{signal.signal_id}_{i}",
            )
            options.append(opt)

        # 追加自由输入选项（必须）
        freeform = PredictedReplyOption(
            option_id=_uid("opt_free"),
            label=_FREEFORM_OPTION["label"],
            semantic_value=_FREEFORM_OPTION["semantic_value"],
            confidence=_FREEFORM_OPTION["confidence"],
            is_disconfirming=True,
            is_freeform=True,
            state_patch=dict(_FREEFORM_OPTION["state_patch"]),
            telemetry_id=f"opt_{signal.signal_id}_free",
        )
        options.append(freeform)

        question = PredictedReplyQuestion(
            question_id=_uid("q"),
            question_type=template["question_type"],
            prompt_text=template["prompt_template"],
            state_key=template["state_key"],
            options=options,
        )

        logger.info(
            "PredictedReplyQuestion: id={} type={} state_key={} options={}",
            question.question_id, question.question_type,
            question.state_key, len(options),
        )

        return question

    def process_user_selection(
        self,
        question: PredictedReplyQuestion,
        selected_option_id: str,
        freeform_text: str | None = None,
    ) -> dict[str, str]:
        """
        处理用户选择，返回状态补丁。

        Args:
            question: 问题对象
            selected_option_id: 用户选择的选项 ID
            freeform_text: 如果用户选择了自由输入，这里是对应的文本

        Returns:
            State patch dict to apply.
        """
        for opt in question.options:
            if opt.option_id == selected_option_id:
                patch = dict(opt.state_patch)
                if opt.is_freeform and freeform_text:
                    patch["freeform_text"] = freeform_text
                logger.info(
                    "User selected: option={} semantic={} patch={}",
                    opt.label, opt.semantic_value, patch,
                )
                return patch

        logger.warning("Selected option not found: {}", selected_option_id)
        return {}
