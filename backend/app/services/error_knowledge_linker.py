"""
ErrorKnowledgeLinker — 错题→知识节点确定性归位（CP-03，零 LLM 优先）。

断环背景（v3-output/NORTHSTAR-LOOP1 CP-03 + P1-5 §6）：
  错题落本成功、review 触发的 mastery 同步也已接线，但同步依赖
  ``error_record.linked_knowledge_node_ids``——该字段此前只由 analyze_and_link
  的向量检索/LLM 链路产出，冷启动或检索失败时为空 → mastery 同步合法 no-op，
  星图对错题零反应（「半程失败」）。

本服务在 LLM/向量检索之前插入一条**零 LLM 的确定性归位链**：

  1. 考纲词典（sprint pack）：科目 → pack → 章节/题目文本与节点 label /
     node_id / 章节提示词典做 alnum 归一化包含匹配（GalaxyService P0-1
     匹配模式复用）→ 命中经 ``GalaxyService.ensure_sprint_node`` 解析到
     canonical 星图节点（缺失才建，确定性 uuid5，幂等）；
  2. 星图节点名：用户可见节点（种子或已有 UserNodeStatus）的
     name/name_en/keywords 与章节/题目文本做同样的归一化匹配。

LLM 兜底（不在本服务内发起任何 LLM 调用）：
  analyze_and_link 在确定性链与向量检索都落空时，把**既有 LLM 分析调用**
  返回的 ``recommended_knowledge`` 概念名作为 concept_hints 传入本服务做
  同样的确定性字符串匹配——即「LLM 归位」复用既有分析调用的产物，
  零新增直发点/预算消耗（AY / P2DISPATCH 面零变化）。

幂等：归位是 (错题内容, 词典) 的纯函数——同一错题重复归位得到同一节点集
（去重、封顶 MAX_LINKED_NODES），重复调用不产生累积或重复链接。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select

from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.schemas.error_book import SUBJECT_TO_SPRINT_PACK, normalize_subject
from app.sprint_packs.sprint_pack_registry import PACKS_DIR

# ---------------------------------------------------------------------------
# Matching primitives（GalaxyService._pack_node_match_key 同款归一化）
# ---------------------------------------------------------------------------

# 子串包含匹配的最短 key 长度（alnum 归一化后；中文按字符计）。
# 防止「树」「图」等单字节点名/短词把任意题目文本误链到节点。
MIN_CONTAINMENT_KEY_LEN = 4

# 与 mastery sync 的 top-3 上限对齐
MAX_LINKED_NODES = 3

# 题目文本参与匹配的最大长度（防超长文本的键值膨胀）
MAX_MATCH_TEXT_CHARS = 600


def _match_key(value: Any) -> str:
    """alnum 归一化匹配键（与 GalaxyService._pack_node_match_key 同规则）。"""
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


# ---------------------------------------------------------------------------
# Sprint pack 词典（进程级缓存，与 exam_sprint_diagnostic_service 同款模式）
# ---------------------------------------------------------------------------

# pack_key → 节点前缀（CHAPTER_NODE_HINTS 的作用域过滤用）
_PACK_PREFIXES: dict[str, str] = {
    "discrete_mathematics": "dm",
    "data_structures_algorithms": "ds",
    "computer_networks": "cn",
    "operating_systems": "os",
    "mathematics": "math",
}

# 进程级缓存：(pack_key, node_id, label_key) 全集
_PACK_NODE_INDEX_CACHE: list[tuple[str, str, str]] | None = None


def _pack_node_index() -> list[tuple[str, str, str]]:
    """扫描 sprint_packs/*_v1.json 构建 (pack_key, node_id, label_key) 索引。

    坏包优雅跳过（与 loader 的 None 容错同口径），索引进程内缓存。
    """
    global _PACK_NODE_INDEX_CACHE
    if _PACK_NODE_INDEX_CACHE is not None:
        return _PACK_NODE_INDEX_CACHE
    index: list[tuple[str, str, str]] = []
    for path in sorted(Path(PACKS_DIR).glob("*_v1.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.debug("ErrorKnowledgeLinker: failed to read pack {}: {}", path, exc)
            continue
        pack_key = str(payload.get("id") or path.stem).split("@", 1)[0]
        for node in payload.get("knowledge_nodes") or []:
            node_id = str(node.get("node_id") or "").strip()
            label_key = _match_key(node.get("label"))
            if node_id and label_key:
                index.append((pack_key, node_id, label_key))
    _PACK_NODE_INDEX_CACHE = index
    return index


# 章节提示词典：高频章节关键词 → 完整 external node id。
# 为什么需要它：章节常只写「欧拉图」，而节点 label 是「欧拉图与哈密顿图」，
# 纯 label 包含匹配会漏。提示词均为 ≥2 字的特异词，避免单字误链。
CHAPTER_NODE_HINTS: dict[str, str] = {
    # --- 离散数学 dm.* ---
    "命题逻辑": "dm.propositional_logic",
    "主析取范式": "dm.propositional_logic",
    "主合取范式": "dm.propositional_logic",
    "谓词逻辑": "dm.predicate_logic",
    "量词": "dm.predicate_logic",
    "集合及其运算": "dm.set_theory",
    "集合运算": "dm.set_theory",
    "集合论": "dm.set_theory",
    "二元关系": "dm.binary_relations",
    "等价关系": "dm.binary_relations",
    "偏序": "dm.binary_relations",
    "函数与基数": "dm.functions_cardinality",
    "基数": "dm.functions_cardinality",
    "图的基本概念": "dm.graph_basics",
    "图论": "dm.graph_basics",
    "连通图": "dm.graph_basics",
    "欧拉": "dm.euler_hamilton",
    "哈密顿": "dm.euler_hamilton",
    "一笔画": "dm.euler_hamilton",
    "生成树": "dm.trees",
    "组合计数": "dm.combinatorics",
    "排列组合": "dm.combinatorics",
    "鸽巢原理": "dm.combinatorics",
    "抽屉原理": "dm.combinatorics",
    "代数系统": "dm.algebraic_structures",
    "群论": "dm.algebraic_structures",
    "子群": "dm.algebraic_structures",
    "循环群": "dm.algebraic_structures",
    "布尔代数": "dm.algebraic_structures",
    # --- 数据结构 ds.* ---
    "顺序表": "ds.array",
    "链表": "ds.linked_list",
    "循环队列": "ds.circular_queue",
    "串匹配": "ds.string_matching",
    "KMP": "ds.string_matching",
    "二叉树": "ds.binary_tree",
    "二叉排序树": "ds.bst",
    "平衡二叉树": "ds.avl_tree",
    "哈夫曼": "ds.huffman_tree",
    "拓扑排序": "ds.topological_sort",
    "关键路径": "ds.critical_path",
    "最短路径": "ds.dijkstra",
    "迪杰斯特拉": "ds.dijkstra",
    "dijkstra": "ds.dijkstra",
    "普里姆": "ds.prim",
    "prim": "ds.prim",
    "克鲁斯卡尔": "ds.kruskal",
    "kruskal": "ds.kruskal",
    "并查集": "ds.union_find",
    "散列表": "ds.hash_table",
    "哈希表": "ds.hash_table",
    "折半查找": "ds.binary_search",
    "快速排序": "ds.quicksort",
    "冒泡排序": "ds.bubble_sort",
    "归并排序": "ds.merge_sort",
    "堆排序": "ds.heap_sort",
    "希尔排序": "ds.shell_sort",
    "基数排序": "ds.radix_sort",
    "时间复杂度": "ds.time_complexity",
    "空间复杂度": "ds.space_complexity",
    "动态规划": "ds.dynamic_programming",
    "贪心算法": "ds.greedy",
    "分治": "ds.divide_conquer",
    "回溯": "ds.backtracking",
    "分支限界": "ds.branch_bound",
    "广度优先": "ds.bfs",
    "深度优先": "ds.dfs",
    # --- 计算机网络 cn.* ---
    "osi": "cn.osi_model",
    "三次握手": "cn.tcp_three_way",
    "四次挥手": "cn.tcp_four_way",
    "拥塞控制": "cn.tcp_congestion_control",
    "滑动窗口": "cn.tcp_flow_control",
    "流量控制": "cn.flow_control",
    "子网划分": "cn.subnetting",
    "cidr": "cn.subnetting",
    "子网掩码": "cn.subnetting",
    "arp": "cn.arp",
    "icmp": "cn.icmp",
    "ipv6": "cn.ipv6_basics",
    "路由": "cn.routing_basics",
    "rip": "cn.routing_rip",
    "ospf": "cn.routing_ospf",
    "bgp": "cn.routing_bgp",
    "dns": "cn.dns",
    "域名解析": "cn.dns",
    "以太网": "cn.ethernet",
    "csma": "cn.mac_protocols",
    "差错检测": "cn.error_detection",
    "crc": "cn.error_detection",
    "海明码": "cn.error_detection",
    "多路复用": "cn.multiplexing",
    "nat": "cn.nat",
    "网络地址转换": "cn.nat",
    "http": "cn.http",
    "udp": "cn.udp",
    # --- 操作系统 os.* ---
    "进程状态": "os.process_states",
    "pcb": "os.process_concept",
    "时间片轮转": "os.rr_scheduling",
    "先来先服务": "os.fcfs_scheduling",
    "短作业优先": "os.sjf_scheduling",
    "多级反馈": "os.multilevel_feedback_queue",
    "信号量": "os.semaphore_pv",
    "pv操作": "os.semaphore_pv",
    "临界区": "os.synchronization_concepts",
    "生产者消费者": "os.producer_consumer",
    "读者写者": "os.reader_writer",
    "哲学家进餐": "os.dining_philosophers",
    "死锁": "os.deadlock_conditions",
    "银行家算法": "os.banker_algorithm",
    "页面置换": "os.fifo_replacement",
    "lru": "os.lru_replacement",
    "缺页": "os.page_fault_process",
    "页表": "os.paging_basics",
    "分段": "os.segmentation_basics",
    "抖动": "os.working_set_thrashing",
    "磁盘调度": "os.sstf_scheduling",
    "中断": "os.interrupt_handling",
    # --- 高等数学/线代 math.* ---
    "洛必达": "math.lhopital_rule",
    "等价无穷小": "math.equivalent_infinitesimal",
    "夹逼准则": "math.sequence_limits",
    "间断点": "math.continuity_discontinuity",
    "中值定理": "math.mean_value_theorem",
    "隐函数求导": "math.implicit_parametric_derivative",
    "分部积分": "math.integration_by_parts",
    "换元积分": "math.substitution_integral",
    "牛顿莱布尼茨": "math.newton_leibniz",
    "广义积分": "math.improper_integral",
    "二重积分": "math.double_integral_rectangular",
    "偏导数": "math.partial_derivatives",
    "全微分": "math.total_differential",
    "泰勒": "math.taylor_series",
    "幂级数": "math.power_series",
    "级数收敛": "math.series_basic_convergence",
    "行列式": "math.determinant_definition",
    "矩阵的秩": "math.matrix_rank",
    "初等变换": "math.elementary_transformations",
    "伴随矩阵": "math.inverse_matrix",
    "高斯消元": "math.linear_system_gaussian",
    "克拉默": "math.cramers_rule",
    "基础解系": "math.homogeneous_system_solution_space",
    "线性相关": "math.vector_space_linear_dependence",
    "线性无关": "math.vector_space_linear_dependence",
    "特征值": "math.eigenvalues_eigenvectors",
    "特征向量": "math.eigenvalues_eigenvectors",
    "对角化": "math.diagonalization",
    "相似矩阵": "math.matrix_similarity",
    "二次型": "math.quadratic_form",
    "正定矩阵": "math.positive_definite_matrix",
}

# 进程级缓存：hint key → (node_prefix, ext_id)，按 key 长度降序（特异性优先）
_HINT_INDEX_CACHE: list[tuple[str, str, str]] | None = None


def _hint_index() -> list[tuple[str, str, str]]:
    global _HINT_INDEX_CACHE
    if _HINT_INDEX_CACHE is None:
        _HINT_INDEX_CACHE = sorted(
            ((_match_key(hint), str(ext_id).split(".", 1)[0], ext_id) for hint, ext_id in CHAPTER_NODE_HINTS.items()),
            key=lambda item: len(item[0]),
            reverse=True,
        )
    return _HINT_INDEX_CACHE


# ---------------------------------------------------------------------------
# Linker
# ---------------------------------------------------------------------------


@dataclass
class KnowledgeLinkMatch:
    """一条确定性归位结果。"""

    node_id: UUID
    source: str  # sprint_pack | node_name
    detail: str = ""


class ErrorKnowledgeLinker:
    """错题→知识节点确定性归位（零 LLM；LLM 兜底仅消费既有调用的概念产物）。"""

    def __init__(self, db):
        self.db = db

    async def link_error(
        self,
        *,
        user_id: UUID,
        error: Any,
        concept_hints: list[str] | None = None,
    ) -> list[KnowledgeLinkMatch]:
        """为错题返回确定性解析出的知识节点（≤ MAX_LINKED_NODES，去重）。

        匹配文本源（按确定性递减）：chapter → question_text（截断）→
        concept_hints（LLM recommended_knowledge 等概念名词，仍走纯字符串匹配）。
        匹配不到返回空列表——诚实 none，不造节点（sprint 词典节点除外，
        其创建本身是 P0-1 ensure_sprint_node 的既有确定性语义）。
        """
        subject_enum = normalize_subject(getattr(error, "subject_code", None))
        texts = [
            str(getattr(error, "chapter", None) or "").strip(),
            str(getattr(error, "question_text", None) or "").strip()[:MAX_MATCH_TEXT_CHARS],
            *(str(hint).strip() for hint in (concept_hints or []) if str(hint or "").strip()),
        ]
        texts = [text for text in texts if text]
        if not texts:
            return []

        text_key = _match_key(" ".join(texts))
        if not text_key:
            return []

        matches: list[KnowledgeLinkMatch] = []
        seen: set[UUID] = set()

        # --- 链 1：考纲 sprint pack 词典（subject 定 scope；未知科目全局扫） ---
        pack_key = SUBJECT_TO_SPRINT_PACK.get(subject_enum) if subject_enum else None
        for ext_id, detail in self._match_pack_nodes(pack_key, text_key):
            if len(matches) >= MAX_LINKED_NODES:
                break
            node_id = await self._ensure_sprint_node(ext_id)
            if node_id is None or node_id in seen:
                continue
            seen.add(node_id)
            matches.append(KnowledgeLinkMatch(node_id=node_id, source="sprint_pack", detail=detail))

        # --- 链 2：星图既有节点名（种子/用户节点，P0-1 同款可见性） ---
        if len(matches) < MAX_LINKED_NODES:
            for node_id, detail in await self._match_galaxy_node_names(user_id, text_key):
                if node_id in seen:
                    continue
                seen.add(node_id)
                matches.append(KnowledgeLinkMatch(node_id=node_id, source="node_name", detail=detail))
                if len(matches) >= MAX_LINKED_NODES:
                    break

        return matches

    # -------------------------------------------------------------------
    # 链 1：pack 词典匹配
    # -------------------------------------------------------------------

    def _match_pack_nodes(self, pack_key: str | None, text_key: str) -> list[tuple[str, str]]:
        """返回 [(external_node_id, detail)]，scoped 优先、特异性降序。"""
        index = _pack_node_index()
        hints = _hint_index()

        scoped = pack_key in _PACK_PREFIXES
        pack_prefix = _PACK_PREFIXES.get(pack_key, "") if scoped else ""

        label_hits: list[tuple[int, str, str]] = []
        hint_hits: list[tuple[int, str, str]] = []

        for candidate_pack, node_id, label_key in index:
            if scoped and candidate_pack != pack_key:
                continue
            if len(label_key) >= MIN_CONTAINMENT_KEY_LEN and label_key in text_key:
                label_hits.append((len(label_key), node_id, f"label:{node_id}"))

        for hint_key, hint_prefix, ext_id in hints:
            if scoped and hint_prefix != pack_prefix:
                continue
            if hint_key and hint_key in text_key:
                hint_hits.append((len(hint_key), ext_id, f"hint:{ext_id}"))

        # scoped 无命中且科目未知时已自动全局扫（scoped=False 即全量）；
        # 科目已知但 scoped 无命中——保守不跨科（数学 label 撞进离散题会错链）。
        ordered = sorted(label_hits + hint_hits, key=lambda item: item[0], reverse=True)
        result: list[tuple[str, str]] = []
        seen_ext: set[str] = set()
        for _score, ext_id, detail in ordered:
            if ext_id in seen_ext:
                continue
            seen_ext.add(ext_id)
            result.append((ext_id, detail))
        return result

    async def _ensure_sprint_node(self, external_node_id: str) -> UUID | None:
        """解析/按需创建 canonical sprint 节点（P0-1 既有确定性语义）。"""
        try:
            from app.services.galaxy_service import GalaxyService

            return await GalaxyService(self.db).ensure_sprint_node(external_node_id)
        except Exception as exc:
            logger.warning("ErrorKnowledgeLinker: ensure_sprint_node({}) failed: {}", external_node_id, exc)
            return None

    # -------------------------------------------------------------------
    # 链 2：星图节点名匹配
    # -------------------------------------------------------------------

    async def _match_galaxy_node_names(self, user_id: UUID, text_key: str) -> list[tuple[UUID, str]]:
        """在用户可见节点（种子或已有状态）的 name/name_en/keywords 里做包含匹配。"""
        try:
            stmt = (
                select(KnowledgeNode)
                .outerjoin(
                    UserNodeStatus,
                    (UserNodeStatus.node_id == KnowledgeNode.id) & (UserNodeStatus.user_id == user_id),
                )
                .where(
                    KnowledgeNode.not_deleted_filter(),
                    KnowledgeNode.name.isnot(None),
                    (KnowledgeNode.is_seed.is_(True)) | (UserNodeStatus.user_id.isnot(None)),
                )
            )
            rows = (await self.db.execute(stmt)).scalars().all()
        except Exception as exc:
            logger.warning("ErrorKnowledgeLinker: galaxy node name scan failed: {}", exc)
            return []

        hits: list[tuple[int, UUID, str]] = []
        for node in rows:
            candidates: list[str] = []
            for value in (
                getattr(node, "name", None),
                getattr(node, "name_en", None),
            ):
                key = _match_key(value)
                if key:
                    candidates.append(key)
            keywords = getattr(node, "keywords", None)
            if isinstance(keywords, dict):
                keyword_values = [*keywords.keys(), *keywords.values()]
            elif isinstance(keywords, list):
                keyword_values = keywords
            else:
                keyword_values = []
            for value in keyword_values:
                key = _match_key(value)
                if key and key != _match_key(getattr(node, "name", None)):
                    candidates.append(key)

            best = 0
            for key in set(candidates):
                if key == text_key or (len(key) >= MIN_CONTAINMENT_KEY_LEN and key in text_key):
                    best = max(best, len(key))
            if best:
                hits.append((best, node.id, f"node_name:{node.name}"))

        hits.sort(key=lambda item: item[0], reverse=True)
        return [(node_id, detail) for _score, node_id, detail in hits]
