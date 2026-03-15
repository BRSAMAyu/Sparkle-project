from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.agents.graph.nodes.deep_analyst import deep_analyst_node
from app.agents.graph.nodes.error_analyst import error_analyst_node
from app.agents.graph.nodes.exam_oracle import exam_oracle_node
from app.agents.graph.nodes.expert_node_factory import create_specialist_node
from app.agents.graph.nodes.galaxy_guide import galaxy_guide_node
from app.agents.graph.nodes.registry_tools import create_task, query_knowledge
from app.agents.graph.nodes.study_buddy import study_buddy_node
from app.agents.graph.nodes.time_tutor import time_tutor_node
from app.agents.graph.state import SparkleState


@dataclass(frozen=True)
class GraphExpertSpec:
    expert_id: str
    node_name: str
    node_handler: Callable[[SparkleState], dict]
    aliases: tuple[str, ...] = ()
    default_rank: int = 100
    supports_collaboration: bool = True


_math_node = create_specialist_node(
    agent_id="math_agent",
    planning_prompt=(
        "你是数学专家（规划模式）。\n"
        "## 思维框架\n"
        "先识别题型与核心方法，再判断前置概念是否缺失，最后拆成可练习的子任务。\n"
        "## 规划输出\n"
        "必须用 tool calls 生成计划或检索知识，避免直接给最终答案。"
    ),
    system_prompt=(
        "你是数学专家，擅长把问题拆成清晰的数学结构与解题路径。\n"
        "## 思维框架\n"
        "先判断题型/概念，再给关键方法或公式，再指出易错点或常见误区。\n"
        "## 输出格式\n"
        "1. 核心判断（1 句）\n"
        "2. 2-3 个关键论点或步骤（含简要依据）\n"
        "3. 1 条可执行建议或练习方向\n"
        "## 个性化适配\n"
        "若上文包含用户偏好或难度提示，请据此调整术语密度与解释深度。"
    ),
    task_prompt_prefix="Math expert context",
    toolset=[query_knowledge, create_task],
)

_code_node = create_specialist_node(
    agent_id="code_agent",
    planning_prompt=(
        "你是编程专家（规划模式）。\n"
        "## 思维框架\n"
        "先明确需求/约束，再选择技术栈与方案，再拆分成可实现的任务与验证点。\n"
        "## 规划输出\n"
        "必须用 tool calls 生成计划或检索参考，不要直接输出最终代码。"
    ),
    system_prompt=(
        "你是编程专家，擅长把问题映射到清晰的工程方案与实现步骤。\n"
        "## 思维框架\n"
        "先澄清需求与约束，再给出结构化方案，最后给出关键实现要点或风险。\n"
        "## 输出格式\n"
        "1. 核心判断（1 句）\n"
        "2. 2-3 个要点（含简要理由）\n"
        "3. 1 条可执行建议或实现提示\n"
        "## 个性化适配\n"
        "若上文包含用户偏好或难度提示，请据此调整复杂度与解释深度。"
    ),
    task_prompt_prefix="Code expert context",
    toolset=[query_knowledge, create_task],
)

_writing_node = create_specialist_node(
    agent_id="writing_agent",
    planning_prompt=(
        "你是写作专家（规划模式）。\n"
        "## 思维框架\n"
        "先明确受众与目的，再规划结构与论点，最后拆分成写作练习任务。\n"
        "## 规划输出\n"
        "必须用 tool calls 生成计划或任务，不要直接给最终成稿。"
    ),
    system_prompt=(
        "你是写作专家，擅长帮助用户组织结构、语气与表达策略。\n"
        "## 思维框架\n"
        "先确认受众与目的，再给结构框架与关键表达建议。\n"
        "## 输出格式\n"
        "1. 核心判断（1 句）\n"
        "2. 2-3 条写作要点（含示例方向）\n"
        "3. 1 条可执行建议或练习提示\n"
        "## 个性化适配\n"
        "若上文包含用户偏好或难度提示，请据此调整语气与细节程度。"
    ),
    task_prompt_prefix="Writing expert context",
    toolset=[create_task],
)

_science_node = create_specialist_node(
    agent_id="science_agent",
    planning_prompt=(
        "你是理科专家（规划模式）。\n"
        "## 思维框架\n"
        "先界定现象/概念，再列出关键机制与证据来源，最后拆成学习任务。\n"
        "## 规划输出\n"
        "必须用 tool calls 检索证据或生成任务，不要直接给最终答案。"
    ),
    system_prompt=(
        "你是理科专家，擅长用机制解释与证据支持结论。\n"
        "## 思维框架\n"
        "先给出机制或原理，再补充关键证据或例子。\n"
        "## 输出格式\n"
        "1. 核心判断（1 句）\n"
        "2. 2-3 个关键机制/证据点\n"
        "3. 1 条可执行建议或练习方向\n"
        "## 个性化适配\n"
        "若上文包含用户偏好或难度提示，请据此调整术语密度与解释深度。"
    ),
    task_prompt_prefix="Science expert context",
    toolset=[query_knowledge, create_task],
)

_search_node = create_specialist_node(
    agent_id="search_agent",
    planning_prompt=(
        "你是搜索专家（规划模式）。\n"
        "## 思维框架\n"
        "先确认需要的证据类型，再检索可信来源，最后整理成可引用的要点。\n"
        "## 规划输出\n"
        "必须用 tool calls 检索证据，不要直接给最终答案。"
    ),
    system_prompt=(
        "你是搜索专家，擅长高效检索并提炼可信证据。\n"
        "## 思维框架\n"
        "先明确检索目标，再给出证据要点与来源线索。\n"
        "## 输出格式\n"
        "1. 核心判断（1 句）\n"
        "2. 2-3 条证据要点（尽量指向来源）\n"
        "3. 1 条可执行建议或下一步检索方向\n"
        "## 个性化适配\n"
        "若上文包含用户偏好或难度提示，请据此调整信息密度。"
    ),
    task_prompt_prefix="Search expert context",
    toolset=[query_knowledge],
)


GRAPH_EXPERT_SPECS: tuple[GraphExpertSpec, ...] = (
    GraphExpertSpec("galaxy_guide", "galaxy_guide", galaxy_guide_node, aliases=("knowledge_agent",), default_rank=10),
    GraphExpertSpec("exam_oracle", "exam_oracle", exam_oracle_node, default_rank=20),
    GraphExpertSpec("time_tutor", "time_tutor", time_tutor_node, default_rank=30),
    GraphExpertSpec("deep_analyst", "deep_analyst", deep_analyst_node, default_rank=40),
    GraphExpertSpec("error_analyst", "error_analyst", error_analyst_node, default_rank=50),
    GraphExpertSpec("study_buddy", "study_buddy", study_buddy_node, aliases=("general_chat",), default_rank=60),
    GraphExpertSpec("math_agent", "math_agent", _math_node, aliases=("math",), default_rank=70),
    GraphExpertSpec("code_agent", "code_agent", _code_node, aliases=("code",), default_rank=80),
    GraphExpertSpec("writing_agent", "writing_agent", _writing_node, aliases=("writing",), default_rank=90),
    GraphExpertSpec("science_agent", "science_agent", _science_node, aliases=("science",), default_rank=100),
    GraphExpertSpec("search_agent", "search_agent", _search_node, aliases=("search",), default_rank=110),
)


def get_graph_expert_specs() -> tuple[GraphExpertSpec, ...]:
    return GRAPH_EXPERT_SPECS


def get_graph_routable_targets() -> tuple[str, ...]:
    targets: list[str] = []
    for spec in GRAPH_EXPERT_SPECS:
        targets.append(spec.node_name)
        targets.extend(spec.aliases)
    targets.extend(["human_assist"])
    return tuple(dict.fromkeys(targets))


def resolve_node_name(target: str | None) -> str | None:
    if not target:
        return None
    target_norm = target.strip().lower()
    for spec in GRAPH_EXPERT_SPECS:
        if target_norm == spec.node_name:
            return spec.node_name
        if target_norm == spec.expert_id:
            return spec.node_name
        if target_norm in spec.aliases:
            return spec.node_name
    return None


def get_node_function(target: str | None):
    resolved = resolve_node_name(target)
    if not resolved:
        return None
    for spec in GRAPH_EXPERT_SPECS:
        if spec.node_name == resolved:
            return spec.node_handler
    return None
