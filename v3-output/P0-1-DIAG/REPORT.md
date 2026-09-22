# P0-1 · 诊断题包支持离散数学（修北极星主路径第一步断点 BP-1）

> worktree wt98-v3（基于 main@24c827fd）· 2026-09-22 · 交付：`changes.patch` + 本报告
> 证据锚点：`v3-output/NORTHSTAR-LOOP1/REPORT.md` BP-1 + `evidence/steps/B4_diagnostic-generate--pretest.json`（`subject=离散数学, question_count=15, days_left=7, pass_score=60.0` → 422「离散数学暂未内置诊断题包」）

---

## 0. 收执（任务卡四问）

1. **题包规模**：22 题（19 单选 + 3 简答，其中 1 题为综合简答），9 个非综合知识领域 + 综合题，核心键 7 题跨 7 领域（≥5 领域门禁在 question_count 10..15 全段成立）；题包结构与既有 cn/ds 科目**同构**（同一 `QuestionTemplate` 数据结构、同一判卷器、同一 `_SUBJECT_TEMPLATE_SETS` 注册面），结构一致性由新增测试 `test_discrete_mathematics_pack_structure_and_grading_invariants` 程序化锁定。
2. **diagnose 端到端验证**：三层——①纯逻辑判卷不变量（每题正确答案 1.0 分、错误选项文本 0 分、SA 正确关键词 1.0 分）；②服务级端到端（pytest+sqlite：generate(subject=离散数学,**与 B4 相同请求面**)→按模板注册表作答→grade(update_galaxy=True)→掌握度落 `user_node_status` 且解析到 canonical `dm.*` sprint-pack 星图节点，图论链答错时瓶颈指向欧拉/哈密顿）；③API 路由层既有 `test_exam_sprint_diagnose_api.py` 全过。全静态模板+确定性判卷，**无 LLM、无预算面**。
3. **星图节点映射**：新建 `discrete_mathematics_v1.json`（`dm.*` 10 节点，覆盖 NS-001 考纲全部 6 章 CH1-CH6 的章级面）；诊断题 linked_slug 全部经 P1-E3 既有模式（`_pack_node_suffix_index` → `GalaxyService.ensure_sprint_node`）解析到 canonical `dm.*` 节点（9/10 节点被诊断触达，`dm.trees` 为章面保留、可被规划触达）。**未做 24 细粒度节点大迁徙**（journey spec 的 `dm.chX_*.01..04` 留后续卡）。
4. **收工核查**：见 §6。

---

## 1. 摸底结论（修复前机制）

- 题包机制：`backend/app/services/exam_sprint_diagnostic_service.py`。科目白名单 = `_SUBJECT_TEMPLATE_SETS`（此前仅 `computer_networks`、`data_structures_algorithms`），**题目为静态内置模板**（`QuestionTemplate`：题型/题干/选项/正确项/SA 关键词判卷/错误标签/挂靠节点 slug/分值/预估用时），判卷确定性（`_score_choice_answer` 支持 index/字母/选项文本，`_score_short_answer` 关键词比值部分给分），无 LLM 出题。
- 答案钥匙不回传客户端（P1-E4：server-side session by `diagnostic_id`）。
- 挂靠节点解析（P1-E3）：模板 `linked_node_slugs` → 精选别名 → sprint-pack 节点后缀索引（扫 `app/sprint_packs/*_v1.json` 的 `knowledge_nodes[].node_id` 后缀）→ `ensure_sprint_node` 按需创建 canonical 星图节点 → 兜底确定性诊断主题节点。**LOOP1 所述「考纲→星图映射不存在」的根因即：无离散数学 pack、无 dm.* 节点、白名单不含该科目。**
- sprint pack JSON 消费方（registry/loader/planning/review/dashboard/aurora）对缺失 pack 均有 None 容错（LOOP1 期间离散数学即走 None 分支成功生成 backbone）——新增合法 pack 为纯增强，坏 pack 会优雅回落为 None（loader 校验 `SprintPackV1` 失败仅告警返回 None）。

## 2. 变更面（changes.patch）

| 文件 | 变更 |
|---|---|
| `backend/app/sprint_packs/discrete_mathematics_v1.json` | **新增**。schema 合法（`SprintPackV1` 校验通过）：`dm.*` 10 节点（layer=ch1..ch6）、8 错误类型、6 题型原型、minimum_pass/score_max 双路径、7d/14d 策略、24h 策略、aurora 规则、检查点规则、1 任务卡模板、优先级公式 |
| `backend/app/sprint_packs/sprint_pack_loader.py` | `_SUBJECT_ALIASES` 增补：离散数学/离散/discrete(_math)(ematics) → `discrete_mathematics` |
| `backend/app/services/exam_sprint_diagnostic_service.py` | 新增 `_DM_DEFAULT_NODES`（10，slug=pack 节点后缀）、`_DM_TEMPLATES`（22 题）、`_DM_CORE_TEMPLATE_KEYS`（7）、注册 `_SUBJECT_TEMPLATE_SETS["discrete_mathematics"]`；`_SUPPORTED_SUBJECT_HINT` →「计算机网络、数据结构、离散数学」 |
| `backend/tests/unit/test_exam_sprint_diagnostic_service.py` | 新增 3 测试（§4） |

**红线自查**：未动其他科目题包（cn/ds 模板零 diff）；diagnose 流程无 LLM/预算面、不涉 P2DISPATCH；API 契约不变（`DiagnosticGenerateRequest/Response` 字段零改动，仅原 422 科目变 200）；幂等（generate 无状态、session 按每次 uuid4 键、`ensure_sprint_node` 确定性 uuid5 + 缺失才建）；无 proto/DB 迁移改动；`_canonical_slug`（CN 专用启发式）未触碰。

## 3. 题目清单与逐题正确性自检（教育内容质量门）

> 判卷面符号：正确项=选项文本（单选）；SA 关键词=满分判定词。自检结论列给出「为什么对」的数学依据。

### CH1 数理逻辑（命题逻辑 dm.propositional_logic / 谓词逻辑 dm.predicate_logic）

| # | template_key | 考点 | 正确答案 | 自检（为什么对） |
|---|---|---|---|---|
| 1 | dm_logic_tautology | 重言式判定 | B. p∨¬p | 排中律恒真；A p→q 在 p=T,q=F 为假；C 矛盾式恒假；D 括号内 p→p 恒真故整体恒假 |
| 2 | dm_logic_implication_equiv（核心） | 蕴含等值式 | A. ¬p∨q | p→q 仅在 p=T,q=F 假；¬p∨q 真值表逐行同值（材料蕴含的析取定义） |
| 3 | dm_logic_biconditional | 等价联结词语义 | C. 真值相同 | p↔q 真值表：p=q 时为真（可同真可同假）；A/B 各只覆盖一半，D 相反 |
| 4 | dm_sa_modus_tollens | 拒取式推理 | p 为**假**；规则=**拒取式** | (p→q)∧¬q⇒¬p：q=F 且蕴含真 ⇒ p 必假（若 p 真则 q 真，矛盾） |
| 5 | dm_predicate_negation（核心） | 量词否定 | B. ∃x¬F(x) | 量词否定等值式 ¬∀xF(x)⇔∃x¬F(x)；A 语义为「全不」；C=¬∀x¬F(x)；D⇔∀xF(x) |
| 6 | dm_predicate_bound_variable | 量词辖域/约束变元 | A. 约束变元 | y 在 ∃y 辖域内被量词约束；非自由（自由=不受任何量词约束）、非常项 |

### CH2 集合论（dm.set_theory）/ 二元关系（dm.binary_relations）

| # | template_key | 考点 | 正确答案 | 自检 |
|---|---|---|---|---|
| 7 | dm_set_union_absorption | 并的吸收律 | C. A⊆B | A∪B=B ⇔ A⊆B（并的元素来自两者，B 并 A 仍为 B 当且仅当 A 不引入新元素）；A 仅在 A=B 时；B 充分不必要；D 反例 A={1},B={2} |
| 8 | dm_sa_set_laws | 运算律命名 | **交换**律；**结合**律 | A∪B=B∪A 交换次序→交换律；A∩(B∩C)=(A∩B)∩C 改变结合方式→结合律 |
| 9 | dm_relation_equivalence | 等价关系定义 | A. 等价关系 | 自反+对称+传递即等价关系定义；偏序=自反+**反对称**+传递；全序还需两两可比；相容=自反+对称（缺传递） |
| 10 | dm_relation_equivalence_count（核心） | 划分计数（Bell 数） | B. 5 | 三元集划分恰 5 个：{123},{1\|23},{2\|13},{3\|12},{1\|2\|3}，划分↔等价关系一一对应 |
| 11 | dm_relation_identity_properties | 恒等关系性质 | C. 四性全有 | I_A：∀x(xIx) 自反；xIy⇒x=y 推出 yIx 对称、且 x=y 反对称；传递显然。A 错在「对称与反对称可共存」——经典辨析点 |

### CH3 函数与基数（dm.functions_cardinality）

| # | template_key | 考点 | 正确答案 | 自检 |
|---|---|---|---|---|
| 12 | dm_function_injection_count（核心） | 单射计数 | B. 24 | P(4,3)=4×3×2=24（逐像两两不同）；12 漏一因子；64=4³ 为全函数数；81=3⁴ 方向反 |
| 13 | dm_function_bijection | 双射判定 | C. f(x)=x+1 | Z 上平移可逆：单射（x+1=y+1⇒x=y）且满射（任 y 取 x=y−1）；A 撞 x²=f(−x)；B 单不满（1 无原像）；D 常函数 |

### CH4 图论（dm.graph_basics / dm.euler_hamilton；dm.trees 为章面节点暂无诊断题）

| # | template_key | 考点 | 正确答案 | 自检 |
|---|---|---|---|---|
| 14 | dm_graph_complete_edges | 完全图边数 | B. 10 | C(5,2)=5×4/2=10；5/20/25 分别为漏乘 (n−1)/漏除 2/错用 n² |
| 15 | dm_graph_degree_sequence | 握手定理（奇偶） | D. (1,1,1,2) | 度数总和=2×边数必为偶，D 和=5 奇 ⇒ 不可能；A 和 4（两独立边）、B 和 8（C4）、C 和 8（a-b,a-c,a-d,b-c）均给出构造图验证可图化 |
| 16 | dm_graph_euler_circuit（核心） | 欧拉回路充要条件 | A. 所有顶点度数为偶 | 欧拉定理：连通图有欧拉回路⇔全偶度；B 为欧拉**通路**（非回路）条件——正是 NS-001「欧拉/哈密顿混淆」痛点；C 充分不必要；D 总度为奇不可能 |
| 17 | dm_graph_hamilton | 哈密顿回路定义 | B. 过每顶点恰一次 | 哈密顿看**点**，欧拉看**边**（A）；C 是欧拉条件；D 反例：星图 K1,3 |

### CH5 组合计数（dm.combinatorics）

| # | template_key | 考点 | 正确答案 | 自检 |
|---|---|---|---|---|
| 18 | dm_combination_committee（核心） | 组合计数 | B. 20 | C(6,3)=6!/(3!3!)=20（不分序）；15=C(6,2)；30=P(6,2)；120=P(6,3) 计序 |
| 19 | dm_pigeonhole_sum11 | 鸽巢原理 | B. 6 | 配对 {1,10},{2,9},{3,8},{4,7},{5,6} 共 5 组，取 6 个必有同组对和=11；取 5 个可各组取一（1,2,3,4,5）无和 11 ⇒ 最少保证数=6 |

### CH6 代数系统（dm.algebraic_structures）

| # | template_key | 考点 | 正确答案 | 自检 |
|---|---|---|---|---|
| 20 | dm_algebra_group | 群判定 | D. ⟨Z,+⟩ | 结合+单位元 0+逆元 −a；A 减法不结合 ((1−2)−3≠1−(2−3))；B 缺逆元；C 除 ±1 缺逆元 |
| 21 | dm_algebra_element_order | 循环群元素阶 | D. 3（文本"3"，位于选项 D 位） | 2¹=2, 2²=4, 2³=6≡0 (mod 6) ⇒ 阶 3；阶 2 需 4≡0 假；阶 1 仅单位元；6 是群阶不是元素阶。**选项排列已做判卷安全审计**（见 §4 测试 3） |
| 22 | dm_sa_koenigsberg（综合题，points 1.2） | 七桥问题/欧拉回路判据 | 不存在欧拉回路因存在**奇度**顶点（4 个顶点度数全为奇**度**） | 欧拉回路充要=连通+全偶度；七桥图四顶点度均为奇（3/3/3/5），与 A 项判据矛盾。NS-001 Day0 对话「分不清欧拉/哈密顿」的直接对标题 |

**判卷自检（程序化）**：22 题全部通过「正确答案（选项文本/1-based 序号/字母/SA 规范关键词）=1.0 分；每个错误选项文本=0 分；SA 错误作答 ≤0.4」三态断言（新增测试 2、3 固化为回归门）。

### 判卷器兼容性审计（本卡发现并修复的真问题）

`_score_choice_answer` 为 P1-E4 兼容接受「裸数字文本」作 0/1-based 索引提交。首版 `dm_algebra_element_order` 选项为 ("2","3","6","1")、正确位=1，此时错误选项文本 "2" 满足 `2-1==correct_index` 被**误判满分**。修复：选项重排为 ("2","6","1","3")（正确位=3）并对全部 49 题（cn/ds/dm 三科）程序化验证无任何错误文本命中索引启发式——该不变量已固化为跨科目回归测试。CN/DS 存量题包经审计天然满足（选项文本均为大数/复合文本），未触碰。

## 4. 新增测试

1. `test_exam_sprint_diagnostic_supports_discrete_mathematics_subject`（端到端，sqlite）：B4 同请求面 generate(15 题)→科目标题变体「离散数学期末」同包→图论链故意答错+其余正确→grade(update_galaxy=True)：分数<90、瓶颈含欧拉/哈密顿或图基础、掌握度全部落 `user_node_status`、节点为 `source_type="sprint_pack"` 的 canonical `dm.*` 且带 pack 中文标签。
2. `test_discrete_mathematics_pack_structure_and_grading_invariants`（内容门）：pack 经 `load_pack("离散数学")` 加载并过 `SprintPackV1` 校验；ch1..ch6 六章 layer 齐全；paths 只引用存在节点；模板 15-30 题、键唯一、≥5 领域、核心键≥5 领域；linked_slug 全解析到 `dm.*`；默认节点 slug 与 pack 后缀精确一致；逐题判卷三态断言。
3. `test_diagnose_choice_texts_do_not_alias_answer_indices_across_subjects`（跨科目回归门）：cn/ds/dm 全部单选题的错误选项文本判 0 分（裸数字索引别名 hazard 防回归）。

## 5. 回归统计

解释器：wt93 venv（pydantic 2.13.5/pytest）；基线对照 = `git clone wt98 /tmp/wt98-p01-baseline`（仅 HEAD@24c827fd + 生成的 `app/gen/`）。

| 套件 | 结果 | 与基线对照 |
|---|---|---|
| `tests/unit/test_exam_sprint_diagnostic_service.py` | **8/8 通过**（5 既有 + 3 新增） | 新增 |
| `tests/unit/test_exam_sprint_diagnose_api.py` | 通过（含于合并批 43 passed） | 无新失败 |
| `tests/unit/test_sprint_pack_loader.py` + `test_sprint_pack_registry.py` | 全过 | 无新失败 |
| `tests/unit/test_exam_sprint_review_service.py` + `test_aurora_runtime_planning.py` + `test_community_template_injection.py` | 37 passed | 无新失败 |
| `tests/unit/test_exam_sprint_intake_service.py` | 1 failed（mock `plan_id="plan_123"` 非 UUID，`_record_north_star_intake_metrics` 强转） | **基线同样失败**——存量债务（LOOP1 引入的度量埋点与旧 mock 不兼容），非本卡引入，红线未触碰 |
| `tests/orchestration/test_planning_workflow.py` | 4 failed / 29 passed | **失败清单与基线逐条一致**（diff 为空）——存量 |
| `tests/unit/test_error_replan_bridge.py` + `northstar_eval gate` + `integration/test_north_star_journey.py` | 8 failed / 22 passed / 2 errors | **失败清单与基线 diff 为空**——存量 |
| `tests/unit/test_signal_spine.py` 合并批 | 1011 passed, 1 failed | 失败为 `ModuleNotFoundError: langchain_core`（venv 缺依赖），基线同败——环境性 |
| `tests/northstar_eval/test_real_drive_unit.py` | 未运行 | venv 缺 `requests`，环境性（与代码无关） |

**结论：本卡零新增失败；全部差异测试与基线逐条一致。**

## 6. 收工核查声明

- [x] 全部修改仅落 wt98 worktree；主仓只读未动；未在仓库根/家目录建文件
- [x] 未 commit / 未 push；交付物 = `v3-output/P0-1-DIAG/changes.patch` + `REPORT.md`（patch 含新增 JSON pack，可 `git apply`）
- [x] `backend/app/gen/` 为本 worktree 本地生成产物（`make proto-gen`，proto 未改动）——不入库、不入 patch，主会话 worktree 回收时随之清理
- [x] 无独立端口进程/模拟器/浏览器实例；`/tmp/wt98-p01-baseline` 基线克隆与 `/tmp/*-failed.txt` 对照文件已删
- [x] 磁盘：本卡无构建产物（纯 Python/JSON/测试）；克隆临时盘占用收工即释
- [x] 借用 wt93 venv 仅进程级只读执行，未写入他 worktree 文件

## 7. 留卡（不在本卡范围）

1. **24 细粒度考纲节点**：journey spec 的 `dm.chX_*.01..04` 与章级 `dm.*` 节点的父子映射/逐节点掌握度下钻（本卡只补诊断触达必需的章级面 10 节点，其中 9 个被诊断题直接触达）。
2. `dm.trees` 节点暂无诊断题挂靠（章面保留，规划/后续题包卡可挂）。
3. intake `_record_north_star_intake_metrics` 与既有 mock 的 plan_id 兼容（存量失败，见 §5）。
4. `test_real_drive_unit.py` 需含 `requests` 的运行环境才能回归；NS-001 全链路复跑（B4 应由 422 转 200）待主会话排期。
