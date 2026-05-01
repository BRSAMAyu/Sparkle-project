# Reviewer A — E09: Sprint Pack Schema验证——4个科目JSON完整性
Timestamp: 2026-04-26T12:10:00+08:00
Chain Index: 19

## Chain Flow Summary
4个Sprint Pack JSON文件（计算机网络/操作系统/数据结构与算法/高等数学）定义了考试冲刺知识包，由 `sprint_pack_loader.py` 加载、`task_card_generator.py` 生成任务卡、`planning_workflow.py` 编排计划。存在 Pydantic schema (`sprint_pack_schema.py`) 和离线验证脚本 (`validate_sprint_pack.py`)，但 `load_pack()` 加载时不执行 schema 验证。4个JSON结构大体一致，但 DSA 包的 task_card_templates 缺少关键字段且缺少 checkpoint_rules。

## Critical Issues 🔴
None found — 所有4个JSON文件都能正常加载和使用。

## Major Issues 🟡

**1. `load_pack()` 加载时不验证 schema — 坏数据静默通过**
- `backend/app/sprint_packs/sprint_pack_loader.py:96-102` — `_load_pack_file()` 只做 `json.loads()` + 返回 dict
- Pydantic schema 存在 (`sprint_pack_schema.py`)，离线验证脚本也存在 (`scripts/validate_sprint_pack.py`)，但加载路径完全不使用
- Expected: `load_pack()` 至少在 DEBUG 模式下调用 `SprintPackV1.model_validate(data)` 捕获缺失字段
- Actual: 任何格式错误的JSON只要语法合法就会被当作有效pack使用，运行时才在下游随机崩溃
- Evidence: `sprint_pack_loader.py` 全文无 `schema` / `validate` / `SprintPackV1` 引用

**2. DSA 包 `task_card_templates` 缺少 4 个关键字段**
- `data_structures_algorithms_v1.json` 的 4 个 template 只有 `template_id`, `label`, `instruction` — 缺少 `steps`, `done_criteria`, `duration_minutes`, `description`
- 其他3个包的 templates 都有完整的 6 个字段
- `task_card_generator.py:302` 在 `_select_template()` 中读取 `duration_minutes` 用于评分，缺失时 `_safe_int()` 返回 None，评分不受影响但降级到默认行为
- `task_card_generator.py:350` 在 `_select_step_names()` 中读取 `steps`，缺失时 `_split_lines()` 返回空列表，回退到 generic step names — 不致命但丢失了 DSA 特定的步骤指导

**3. DSA 包缺少 `checkpoint_rules`**
- `data_structures_algorithms_v1.json` 没有 `checkpoint_rules` 键（其他3个包都有）
- `checkpoint_rules` 在 schema 中定义为 `Field(default_factory=dict)` 所以 schema 验证不会报错
- 但 `planning_workflow.py` 中 checkpoint 逻辑依赖这些规则，缺失时使用空 dict 可能导致检查点不被触发

## Minor Issues 🟢

**4. DSA 包缺少 `priority_formula` 顶层字段**
- `computer_networks_v1.json` 和 `mathematics_v1.json` 有 `priority_formula` 字段，DSA 和 OS 没有
- `sprint_pack_loader.py:194-203` 的 `query_nodes_by_priority()` 不使用此字段（直接硬编码公式），所以无运行时影响
- 但文档/可审计性层面：4个包的优先级公式应该透明声明

**5. `mathematics_v1.json` 有额外的 `aliases` 字段**
- 其他3个包没有此字段，不影响运行（schema 设了 `extra="allow"`），但不一致

## Working Well ✅

1. **知识节点结构一致** — 4个包的 knowledge_nodes 都包含全部 12 个必需字段（node_id, label, layer, prerequisites, exam_weight, frequency, trainability, time_cost, difficulty, minimum_pass_required, score_max_required, common_mistakes, recommended_action）
2. **路径覆盖完整** — 4个包都有 `minimum_pass` 和 `score_max` 两条路线
3. **策略预设齐全** — 4个包都有 `7d` 和 `14d` 策略预设
4. **科目别名丰富** — `sprint_pack_loader.py` 的 `_SUBJECT_ALIASES` 覆盖了中英文各种缩写和全称
5. **`TaskCardGenerator` 降级健壮** — 所有字段读取都有 helper 函数（`_strip`, `_safe_int`, `_safe_float`）兜底，缺失字段不会崩溃
6. **计算机网络包质量极高** — 45节点、18题型、48错误类型、5模板、完整 last_24h_strategy 和 aurora_rules，可作为标准参考
7. **节点量级合理** — OS(46) > Math(57) > CN(45) > DSA(45)，覆盖本科核心考点
8. **Pydantic schema + 离线验证脚本** 存在且可用：`python scripts/validate_sprint_pack.py backend/app/sprint_packs/computer_networks_v1.json`

## Files Examined
- `backend/app/sprint_packs/computer_networks_v1.json` (2243 lines)
- `backend/app/sprint_packs/operating_systems_v1.json` (structure analyzed)
- `backend/app/sprint_packs/data_structures_algorithms_v1.json` (structure analyzed)
- `backend/app/sprint_packs/mathematics_v1.json` (structure analyzed)
- `backend/app/sprint_packs/sprint_pack_loader.py` (240 lines)
- `backend/app/sprint_packs/sprint_pack_schema.py` (45 lines)
- `backend/app/orchestration/task_card_generator.py` (796 lines)
- `backend/app/orchestration/planning_workflow.py` (lines 27-38, 216-234, 322-334)
- `backend/scripts/validate_sprint_pack.py` (132 lines)

## Confidence: High — 用脚本验证了4个JSON的结构完整性，追踪了加载/生成/编排的完整链路。
