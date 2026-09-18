from __future__ import annotations

import json
import math
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, NAMESPACE_URL, uuid4, uuid5

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.user_preferences import UserPreferencesCenter
from app.scenario_packs.exam_prep_14d import EXAM_PREP_14D_MANIFEST_PATH, EXAM_PREP_14D_PACK_ID
from app.schemas.exam_sprint import (
    DiagnoseConfidence,
    DiagnoseQuestionType,
    DiagnosticBottleneck,
    DiagnosticGenerateRequest,
    DiagnosticGenerateResponse,
    DiagnosticGradeRequest,
    DiagnosticGradeResponse,
    DiagnosticKnowledgeNode,
    DiagnosticMasteryUpdate,
    DiagnosticQuestionGrader,
    DiagnosticQuestionPrompt,
    RecommendedPath,
)
from app.services.galaxy_service import GalaxyService
from app.services.profile_write_service import ProfileWriteService
from app.sprint_packs.sprint_pack_registry import PACKS_DIR
from app.core.cache import cache_service


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# P1-E3: diagnostic topics -> galaxy node resolution
#
# Diagnostic question templates link to topic slugs (e.g. ``ip_subnetting``).
# When no galaxy ``KnowledgeNode`` shares the topic name, mastery updates used
# to be silently dropped. We now resolve each topic to a canonical sprint-pack
# node id (created on demand by GalaxyService) so ``update_galaxy=True`` always
# lands in the knowledge graph.
# ---------------------------------------------------------------------------

# Curated topic slug -> sprint-pack node id for slugs whose name does not match
# a pack node suffix. Values must exist in app/sprint_packs/*_v1.json.
_DIAG_TOPIC_NODE_ALIASES: dict[str, str] = {
    "layering_protocol_stack": "cn.protocol_stack_concepts",
    "ip_subnetting": "cn.subnetting",
    "http_dns": "cn.http",
    "link_layer_basics": "cn.error_detection",
}

_DIAGNOSTIC_TOPIC_NODE_NAMESPACE = uuid5(NAMESPACE_URL, "sparkle:diagnostic-topic-node")

_pack_node_suffix_index_cache: dict[str, str] | None = None


def _pack_node_suffix_index() -> dict[str, str]:
    """Map ``<prefix>.<suffix>`` sprint-pack node ids by their unique suffix."""
    global _pack_node_suffix_index_cache
    if _pack_node_suffix_index_cache is not None:
        return _pack_node_suffix_index_cache
    index: dict[str, str] = {}
    for path in sorted(PACKS_DIR.glob("*_v1.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.debug("diagnostic topic resolver: failed to read pack {}: {}", path, exc)
            continue
        for node in payload.get("knowledge_nodes") or []:
            node_id = str(node.get("node_id") or "").strip()
            if not node_id or "." not in node_id:
                continue
            suffix = node_id.split(".", 1)[1]
            index.setdefault(suffix, node_id)
    _pack_node_suffix_index_cache = index
    return index


def _diagnostic_topic_node_uuid(slug: str) -> UUID:
    """Deterministic galaxy node id for diagnostic topics without a pack node."""
    return uuid5(_DIAGNOSTIC_TOPIC_NODE_NAMESPACE, slug.strip())


# ---------------------------------------------------------------------------
# P1-E4: server-side grading sessions
#
# ``/diagnose/generate`` used to ship grading_payload (answer keys) to the
# client so that ``/diagnose/grade`` could stay stateless — leaking answers and
# letting direct consumers submit their own payload. Answer keys now stay in a
# short-lived session store keyed by diagnostic_id; the client only submits
# answers. Redis is used when available, with an in-process TTL fallback.
# ---------------------------------------------------------------------------

_DIAGNOSTIC_SESSION_PREFIX = "exam_sprint:diagnostic:grading_session:"
_DIAGNOSTIC_SESSION_TTL_SECONDS = 24 * 3600


class _DiagnosticSessionStore:
    def __init__(self) -> None:
        self._local: dict[str, tuple[float, dict[str, Any]]] = {}

    def _purge_expired(self, now: float) -> None:
        expired = [key for key, (deadline, _) in self._local.items() if deadline <= now]
        for key in expired:
            self._local.pop(key, None)

    async def save(self, diagnostic_id: str, session: dict[str, Any]) -> None:
        key = _DIAGNOSTIC_SESSION_PREFIX + diagnostic_id
        deadline = time.monotonic() + _DIAGNOSTIC_SESSION_TTL_SECONDS
        self._purge_expired(time.monotonic())
        self._local[key] = (deadline, session)
        redis = cache_service.redis
        if redis is not None:
            try:
                await cache_service.set(key, session, ttl=_DIAGNOSTIC_SESSION_TTL_SECONDS)
            except Exception as exc:  # pragma: no cover - redis best-effort
                logger.debug("diagnostic session redis save failed: {}", exc)

    async def load(self, diagnostic_id: str) -> dict[str, Any] | None:
        key = _DIAGNOSTIC_SESSION_PREFIX + diagnostic_id
        entry = self._local.get(key)
        if entry is not None:
            deadline, session = entry
            if deadline > time.monotonic():
                return session
            self._local.pop(key, None)
        redis = cache_service.redis
        if redis is not None:
            try:
                cached = await cache_service.get(key)
                if isinstance(cached, dict):
                    return cached
            except Exception as exc:  # pragma: no cover - redis best-effort
                logger.debug("diagnostic session redis load failed: {}", exc)
        return None


_diagnostic_session_store = _DiagnosticSessionStore()


def _normalize_text(value: str) -> str:
    return re.sub(r"[\s_\-，。；：、,.!?:（）()]+", "", str(value or "").strip().lower())


def _contains_network_subject(subject: str) -> bool:
    text = str(subject or "").strip().lower()
    return any(token in text for token in ("计算机网络", "计网", "computer network", "networking", "network"))


def _confidence_weight(value: DiagnoseConfidence | str | None) -> float:
    mapping = {
        DiagnoseConfidence.CERTAIN.value: 1.0,
        DiagnoseConfidence.FUZZY.value: 0.6,
        DiagnoseConfidence.GUESS.value: 0.3,
    }
    return mapping.get(str(value or DiagnoseConfidence.FUZZY.value), 0.6)


def _confidence_label(weight: float) -> str:
    if weight >= 0.85:
        return DiagnoseConfidence.CERTAIN.value
    if weight <= 0.4:
        return DiagnoseConfidence.GUESS.value
    return DiagnoseConfidence.FUZZY.value


@dataclass(frozen=True)
class QuestionTemplate:
    template_key: str
    domain: str
    archetype: str
    question_type: DiagnoseQuestionType
    stem: str
    choices: tuple[str, ...] = ()
    correct_choice_index: int | None = None
    accepted_answers: tuple[str, ...] = ()
    required_keywords: tuple[str, ...] = ()
    partial_keywords: tuple[str, ...] = ()
    error_tags: tuple[str, ...] = ()
    linked_node_slugs: tuple[str, ...] = ()
    expected_seconds: int = 50
    points: float = 1.0
    priority: float = 1.0


_CN_DEFAULT_NODES: tuple[dict[str, Any], ...] = (
    {
        "slug": "layering_protocol_stack",
        "name": "分层模型与协议栈",
        "domain": "分层模型与协议栈",
        "exam_weight": 1.0,
        "frequency": 0.95,
        "mistake_tags": ["layer_confusion"],
    },
    {
        "slug": "ip_subnetting",
        "name": "IP / 子网划分",
        "domain": "IP / 子网划分",
        "exam_weight": 1.25,
        "frequency": 1.25,
        "mistake_tags": ["bit_byte_confusion", "subnet_calculation_error"],
    },
    {
        "slug": "routing_basics",
        "name": "路由基础",
        "domain": "路由基础",
        "exam_weight": 1.1,
        "frequency": 1.0,
        "mistake_tags": ["longest_prefix_error", "route_update_confusion"],
    },
    {
        "slug": "tcp_reliable_transport",
        "name": "TCP 可靠传输",
        "domain": "TCP 可靠传输",
        "exam_weight": 1.2,
        "frequency": 1.2,
        "mistake_tags": ["ack_misread", "window_variable_confusion"],
    },
    {
        "slug": "tcp_congestion_control",
        "name": "TCP 拥塞控制",
        "domain": "TCP 拥塞控制",
        "exam_weight": 1.3,
        "frequency": 1.25,
        "mistake_tags": ["state_transition_error", "window_variable_confusion"],
    },
    {
        "slug": "http_dns",
        "name": "HTTP / DNS",
        "domain": "HTTP / DNS",
        "exam_weight": 1.05,
        "frequency": 1.1,
        "mistake_tags": ["process_gap"],
    },
    {
        "slug": "link_layer_basics",
        "name": "链路层基础",
        "domain": "链路层基础",
        "exam_weight": 0.9,
        "frequency": 0.85,
        "mistake_tags": ["mac_confusion"],
    },
)

_CN_QUESTION_ARCHETYPES: tuple[str, ...] = (
    "high_frequency_concept_judgment",
    "high_frequency_calculation",
    "process_trace",
    "integrated_scenario",
)

_CN_CHECKPOINT_TEMPLATE = "mixed_mastery_probe_v1"

_CN_TEMPLATES: tuple[QuestionTemplate, ...] = (
    QuestionTemplate(
        template_key="cn_layers_transport_layer",
        domain="分层模型与协议栈",
        archetype="high_frequency_concept_judgment",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="在 TCP/IP 协议栈里，负责端到端进程复用与分用的主要是哪个层次？",
        choices=("应用层", "传输层", "网络层", "链路层"),
        correct_choice_index=1,
        error_tags=("layer_confusion",),
        linked_node_slugs=("layering_protocol_stack",),
        priority=1.0,
    ),
    QuestionTemplate(
        template_key="cn_layers_router_switch",
        domain="分层模型与协议栈",
        archetype="process_trace",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="一台路由器在转发 IP 数据报时，最直接依赖哪一层的地址信息做下一跳判断？",
        choices=("应用层端口号", "传输层序号", "网络层 IP 地址", "链路层 CRC"),
        correct_choice_index=2,
        error_tags=("layer_confusion",),
        linked_node_slugs=("layering_protocol_stack", "routing_basics"),
        priority=0.95,
    ),
    QuestionTemplate(
        template_key="cn_subnet_hosts",
        domain="IP / 子网划分",
        archetype="high_frequency_calculation",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="网段 `192.168.10.0/27` 最多可分配给主机的可用地址数量是多少？",
        choices=("14", "30", "32", "62"),
        correct_choice_index=1,
        error_tags=("subnet_calculation_error", "bit_byte_confusion"),
        linked_node_slugs=("ip_subnetting",),
        priority=1.3,
    ),
    QuestionTemplate(
        template_key="cn_subnet_mask_short",
        domain="IP / 子网划分",
        archetype="high_frequency_calculation",
        question_type=DiagnoseQuestionType.SHORT_ANSWER,
        stem="请写出前缀 `/26` 对应的子网掩码，并写出一个子网中可用主机地址的数量。",
        accepted_answers=("255.255.255.192,62", "255.255.255.192 62", "255.255.255.192；62"),
        required_keywords=("255.255.255.192", "62"),
        partial_keywords=("26",),
        error_tags=("subnet_calculation_error", "bit_byte_confusion"),
        linked_node_slugs=("ip_subnetting",),
        expected_seconds=75,
        priority=1.25,
    ),
    QuestionTemplate(
        template_key="cn_routing_longest_prefix",
        domain="路由基础",
        archetype="process_trace",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="路由器查表时，如果一条报文同时匹配多条路由，默认应优先采用哪条？",
        choices=("跳数最少的", "前缀最长的", "管理距离最小的", "最先配置的"),
        correct_choice_index=1,
        error_tags=("longest_prefix_error",),
        linked_node_slugs=("routing_basics",),
        priority=1.15,
    ),
    QuestionTemplate(
        template_key="cn_routing_dv_ls",
        domain="路由基础",
        archetype="high_frequency_concept_judgment",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="下列哪项更符合链路状态路由协议的特点？",
        choices=("只向邻居通告距离向量", "每次仅更新一条默认路由", "维护全网拓扑后本地运行最短路算法", "只依赖 ARP 缓存做更新"),
        correct_choice_index=2,
        error_tags=("route_update_confusion",),
        linked_node_slugs=("routing_basics",),
        priority=1.0,
    ),
    QuestionTemplate(
        template_key="cn_tcp_ack",
        domain="TCP 可靠传输",
        archetype="high_frequency_calculation",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="主机 A 发送了一个从序号 1000 开始、长度为 200 字节的 TCP 报文段，主机 B 正常收到后返回的累计 ACK 应该是多少？",
        choices=("1000", "1001", "1199", "1200"),
        correct_choice_index=3,
        error_tags=("ack_misread",),
        linked_node_slugs=("tcp_reliable_transport",),
        priority=1.2,
    ),
    QuestionTemplate(
        template_key="cn_tcp_window",
        domain="TCP 可靠传输",
        archetype="high_frequency_concept_judgment",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="TCP 中接收窗口 `rwnd` 最直接反映的是什么？",
        choices=("链路带宽上限", "接收方缓存还能接收多少数据", "拥塞窗口的初始值", "往返时延 RTT"),
        correct_choice_index=1,
        error_tags=("window_variable_confusion",),
        linked_node_slugs=("tcp_reliable_transport",),
        priority=1.0,
    ),
    QuestionTemplate(
        template_key="cn_tcp_congestion_timeout",
        domain="TCP 拥塞控制",
        archetype="process_trace",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="TCP 发送方发生超时重传后，拥塞控制最典型的动作是什么？",
        choices=("cwnd 翻倍继续发送", "ssthresh 不变，cwnd 清零", "ssthresh 减半，并把 cwnd 退回到较小值重新慢启动", "直接进入快速恢复并保持窗口不变"),
        correct_choice_index=2,
        error_tags=("state_transition_error",),
        linked_node_slugs=("tcp_congestion_control",),
        priority=1.35,
    ),
    QuestionTemplate(
        template_key="cn_tcp_congestion_dup_ack",
        domain="TCP 拥塞控制",
        archetype="integrated_scenario",
        question_type=DiagnoseQuestionType.SHORT_ANSWER,
        stem="发送方连续收到 3 个重复 ACK 时，通常会触发哪两个关键机制？请各写出一个名称。",
        accepted_answers=("快重传 快恢复", "快重传,快恢复", "fast retransmit fast recovery"),
        required_keywords=("快重传", "快恢复"),
        partial_keywords=("重复ack", "duplicateack"),
        error_tags=("state_transition_error", "ack_misread"),
        linked_node_slugs=("tcp_congestion_control", "tcp_reliable_transport"),
        expected_seconds=80,
        priority=1.3,
    ),
    QuestionTemplate(
        template_key="cn_dns_order",
        domain="HTTP / DNS",
        archetype="process_trace",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="浏览器输入一个新域名并回车后，在真正发送 HTTP 请求前，通常最先必须完成的关键网络动作是什么？",
        choices=("三次握手结束并传输正文", "DNS 解析得到目标 IP", "路由器刷新整张路由表", "应用层先发送 ACK"),
        correct_choice_index=1,
        error_tags=("process_gap",),
        linked_node_slugs=("http_dns",),
        priority=1.15,
    ),
    QuestionTemplate(
        template_key="cn_http_keep_alive",
        domain="HTTP / DNS",
        archetype="high_frequency_concept_judgment",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="HTTP 持久连接（keep-alive）的主要收益更接近下面哪一项？",
        choices=("绕过 DNS 解析", "减少重复建立 TCP 连接的开销", "替代拥塞控制", "把 IP 地址变成域名"),
        correct_choice_index=1,
        error_tags=("process_gap",),
        linked_node_slugs=("http_dns",),
        priority=1.0,
    ),
    QuestionTemplate(
        template_key="cn_link_crc",
        domain="链路层基础",
        archetype="high_frequency_concept_judgment",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="以太网帧尾部的 CRC 校验最主要用于什么？",
        choices=("确认路由是否最短", "检测比特传输差错", "计算子网掩码", "决定拥塞窗口大小"),
        correct_choice_index=1,
        error_tags=("mac_confusion",),
        linked_node_slugs=("link_layer_basics",),
        priority=0.95,
    ),
    QuestionTemplate(
        template_key="cn_integrated_end_to_end",
        domain="综合题",
        archetype="integrated_scenario",
        question_type=DiagnoseQuestionType.SHORT_ANSWER,
        stem="用户访问一个从未访问过的网站时，请按先后写出 3 个关键步骤，至少包含 DNS、TCP 或 HTTP 中的两个词。",
        required_keywords=("dns", "tcp", "http"),
        partial_keywords=("三次握手", "请求", "解析"),
        error_tags=("process_gap", "layer_confusion"),
        linked_node_slugs=("http_dns", "tcp_reliable_transport", "layering_protocol_stack"),
        expected_seconds=90,
        priority=1.05,
        points=1.2,
    ),
)

_CN_CORE_TEMPLATE_KEYS = (
    "cn_layers_transport_layer",
    "cn_subnet_hosts",
    "cn_routing_longest_prefix",
    "cn_tcp_ack",
    "cn_tcp_congestion_timeout",
    "cn_dns_order",
    "cn_link_crc",
)

# ---------------------------------------------------------------------------
# P1-E2: data-structures template set
#
# The MVP whitelist only accepted computer networks, so the seeded「数据结构」
# scenario failed with 422. A second template set (content verified against the
# data_structures_algorithms sprint pack, slugs = pack node suffixes so mastery
# maps onto canonical ds.* galaxy nodes) unlocks the seed scenario.
# ---------------------------------------------------------------------------

_DS_DEFAULT_NODES: tuple[dict[str, Any], ...] = (
    {"slug": "array", "name": "数组与顺序表", "domain": "线性表", "exam_weight": 1.0, "frequency": 1.0, "mistake_tags": ["complexity_confusion"]},
    {"slug": "linked_list", "name": "链表", "domain": "线性表", "exam_weight": 1.1, "frequency": 1.05, "mistake_tags": ["pointer_order_error"]},
    {"slug": "stack", "name": "栈", "domain": "栈与队列", "exam_weight": 1.15, "frequency": 1.15, "mistake_tags": ["sequence_permutation_error"]},
    {"slug": "queue", "name": "队列与循环队列", "domain": "栈与队列", "exam_weight": 1.05, "frequency": 1.0, "mistake_tags": ["boundary_condition_error"]},
    {"slug": "binary_tree", "name": "二叉树性质", "domain": "树与二叉树", "exam_weight": 1.2, "frequency": 1.2, "mistake_tags": ["property_formula_error"]},
    {"slug": "bst", "name": "二叉搜索树", "domain": "树与二叉树", "exam_weight": 1.15, "frequency": 1.1, "mistake_tags": ["traversal_confusion"]},
    {"slug": "graph_representation", "name": "图的存储", "domain": "图", "exam_weight": 1.0, "frequency": 0.95, "mistake_tags": ["storage_confusion"]},
    {"slug": "bfs", "name": "广度优先搜索", "domain": "图", "exam_weight": 1.1, "frequency": 1.05, "mistake_tags": ["auxiliary_structure_confusion"]},
    {"slug": "dfs", "name": "深度优先搜索", "domain": "图", "exam_weight": 1.1, "frequency": 1.05, "mistake_tags": ["auxiliary_structure_confusion"]},
    {"slug": "binary_search", "name": "二分查找", "domain": "查找与哈希", "exam_weight": 1.15, "frequency": 1.15, "mistake_tags": ["complexity_confusion"]},
    {"slug": "hash_table", "name": "哈希表", "domain": "查找与哈希", "exam_weight": 1.05, "frequency": 1.0, "mistake_tags": ["collision_method_confusion"]},
    {"slug": "quicksort", "name": "快速排序", "domain": "排序", "exam_weight": 1.25, "frequency": 1.2, "mistake_tags": ["complexity_confusion"]},
    {"slug": "heap_sort", "name": "堆排序", "domain": "排序", "exam_weight": 1.1, "frequency": 1.0, "mistake_tags": ["heap_property_error"]},
    {"slug": "time_complexity", "name": "时间复杂度分析", "domain": "复杂度分析", "exam_weight": 1.2, "frequency": 1.15, "mistake_tags": ["complexity_confusion"]},
)

_DS_QUESTION_ARCHETYPES: tuple[str, ...] = (
    "high_frequency_concept_judgment",
    "high_frequency_calculation",
    "process_trace",
    "integrated_scenario",
)

_DS_TEMPLATES: tuple[QuestionTemplate, ...] = (
    QuestionTemplate(
        template_key="ds_array_random_access",
        domain="线性表",
        archetype="high_frequency_concept_judgment",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="含 n 个元素的顺序表（数组）按下标随机访问第 i 个元素，时间复杂度是？",
        choices=("O(n)", "O(log n)", "O(1)", "O(n log n)"),
        correct_choice_index=2,
        error_tags=("complexity_confusion",),
        linked_node_slugs=("array",),
        expected_seconds=40,
    ),
    QuestionTemplate(
        template_key="ds_linked_list_insert",
        domain="线性表",
        archetype="process_trace",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="单链表中指针 p 指向某结点，将新结点 s 插入到 p 之后，正确的操作序列是？",
        choices=("p.next = s; s.next = p.next", "s.next = p.next; p.next = s", "s.next = p; p = s", "p.next = s.next; s.next = p"),
        correct_choice_index=1,
        error_tags=("pointer_order_error",),
        linked_node_slugs=("linked_list",),
        expected_seconds=55,
    ),
    QuestionTemplate(
        template_key="ds_stack_permutation",
        domain="栈与队列",
        archetype="high_frequency_calculation",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="元素 1、2、3 依次进栈（进栈与出栈可交错进行），下列哪个出栈序列不可能得到？",
        choices=("3 1 2", "3 2 1", "2 3 1", "1 3 2"),
        correct_choice_index=0,
        error_tags=("sequence_permutation_error",),
        linked_node_slugs=("stack",),
        expected_seconds=60,
    ),
    QuestionTemplate(
        template_key="ds_queue_circular_full",
        domain="栈与队列",
        archetype="high_frequency_concept_judgment",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="循环队列用大小为 m 的数组实现，front 指向队头、rear 指向队尾的下一位置，牺牲一个存储单元区分队空与队满，则队满条件是？",
        choices=("rear == front", "(rear + 1) % m == front", "rear - front == m", "front == 0 且 rear == m"),
        correct_choice_index=1,
        error_tags=("boundary_condition_error",),
        linked_node_slugs=("queue",),
        expected_seconds=50,
    ),
    QuestionTemplate(
        template_key="ds_binary_tree_leaf_count",
        domain="树与二叉树",
        archetype="high_frequency_calculation",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="某二叉树中有 5 个度为 2 的结点，则叶子结点的个数是？",
        choices=("5", "6", "4", "7"),
        correct_choice_index=1,
        error_tags=("property_formula_error",),
        linked_node_slugs=("binary_tree",),
        expected_seconds=50,
    ),
    QuestionTemplate(
        template_key="ds_bst_inorder",
        domain="树与二叉树",
        archetype="high_frequency_concept_judgment",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="对二叉搜索树（BST）进行中序遍历，得到的关键码序列是？",
        choices=("递增有序序列", "递减有序序列", "无序序列", "按层访问序列"),
        correct_choice_index=0,
        error_tags=("traversal_confusion",),
        linked_node_slugs=("bst",),
        expected_seconds=40,
    ),
    QuestionTemplate(
        template_key="ds_graph_bfs_aux",
        domain="图",
        archetype="high_frequency_concept_judgment",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="对图进行广度优先搜索（BFS）时，通常使用的辅助数据结构是？",
        choices=("栈", "队列", "优先队列", "散列表"),
        correct_choice_index=1,
        error_tags=("auxiliary_structure_confusion",),
        linked_node_slugs=("bfs", "graph_representation"),
        expected_seconds=40,
    ),
    QuestionTemplate(
        template_key="ds_graph_dfs_aux",
        domain="图",
        archetype="high_frequency_concept_judgment",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="对图进行深度优先搜索（DFS）的非递归实现中，通常使用的辅助数据结构是？",
        choices=("队列", "堆", "栈", "循环队列"),
        correct_choice_index=2,
        error_tags=("auxiliary_structure_confusion",),
        linked_node_slugs=("dfs",),
        expected_seconds=40,
    ),
    QuestionTemplate(
        template_key="ds_binary_search_worst",
        domain="查找与哈希",
        archetype="high_frequency_calculation",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="对含 n 个元素的有序顺序表进行二分查找，最坏情况下的时间复杂度是？",
        choices=("O(1)", "O(n)", "O(n log n)", "O(log n)"),
        correct_choice_index=3,
        error_tags=("complexity_confusion",),
        linked_node_slugs=("binary_search",),
        expected_seconds=45,
    ),
    QuestionTemplate(
        template_key="ds_hash_collision",
        domain="查找与哈希",
        archetype="high_frequency_concept_judgment",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="下列哪种方法不属于哈希表解决冲突的常用方法？",
        choices=("开放定址法（线性探测）", "链地址法", "再哈希法", "二分插入法"),
        correct_choice_index=3,
        error_tags=("collision_method_confusion",),
        linked_node_slugs=("hash_table",),
        expected_seconds=45,
    ),
    QuestionTemplate(
        template_key="ds_quicksort_complexity",
        domain="排序",
        archetype="high_frequency_calculation",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="快速排序在平均情况与最坏情况下的时间复杂度分别是？",
        choices=("O(n log n)，O(n^2)", "O(n^2)，O(n log n)", "O(n log n)，O(n log n)", "O(n^2)，O(n^2)"),
        correct_choice_index=0,
        error_tags=("complexity_confusion",),
        linked_node_slugs=("quicksort",),
        expected_seconds=50,
    ),
    QuestionTemplate(
        template_key="ds_heap_sort_top",
        domain="排序",
        archetype="high_frequency_concept_judgment",
        question_type=DiagnoseQuestionType.SINGLE_CHOICE,
        stem="使用最大堆进行堆排序（升序输出）时，堆顶元素是整个序列的？",
        choices=("最小值", "最大值", "中位数", "随机元素"),
        correct_choice_index=1,
        error_tags=("heap_property_error",),
        linked_node_slugs=("heap_sort",),
        expected_seconds=40,
    ),
    QuestionTemplate(
        template_key="ds_sa_quicksort_worst",
        domain="复杂度分析",
        archetype="high_frequency_calculation",
        question_type=DiagnoseQuestionType.SHORT_ANSWER,
        stem="简答：写出快速排序最坏情况下的时间复杂度（用大 O 记号表示，如 O(n^2)）。",
        accepted_answers=("O(n^2)", "O(n²)", "O(n*n)", "O(n2)", "n^2"),
        required_keywords=("n^2",),
        error_tags=("complexity_confusion",),
        linked_node_slugs=("time_complexity",),
        expected_seconds=60,
    ),
)

_DS_CORE_TEMPLATE_KEYS = (
    "ds_array_random_access",
    "ds_stack_permutation",
    "ds_binary_tree_leaf_count",
    "ds_graph_bfs_aux",
    "ds_binary_search_worst",
    "ds_quicksort_complexity",
    "ds_sa_quicksort_worst",
)


@dataclass(frozen=True)
class _SubjectTemplateSet:
    """Per-subject question templates, core keys and default knowledge nodes."""

    templates: tuple[QuestionTemplate, ...]
    core_keys: tuple[str, ...]
    default_nodes: tuple[dict[str, Any], ...]
    archetypes: tuple[str, ...] = (
        "high_frequency_concept_judgment",
        "high_frequency_calculation",
        "process_trace",
        "integrated_scenario",
    )


_SUBJECT_TEMPLATE_SETS: dict[str, _SubjectTemplateSet] = {
    "computer_networks": _SubjectTemplateSet(
        _CN_TEMPLATES, _CN_CORE_TEMPLATE_KEYS, _CN_DEFAULT_NODES, _CN_QUESTION_ARCHETYPES
    ),
    "data_structures_algorithms": _SubjectTemplateSet(
        _DS_TEMPLATES, _DS_CORE_TEMPLATE_KEYS, _DS_DEFAULT_NODES, _DS_QUESTION_ARCHETYPES
    ),
}

_SUPPORTED_SUBJECT_HINT = "计算机网络、数据结构"


def _resolve_subject_pack_key(subject: str) -> str | None:
    """Map free-text subject (incl. titles like「数据结构期中」) to a pack key."""
    text = str(subject or "").strip()
    if not text:
        return None
    try:
        from app.sprint_packs.sprint_pack_loader import _SUBJECT_ALIASES
        from app.sprint_packs.sprint_pack_registry import SprintPackRegistry

        direct = SprintPackRegistry().match_subject(text)
        if direct:
            return direct
        lowered = text.lower()
        for alias, pack_id in _SUBJECT_ALIASES.items():
            if lowered.startswith(alias):
                return pack_id
    except Exception as exc:  # pragma: no cover - registry is best-effort
        logger.debug("subject pack resolution failed for {!r}: {}", subject, exc)
    if _contains_network_subject(text):
        return "computer_networks"
    return None


class ExamSprintDiagnosticService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate(
        self,
        *,
        user_id: UUID,
        request: DiagnosticGenerateRequest,
    ) -> DiagnosticGenerateResponse:
        del user_id
        pack_payload = self._load_pack_payload(
            sprint_pack_id=request.sprint_pack_id,
            sprint_pack_path=request.sprint_pack_path,
        )
        subject = str(request.subject).strip()
        nodes = await self._resolve_nodes(subject=subject, requested_nodes=request.knowledge_nodes)
        templates = self._select_templates(subject=subject, nodes=nodes, question_count=request.question_count)
        if len({template.domain for template in templates if template.domain != "综合题"}) < 5:
            raise ValueError("诊断题覆盖领域不足，至少需要 5 个不同知识领域")

        node_index = {node.slug or "": node for node in nodes}
        questions: list[DiagnosticQuestionPrompt] = []
        grading_payload: dict[str, DiagnosticQuestionGrader] = {}
        total_seconds = 0
        diagnostic_id = f"diag-{uuid4()}"
        for index, template in enumerate(templates, start=1):
            question_id = f"diag_{index}_{template.template_key}"
            linked_nodes = [node_index[slug] for slug in template.linked_node_slugs if slug in node_index]
            questions.append(
                DiagnosticQuestionPrompt(
                    question_id=question_id,
                    domain=template.domain,
                    archetype=template.archetype,
                    question_type=template.question_type,
                    stem=template.stem,
                    choices=list(template.choices),
                    linked_node_slugs=list(template.linked_node_slugs),
                    linked_node_ids=[node.node_id for node in linked_nodes if node.node_id is not None],
                    linked_node_names=[node.name for node in linked_nodes],
                    points=template.points,
                    expected_seconds=template.expected_seconds,
                )
            )
            total_seconds += template.expected_seconds
            grading_payload[question_id] = DiagnosticQuestionGrader(
                template_key=template.template_key,
                question_type=template.question_type,
                correct_choice_index=template.correct_choice_index,
                choices=list(template.choices),
                accepted_answers=list(template.accepted_answers),
                required_keywords=list(template.required_keywords),
                partial_keywords=list(template.partial_keywords),
                error_tags=list(template.error_tags),
                linked_node_slugs=list(template.linked_node_slugs),
                linked_node_ids=[node.node_id for node in linked_nodes if node.node_id is not None],
                linked_node_names=[node.name for node in linked_nodes],
                points=template.points,
            )

        # P1-E4: keep answer keys server-side; the client only receives questions.
        await _diagnostic_session_store.save(
            str(diagnostic_id),
            {
                "subject": subject,
                "days_left": request.days_left,
                "pass_score": request.pass_score,
                "sprint_pack_id": request.sprint_pack_id,
                "grading_payload": {key: value.model_dump(mode="json") for key, value in grading_payload.items()},
                "knowledge_nodes": [node.model_dump(mode="json") for node in nodes],
            },
        )

        return DiagnosticGenerateResponse(
            diagnostic_id=diagnostic_id,
            subject=subject,
            sprint_pack_id=str(request.sprint_pack_id or pack_payload.get("id") or EXAM_PREP_14D_PACK_ID),
            question_count=len(questions),
            estimated_minutes=max(10, round(total_seconds / 60)),
            coverage_domains=self._coverage_domains(questions),
            question_archetypes=self._extract_question_archetypes(pack_payload, subject),
            checkpoint_template=self._extract_checkpoint_template(pack_payload, subject),
            questions=questions,
        )

    async def grade(
        self,
        *,
        user_id: UUID,
        request: DiagnosticGradeRequest,
    ) -> DiagnosticGradeResponse:
        subject = str(request.subject).strip()
        nodes = await self._resolve_nodes(subject=subject, requested_nodes=request.knowledge_nodes)
        node_index = {node.slug or "": node for node in nodes}
        grading_payload = dict(request.grading_payload or {})
        days_left_override = request.days_left
        pass_score_override = request.pass_score

        # P1-E4: the server-held session (from /diagnose/generate) is authoritative;
        # request.grading_payload is only honored as a legacy stateless fallback.
        session = None
        if request.diagnostic_id:
            session = await _diagnostic_session_store.load(str(request.diagnostic_id))
        if session is not None:
            raw_payload = session.get("grading_payload") or {}
            grading_payload = {
                key: value if isinstance(value, DiagnosticQuestionGrader) else DiagnosticQuestionGrader(**value)
                for key, value in raw_payload.items()
            }
            raw_nodes = session.get("knowledge_nodes") or []
            if raw_nodes and not request.knowledge_nodes:
                nodes = await self._resolve_nodes(
                    subject=subject,
                    requested_nodes=[DiagnosticKnowledgeNode(**item) for item in raw_nodes],
                )
                node_index = {node.slug or "": node for node in nodes}
            if days_left_override is None and session.get("days_left") is not None:
                days_left_override = int(session["days_left"])
            if session.get("pass_score") is not None:
                pass_score_override = float(session["pass_score"])
        if not grading_payload:
            raise ValueError(
                "grading_payload is required: pass the diagnostic_id returned by /diagnose/generate "
                "(server-held session) or, for legacy stateless calls, the grading_payload"
            )

        answers_by_id = {item.question_id: item for item in request.answers}
        total_points = 0.0
        earned_points = 0.0
        error_counter: Counter[str] = Counter()
        confidence_stats = {
            "certain_total": 0,
            "certain_correct": 0,
            "guess_total": 0,
            "guess_correct": 0,
            "overconfidence_miss": 0,
        }
        node_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "node": None,
                "total_points": 0.0,
                "earned_points": 0.0,
                "confidence_total": 0.0,
                "confidence_count": 0,
                "mistake_tags": Counter(),
            }
        )

        for question_id, grader in grading_payload.items():
            submission = answers_by_id.get(question_id)
            answer_text = submission.answer if submission else ""
            confidence = submission.confidence if submission else DiagnoseConfidence.GUESS
            correctness = self._score_answer(answer_text, grader)
            earned_points += correctness * grader.points
            total_points += grader.points
            confidence_weight = _confidence_weight(confidence)
            if confidence == DiagnoseConfidence.CERTAIN:
                confidence_stats["certain_total"] += 1
                if correctness >= 0.999:
                    confidence_stats["certain_correct"] += 1
            if confidence == DiagnoseConfidence.GUESS:
                confidence_stats["guess_total"] += 1
                if correctness >= 0.999:
                    confidence_stats["guess_correct"] += 1
            if correctness < 0.999 and confidence == DiagnoseConfidence.CERTAIN:
                confidence_stats["overconfidence_miss"] += 1
                error_counter["overconfidence_miss"] += 1
            if correctness < 0.999:
                for tag in grader.error_tags:
                    error_counter[tag] += 1

            for idx, slug in enumerate(grader.linked_node_slugs):
                node = node_index.get(slug)
                if node is None:
                    fallback_name = grader.linked_node_names[idx] if idx < len(grader.linked_node_names) else slug
                    node = DiagnosticKnowledgeNode(name=fallback_name, slug=slug, domain=fallback_name)
                    node_index[slug] = node
                stats = node_stats[slug]
                stats["node"] = node
                stats["total_points"] += grader.points
                stats["earned_points"] += correctness * grader.points
                stats["confidence_total"] += confidence_weight
                stats["confidence_count"] += 1
                if correctness < 0.999:
                    stats["mistake_tags"].update(grader.error_tags)

        estimated_score_now = round((earned_points / max(total_points, 0.001)) * 100.0, 1)
        days_left = await self._resolve_days_left(user_id=user_id, request_days_left=days_left_override)
        all_node_mastery_updates = self._build_node_mastery_updates(node_stats)
        top_bottlenecks = self._build_bottlenecks(node_stats)
        recommended_path = self._recommend_path(
            estimated_score_now=estimated_score_now,
            pass_score=pass_score_override,
            days_left=days_left,
            bottlenecks=top_bottlenecks,
        )
        pass_probability = round(
            self._estimate_pass_probability(
                estimated_score_now=estimated_score_now,
                pass_score=pass_score_override,
                days_left=days_left,
                overconfidence_miss=confidence_stats["overconfidence_miss"],
            ),
            3,
        )

        if request.update_galaxy:
            await self._persist_node_mastery(user_id=user_id, mastery_updates=all_node_mastery_updates)

        await self._persist_profile_diagnostic_summary(
            user_id=user_id,
            subject=subject,
            days_left=days_left,
            estimated_score_now=estimated_score_now,
            pass_probability=pass_probability,
            recommended_path=recommended_path,
            top_bottlenecks=top_bottlenecks,
            node_mastery_updates=all_node_mastery_updates,
            coverage_domains=sorted(
                {item.domain for item in top_bottlenecks} | {item.node_name for item in all_node_mastery_updates}
            ),
        )

        return DiagnosticGradeResponse(
            estimated_score_now=estimated_score_now,
            pass_probability=pass_probability,
            top_bottlenecks=top_bottlenecks,
            error_distribution={key: float(value) for key, value in error_counter.items()},
            mistake_clusters=self._top_mistake_clusters(error_counter),
            recommended_path=recommended_path,
            node_mastery_updates=all_node_mastery_updates,
            coverage_domains=sorted({item.domain for item in top_bottlenecks} | {item.node_name for item in all_node_mastery_updates}),
            confidence_calibration=self._build_confidence_calibration(confidence_stats),
        )

    async def _resolve_nodes(
        self,
        *,
        subject: str,
        requested_nodes: list[DiagnosticKnowledgeNode],
    ) -> list[DiagnosticKnowledgeNode]:
        resolved: list[DiagnosticKnowledgeNode] = []
        seen: set[str] = set()
        for raw in requested_nodes:
            slug = self._canonical_slug(raw.slug or raw.name)
            node = raw.model_copy(update={"slug": slug, "domain": raw.domain or raw.name})
            if slug and slug not in seen:
                resolved.append(node)
                seen.add(slug)
        if _contains_network_subject(subject):
            for item in _CN_DEFAULT_NODES:
                if item["slug"] in seen:
                    continue
                resolved.append(DiagnosticKnowledgeNode(**item))
                seen.add(item["slug"])
        pack_key = _resolve_subject_pack_key(subject)
        subject_set = _SUBJECT_TEMPLATE_SETS.get(pack_key or "")
        if subject_set is not None:
            for item in subject_set.default_nodes:
                if item["slug"] in seen:
                    continue
                resolved.append(DiagnosticKnowledgeNode(**item))
                seen.add(item["slug"])
        elif len(resolved) < 5:
            # daily-flow DF-4：未内置题包的科目（eval 里是「大学物理」）不能拿
            # 「知识节点覆盖不足」搪塞——即使用户补足节点，模板选择依然无题可出。
            # 直接给出可行动的错误：指明科目不支持与当前支持的科目清单。
            hint = f"诊断暂支持的科目：{_SUPPORTED_SUBJECT_HINT}；「{subject or '未指定科目'}」暂未内置诊断题包"
            raise ValueError(hint)
        if len({item.domain for item in resolved}) < 5:
            raise ValueError("知识节点覆盖不足，至少需要 5 个不同知识领域")
        return resolved

    def _select_templates(
        self,
        *,
        subject: str,
        nodes: list[DiagnosticKnowledgeNode],
        question_count: int,
    ) -> list[QuestionTemplate]:
        # P1-E2: subject-driven template selection (was computer-networks only).
        subject_set = _SUBJECT_TEMPLATE_SETS.get(_resolve_subject_pack_key(subject) or "")
        if subject_set is None:
            raise ValueError(f"当前 MVP 支持的科目：{_SUPPORTED_SUBJECT_HINT}，暂不支持「{subject}」的诊断小测")
        templates = subject_set.templates
        node_index = {node.slug or "": node for node in nodes}
        core = [item for item in templates if item.template_key in subject_set.core_keys]
        extras = [
            (self._template_priority(item, node_index), item)
            for item in templates
            if item.template_key not in subject_set.core_keys
        ]
        extras.sort(key=lambda item: item[0], reverse=True)
        selected = list(core)
        for _, template in extras:
            if len(selected) >= question_count:
                break
            selected.append(template)
        return selected[:question_count]

    def _template_priority(
        self,
        template: QuestionTemplate,
        node_index: dict[str, DiagnosticKnowledgeNode],
    ) -> float:
        if not template.linked_node_slugs:
            return template.priority
        weighted = []
        for slug in template.linked_node_slugs:
            node = node_index.get(slug)
            if node is None:
                continue
            weighted.append(float(node.exam_weight) * float(node.frequency))
        return (sum(weighted) / len(weighted) if weighted else 1.0) * template.priority

    def _score_answer(self, answer: str, grader: DiagnosticQuestionGrader) -> float:
        if grader.question_type == DiagnoseQuestionType.SINGLE_CHOICE:
            return self._score_choice_answer(answer, grader)
        return self._score_short_answer(answer, grader)

    def _score_choice_answer(self, answer: str, grader: DiagnosticQuestionGrader) -> float:
        normalized = _normalize_text(answer)
        if grader.correct_choice_index is None:
            return 0.0
        if normalized in {"a", "b", "c", "d"}:
            return 1.0 if {"a": 0, "b": 1, "c": 2, "d": 3}[normalized] == grader.correct_choice_index else 0.0
        if normalized.isdigit():
            index = int(normalized)
            if index == grader.correct_choice_index or index - 1 == grader.correct_choice_index:
                return 1.0
        # P1-E4 compat: clients may submit the choice TEXT instead of an index.
        if grader.choices:
            correct_text = (
                _normalize_text(grader.choices[grader.correct_choice_index])
                if 0 <= grader.correct_choice_index < len(grader.choices)
                else ""
            )
            if correct_text and normalized == correct_text:
                return 1.0
            if any(normalized == _normalize_text(choice) for choice in grader.choices):
                return 0.0
        return 0.0

    def _score_short_answer(self, answer: str, grader: DiagnosticQuestionGrader) -> float:
        normalized = _normalize_text(answer)
        if not normalized:
            return 0.0
        exact = [_normalize_text(item) for item in grader.accepted_answers]
        if exact and normalized in exact:
            return 1.0
        required_hits = sum(1 for item in grader.required_keywords if _normalize_text(item) in normalized)
        partial_hits = sum(1 for item in grader.partial_keywords if _normalize_text(item) in normalized)
        required_ratio = required_hits / max(len(grader.required_keywords), 1)
        if required_ratio >= 1.0:
            return 1.0
        if required_ratio >= 0.5 or partial_hits:
            return round(min(0.85, required_ratio * 0.8 + min(partial_hits, 2) * 0.1), 2)
        return 0.0

    def _build_bottlenecks(self, node_stats: dict[str, dict[str, Any]]) -> list[DiagnosticBottleneck]:
        items: list[DiagnosticBottleneck] = []
        for slug, stats in node_stats.items():
            node = stats["node"]
            total_points = float(stats["total_points"] or 0.0)
            if total_points <= 0:
                continue
            mastery = round((float(stats["earned_points"] or 0.0) / total_points) * 100.0, 1)
            confidence_weight = float(stats["confidence_total"] or 0.0) / max(int(stats["confidence_count"] or 1), 1)
            mistake_tags = [key for key, _ in stats["mistake_tags"].most_common(3)]
            node_name = str(node.name if node else slug)
            domain = str(node.domain or node_name) if node else node_name
            reason = f"{node_name} 相关题得分偏低，当前掌握度估计约 {mastery:.1f}/100。"
            if mistake_tags:
                reason = f"{reason} 主要问题集中在 {', '.join(mistake_tags[:2])}。"
            items.append(
                DiagnosticBottleneck(
                    node_id=node.node_id if node else None,
                    node_name=node_name,
                    node_slug=slug,
                    domain=domain,
                    mastery=mastery,
                    accuracy=round(mastery / 100.0, 3),
                    mistake_tags=mistake_tags,
                    avg_confidence=_confidence_label(confidence_weight),
                    reason=reason,
                )
            )
        items.sort(key=lambda item: (item.mastery, -len(item.mistake_tags), item.node_name))
        return items[:3]

    def _build_node_mastery_updates(
        self,
        node_stats: dict[str, dict[str, Any]],
    ) -> list[DiagnosticMasteryUpdate]:
        updates: list[DiagnosticMasteryUpdate] = []
        for slug, stats in node_stats.items():
            node = stats["node"]
            total_points = float(stats["total_points"] or 0.0)
            if total_points <= 0 or node is None:
                continue
            mastery = round((float(stats["earned_points"] or 0.0) / total_points) * 100.0, 1)
            updates.append(
                DiagnosticMasteryUpdate(
                    node_id=node.node_id,
                    node_name=node.name,
                    node_slug=slug,
                    mastery=mastery,
                )
            )
        updates.sort(key=lambda item: (item.mastery, item.node_name))
        return updates

    def _recommend_path(
        self,
        *,
        estimated_score_now: float,
        pass_score: float,
        days_left: int,
        bottlenecks: list[DiagnosticBottleneck],
    ) -> RecommendedPath:
        severe_bottlenecks = sum(1 for item in bottlenecks if item.mastery < 45.0)
        if days_left <= 7 and estimated_score_now < pass_score + 5:
            return RecommendedPath.MINIMUM_PASS
        if estimated_score_now < pass_score - 8:
            return RecommendedPath.MINIMUM_PASS
        if severe_bottlenecks >= 2 and days_left <= 10:
            return RecommendedPath.MINIMUM_PASS
        return RecommendedPath.SCORE_MAX

    def _estimate_pass_probability(
        self,
        *,
        estimated_score_now: float,
        pass_score: float,
        days_left: int,
        overconfidence_miss: int,
    ) -> float:
        improvement_window = min(22.0, max(days_left, 0) * 1.8)
        risk_penalty = min(10.0, overconfidence_miss * 2.5)
        forecast_score = estimated_score_now + improvement_window - risk_penalty
        return 1.0 / (1.0 + math.exp(-((forecast_score - pass_score) / 6.0)))

    async def _resolve_days_left(self, *, user_id: UUID, request_days_left: int | None) -> int:
        if request_days_left is not None:
            return int(request_days_left)
        prefs = await self.db.execute(select(UserPreferencesCenter.explicit).where(UserPreferencesCenter.user_id == user_id))
        explicit = prefs.scalar_one_or_none() or {}
        if isinstance(explicit, dict):
            cold_start = explicit.get("cold_start_context")
            if isinstance(cold_start, dict):
                try:
                    days_left = int(cold_start.get("time_constraint_days") or cold_start.get("days_left") or 0)
                    if days_left > 0:
                        return days_left
                except (TypeError, ValueError):
                    pass
        return 7

    async def _persist_node_mastery(
        self,
        *,
        user_id: UUID,
        mastery_updates: list[DiagnosticMasteryUpdate],
    ) -> None:
        for item in mastery_updates:
            node_id = item.node_id or await self._resolve_node_id_by_name(item.node_name)
            if node_id is None:
                # P1-E3: fall back to sprint-pack/topic node resolution instead of
                # silently dropping the mastery update when no same-name node exists.
                node_id = await self._ensure_topic_node(item)
            if node_id is None:
                logger.warning("diagnostic mastery update dropped: unresolved topic node for {!r}", item.node_slug)
                continue
            item.node_id = node_id
            await self._write_mastery_value(user_id=user_id, node_id=node_id, mastery=item.mastery)

    async def _ensure_topic_node(self, item: DiagnosticMasteryUpdate) -> UUID | None:
        """Resolve a diagnostic topic to (creating if needed) a galaxy node id.

        Resolution order: curated alias -> sprint-pack node suffix match ->
        deterministic diagnostic topic node. The sprint-pack route keeps the
        node inside the canonical knowledge graph (TECH sector, pack metadata).
        """
        slug = str(item.node_slug or "").strip()
        name = str(item.node_name or slug).strip()
        if not slug and not name:
            return None

        pack_node_id = _DIAG_TOPIC_NODE_ALIASES.get(slug)
        if pack_node_id is None and slug:
            pack_node_id = _pack_node_suffix_index().get(slug)

        if pack_node_id:
            galaxy = GalaxyService(self.db)
            node_id = galaxy.sprint_node_uuid(pack_node_id)
            if await self.db.get(KnowledgeNode, node_id) is None:
                metadata = await galaxy.ensure_sprint_node(pack_node_id)
                if metadata is not None:
                    return metadata
            return node_id

        topic_slug = slug or name
        node_id = _diagnostic_topic_node_uuid(topic_slug)
        if await self.db.get(KnowledgeNode, node_id) is not None:
            return node_id
        self.db.add(
            KnowledgeNode(
                id=node_id,
                name=(name or topic_slug)[:255],
                description=f"诊断小测主题节点：{name or topic_slug}",
                keywords=[topic_slug],
                importance_level=3,
                is_seed=True,
                source_type="exam_diagnostic",
                status="published",
            )
        )
        await self.db.flush()
        return node_id

    async def _write_mastery_value(self, *, user_id: UUID, node_id: UUID, mastery: float) -> None:
        bind = self.db.get_bind()
        dialect = getattr(getattr(bind, "dialect", None), "name", "")
        if dialect and dialect != "sqlite":
            try:
                await GalaxyService(self.db).update_node_mastery(
                    user_id=user_id,
                    node_id=node_id,
                    new_mastery=int(round(mastery)),
                    reason="exam_sprint_diagnostic",
                )
                return
            except Exception as exc:
                logger.warning("GalaxyService diagnostic mastery write failed, falling back to direct upsert: {}", exc)
                await self.db.rollback()
        await self._upsert_mastery_direct(user_id=user_id, node_id=node_id, mastery=mastery)
        await self.db.commit()

    async def _upsert_mastery_direct(self, *, user_id: UUID, node_id: UUID, mastery: float) -> None:
        status = await self.db.get(UserNodeStatus, {"user_id": user_id, "node_id": node_id})
        now = _utcnow()
        mastery = max(0.0, min(100.0, float(mastery)))
        if status is None:
            status = UserNodeStatus(
                user_id=user_id,
                node_id=node_id,
                mastery_score=mastery,
                bkt_mastery_prob=max(0.0, min(mastery / 100.0, 1.0)),
                bkt_last_updated_at=now,
                updated_at=now,
                last_study_at=now,
                last_interacted_at=now,
                is_unlocked=True,
                revision=1,
                total_minutes=0,
                total_study_minutes=0,
                study_count=0,
                is_collapsed=False,
                is_favorite=False,
                decay_paused=False,
                created_at=now,
            )
            self.db.add(status)
        else:
            status.mastery_score = mastery
            status.bkt_mastery_prob = max(0.0, min(mastery / 100.0, 1.0))
            status.bkt_last_updated_at = now
            status.updated_at = now
            status.last_study_at = now
            status.last_interacted_at = now
            status.is_unlocked = True
            status.revision = int(status.revision or 0) + 1
        await self.db.flush()

    async def _resolve_node_id_by_name(self, name: str) -> UUID | None:
        result = await self.db.execute(select(KnowledgeNode.id).where(KnowledgeNode.name == name).limit(1))
        return result.scalar_one_or_none()

    async def _persist_profile_diagnostic_summary(
        self,
        *,
        user_id: UUID,
        subject: str,
        days_left: int,
        estimated_score_now: float,
        pass_probability: float,
        recommended_path: RecommendedPath,
        top_bottlenecks: list[DiagnosticBottleneck],
        node_mastery_updates: list[DiagnosticMasteryUpdate],
        coverage_domains: list[str],
    ) -> None:
        explicit_result = await self.db.execute(select(UserPreferencesCenter.explicit).where(UserPreferencesCenter.user_id == user_id))
        explicit = explicit_result.scalar_one_or_none() or {}
        explicit = explicit if isinstance(explicit, dict) else {}
        cold_start = explicit.get("cold_start_context")
        cold_start = dict(cold_start) if isinstance(cold_start, dict) else {}
        cold_start.update(
            {
                "subject": cold_start.get("subject") or subject,
                "time_constraint_days": cold_start.get("time_constraint_days") or days_left,
                "diagnostic_estimated_score": estimated_score_now,
                "diagnostic_pass_probability": pass_probability,
                "recommended_path": recommended_path.value,
                "diagnostic_top_bottlenecks": [item.node_name for item in top_bottlenecks],
                "diagnostic_node_mastery_snapshot": [
                    {
                        "node_id": str(item.node_id) if item.node_id else None,
                        "node_name": item.node_name,
                        "node_slug": item.node_slug,
                        "mastery": item.mastery,
                    }
                    for item in node_mastery_updates
                ],
                "diagnostic_coverage_domains": list(coverage_domains),
                "diagnostic_updated_at": _utcnow().isoformat(),
            }
        )
        knowledge_gaps = [
            {
                "id": f"diag-gap:{item.node_slug or item.node_name}",
                "description": item.reason,
                "node_name": item.node_name,
                "mastery": item.mastery,
                "source": "exam_sprint_diagnose",
                "created_at": _utcnow().isoformat(),
            }
            for item in top_bottlenecks
        ]
        await ProfileWriteService(self.db).set_explicit_preferences(
            user_id=user_id,
            updates={"cold_start_context": cold_start, "knowledge_gaps": knowledge_gaps},
            evidence_refs_by_key={
                "cold_start_context": [{"type": "system", "id": "exam_sprint_diagnose"}],
                "knowledge_gaps": [{"type": "system", "id": "exam_sprint_diagnose"}],
            },
            confidence_by_key={"cold_start_context": 0.85, "knowledge_gaps": 0.85},
            source_type="system",
            source="exam_sprint_diagnostic_service",
        )

    def _build_confidence_calibration(self, stats: dict[str, int]) -> dict[str, float]:
        certain_total = max(stats["certain_total"], 1)
        guess_total = max(stats["guess_total"], 1)
        return {
            "certain_accuracy": round(stats["certain_correct"] / certain_total, 3),
            "guess_accuracy": round(stats["guess_correct"] / guess_total, 3),
            "overconfidence_miss_rate": round(stats["overconfidence_miss"] / certain_total, 3),
        }

    def _top_mistake_clusters(self, counter: Counter[str]) -> list[dict[str, Any]]:
        return [{"tag": key, "count": value} for key, value in counter.most_common(4)]

    def _coverage_domains(self, questions: list[DiagnosticQuestionPrompt]) -> list[str]:
        seen: list[str] = []
        for question in questions:
            if question.domain == "综合题":
                continue
            if question.domain not in seen:
                seen.append(question.domain)
        return seen

    def _load_pack_payload(
        self,
        *,
        sprint_pack_id: str | None,
        sprint_pack_path: str | None,
    ) -> dict[str, Any]:
        if sprint_pack_path:
            return json.loads(Path(sprint_pack_path).read_text(encoding="utf-8"))
        target = sprint_pack_id or EXAM_PREP_14D_PACK_ID
        if target == EXAM_PREP_14D_PACK_ID:
            return json.loads(EXAM_PREP_14D_MANIFEST_PATH.read_text(encoding="utf-8"))
        return json.loads(EXAM_PREP_14D_MANIFEST_PATH.read_text(encoding="utf-8"))

    def _extract_question_archetypes(self, pack_payload: dict[str, Any], subject: str) -> list[str]:
        raw = pack_payload.get("question_archetypes")
        if isinstance(raw, list) and raw:
            return [str(item) for item in raw if str(item).strip()]
        if _contains_network_subject(subject):
            return list(_CN_QUESTION_ARCHETYPES)
        subject_set = _SUBJECT_TEMPLATE_SETS.get(_resolve_subject_pack_key(subject) or "")
        if subject_set is not None:
            return list(subject_set.archetypes)
        return ["high_frequency_concept_judgment", "process_trace"]

    def _extract_checkpoint_template(self, pack_payload: dict[str, Any], subject: str) -> str:
        raw = pack_payload.get("checkpoint_templates")
        if isinstance(raw, dict):
            for value in raw.values():
                if isinstance(value, dict) and value.get("template_id"):
                    return str(value["template_id"])
        if isinstance(raw, list) and raw:
            first = raw[0]
            if isinstance(first, dict) and first.get("template_id"):
                return str(first["template_id"])
            if isinstance(first, str):
                return first
        if _contains_network_subject(subject):
            return _CN_CHECKPOINT_TEMPLATE
        return "mixed_mastery_probe_v1"

    def _canonical_slug(self, value: str | None) -> str:
        text = _normalize_text(value or "")
        if not text:
            return ""
        if any(token in text for token in ("拥塞", "congestion")):
            return "tcp_congestion_control"
        if any(token in text for token in ("可靠", "ack", "窗口", "传输控制")):
            return "tcp_reliable_transport"
        if any(token in text for token in ("子网", "subnet", "掩码")):
            return "ip_subnetting"
        if any(token in text for token in ("路由", "routing", "前缀")):
            return "routing_basics"
        if any(token in text for token in ("http", "dns", "域名")):
            return "http_dns"
        if any(token in text for token in ("链路", "mac", "crc", "以太网")):
            return "link_layer_basics"
        if any(token in text for token in ("分层", "协议栈", "osi", "tcpip")):
            return "layering_protocol_stack"
        return text[:80]
