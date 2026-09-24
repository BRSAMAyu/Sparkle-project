# WT330 · F-2 内部命名泄漏到用户界面（backend seed 清洗）— REPORT

日期：2026-09-25 ｜ 卡源：wt324 实测问题清单 F-2（major），证据 G03_sheet_loaded.png
分支：`wt330-backend-seedclean`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt330-backend-seedclean`）

## 一、溯源（任务 → 知识节点命名链路）

1. **内部 token 生成语义**：`backend/tests/northstar_eval/feature_tour.py` S7 攒光子阶段
   （:802-803）以 `run = f"{run_id}-{i}-{uuid4().hex[:6]}"`（`run_id`=`uuid4().hex[:8]`，
   注释「subject 全局唯一（重跑安全）」）构造任务标题
   `TOUR 专题{d}-{run}: 真题演练与错因回看`。
   实测样本 `TOUR 专题7-d91d5df0-10-5dc70d: 真题演练与错因回看` =
   TOUR tag + 专题日 7 + run_id `d91d5df0` + 冲刺序 10 + uuid6 `5dc70d`。
   token 本身是评测 harness 的合法去重手段，问题在下游把它拷进用户可见字段。
2. **泄漏链**：POST /api/v1/tasks 原样落任务标题 → 完成时无 `knowledge_node_id` 的任务走
   daily-flow DF-5（`backend/app/services/task_service.py:800`）→
   `GalaxyService.ensure_task_node(raw_title)`（`backend/app/services/galaxy_service.py:2688`）
   把 raw title 逐字写进 `KnowledgeNode.name/description/keywords` →
   REST `/galaxy/graph`、`/galaxy/nodes/{id}` 详情（`backend/app/api/v1/galaxy.py:579` 区域）
   与 gRPC SearchNodes 原样投影 → 星图详情页大标题/描述/关键词三处泄漏（wt324 截图）。

## 二、修复

**新增 `backend/app/services/galaxy/title_sanitizer.py`**（纯函数、无 IO）：
- `strip_internal_tokens(text)`：剥离「(TAG)? 专题/Topic N-token 段: 」块、保留语义尾；
  不匹配该形态的输入 byte 级零改写（「数据结构复习 — 二叉树专题」「导数应用专题练习」
  「Topic modeling: an introduction」均不受影响）。
- `clean_display_title(title)`：有尾取尾；全内部 token（无尾）fallback「专题 N」；
  空串透传。

**生成侧**（`galaxy_service.py`）：
- `task_node_uuid` 键改在清洗后语义名上：干净标题映射与旧口径完全一致（有测试固化）；
  语义相同只剩 token 不同的任务收敛到同一颗星（恢复 docstring「same topic one star」本意）。
- `ensure_task_node` 的 name/description/keywords 只落干净名；内部标识留在
  `id`/`source_task_id` 非展示字段。

**读取侧存量防御**（不改库、只清展示面）：
- `backend/app/schemas/galaxy.py`：`NodeBase.from_model`、`NodeWithStatus.from_models`、
  `_build_auto_tags` 的 name/description/keywords/tags 全部过清洗（gRPC SearchNodes 走
  NodeBase 投影自动覆盖；contribution stats 节点名同步清洗）。
- `backend/app/api/v1/galaxy.py`：节点详情 dict（大标题/描述/关键词）与关系两端名。
- `backend/app/services/galaxy_grpc_service.py`：GetNodeDetail 直读 ORM 分支的
  label/description/tags。

Mobile 兜底未改（后端读取侧已兜住全部投影面，卡面允许省略）。

## 三、测试（红测先行）

- 新增 `tests/services/galaxy/test_title_sanitizer.py`（19 例）：证据串/嵌入描述/全宽冒号/
  英文变体/全 token/零改写/空/keywords 去重；NodeBase 投影脏行清洗 + 干净行零改写。
  先红后绿（初版正则两处缺陷被红测钉出：单字符冲刺序号段、裸 token fallback 顺序）。
- `tests/unit/test_task_galaxy_coupling.py` 追加 5 例（先红后绿）：tokened 任务种出干净
  命名节点；同语义尾不同 token 收敛一颗星；与既有同名种子星点亮不复制；
  `task_node_uuid` 语义键收敛 + 干净标题旧口径不变。
- 定向回归：galaxy services 全目录 + task_service + gRPC 三面 + contribution stats +
  node history/document/contribution API + sprint galaxy mastery =
  **148 + 41 + 24 passed, 0 failed**。

## 四、验收门

| 门 | 结果 |
|---|---|
| ruff check 被碰 7 文件 | 0 问题 |
| 冷缓存 mypy（rm -rf .mypy_cache） | **1615 = 基线**（与 main 逐行 diff 仅行号位移） |
| run_all_rule_guards.sh | **exit 0（83 rules）**（拷齐 gen 三件套后过） |

## 五、记录与移交

- `test_galaxy_concurrency.py` 3 failed/3 error：该文件用真实 `AsyncSessionLocal/engine`
  （需 live Postgres），worktree+sqlite 下 `no such table: user_node_status`——环境限制，
  非本卡回归（与 wt330 改动无交集，未改其表/引擎路径）。
- 仓库 5 个被碰文件在 main 上即不满足 black（格式漂移为存量），按最小 diff 纪律未跑
  black 全格式化；ruff 是门，已过。
- 一次自伤并即时修复：mypy 基线对照时 /tmp 备份两份同名 `galaxy.py` 相互覆盖，恢复时把
  schemas 内容错拷进 api/v1/galaxy.py——已 `git checkout --` 复原并重放三处编辑，
  终态以 git diff 为准（现已核验无误）。
- 遗留观察（不在本卡范围，供后续卡池）：计划 `subject` 字段会被 harness 填
  `TOUR科目-{run}`，详情接口 `subject_name` 原样透出，属 plan 命名链路而非节点 seed 链路；
  修复前创建的存量脏星（uuid5(raw) 键）在读取侧展示已干净，但新完成事件不会再命中旧
  uuid 键（会按语义名新建干净星），如需彻底归并可考虑一次性 devtools 迁移脚本（改数据行，
  需单独授权）。
- Forbidden 区核查：未触碰 growth dashboard/chat_mode/goal current_goal_id；无 migration；
  未改 seed 之外 galaxy 业务逻辑；未碰 sparkle-cosmos；主仓只读（仅执行其 venv 与读 gen）。
