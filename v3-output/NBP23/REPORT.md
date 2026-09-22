# NBP-2+3：goal-detail 运行时 500 + goal→intake 双计划残余（LOOP2 两断点同域打包修复）

> worktree wt116（基于 main@d5cce684），交付 `changes.patch`（4 文件，451 行）+ 本报告。禁止 commit/push。

## ① 两问题根因（各一句）

- **NBP-2（P0）**：`GET /experience/goal-detail/{goal_id}` 稳定 500 的根因**不在 goal_router.py 的模型定义顺序**（该文件内 `CriteriaThresholdPayload` 先于 `MinimumAcceptanceCriteriaPayload` 定义，包内正常导入时 `__pydantic_complete__=True`），而在 `app/api/v1/router.py` 的 `_include_experience_routers()`：closeout 动态加载用 `spec_from_file_location`+`module_from_spec`+`exec_module` **但 exec 前未注册 `sys.modules[module_name]`**，违反 importlib 契约；pydantic v2 解析 `from __future__ import annotations` 产生的字符串前向引用时按 `cls.__module__` 查 `sys.modules`，查不到 → 运行时真正生效的 `GoalDetailPayload` 副本（模块名 `app.api.v1.experience_closeout_goal_router`）`__pydantic_complete__=False` → 首次响应校验触发 `model_rebuild()` 失败抛 `PydanticUserError` → 500。
- **NBP-3（P1）**：`goals.py create_goal` 自建 plan 时**从不写 `subject`**（`PlanModel(...)` 无该字段，`subject=None`），而 INTAKE 幂等复用 `_find_reusable_sprint_plan` 的唯一匹配键是 `(user, SPRINT, active, subject==, target_date==)` → goal 建的 plan 永不命中 → intake 另建第二份 active sprint 计划；且 `subject` 为 NULL 的行不在 `uq_plans_user_sprint_goal_active` 部分唯一索引谓词内（NULL 互异），不撞索引、**静默双计划**（账本 `069bc4f9`+`ad361a54` 并存即此机制）。

### NBP-2 证据链（活栈实测，非推测）

1. 纯包内导入 `app.api.v1.experience.goal_router`：`MinimumAcceptanceCriteriaPayload.__pydantic_complete__ == True`（单测直调 handler 全绿的世界）。
2. 真实 `app.main.app` 装配后取该路径 GET 路由：`response_model` 来自 `app.api.v1.experience_closeout_goal_router`（exec 副本），`complete=False`；对该副本 `model_validate(合法载荷)` 复现 `PydanticUserError: GoalDetailPayload is not fully defined; you should define GoalSummaryPayload...`（LOOP2 eval 栈报的 `MinimumAcceptanceCriteriaPayload` 是同一 rebuild 遍历的另一症状名，同根因）。
3. `sys.modules['app.api.v1.experience_closeout_goal_router']` 在修复前**不存在**（loader 未注册）——直接证明加载方式违反 importlib「exec 前注册 sys.modules」契约。
4. 守卫测试 `test_goal_detail_route_shadowing.py` 全部直调 handler/断言注册面，**不经过 FastAPI response_model 校验路径**，且其 `test_goal_detail_get_is_served_by_goal_router` 断言 `"goal_router" in endpoint.__module__`——`app.api.v1.experience_closeout_goal_router` 恰好包含该子串，断言恒真。**「单测绿/运行红」的方法论缺口由此坐实。**

### NBP-3 证据链

- `app/api/v1/goals.py` `create_goal`（:191-206）：`PlanModel(user_id, goal_id=goal.id, name=标题, type=SPRINT, target_date=payload.target_date, ...)`，无 `subject`；`goal.plan_id = plan.id` 双向关联成立。
- `app/services/exam_sprint_intake_service.py` `_find_reusable_sprint_plan`：`Plan.subject == subject` 等值匹配，`subject` 空则直接返回 None。
- `app/models/plan.py` `uq_plans_user_sprint_goal_active`（=迁移 `intakeidx_20260922`）：键 `(user_id, subject, target_date)`、谓词 `type='SPRINT' AND is_active AND deleted_at IS NULL`——NULL subject 行被排除在约束外，双计划不报错。

## ② 修复方案与论证

### NBP-2：loader 注册 sys.modules（根因最小修复）

`router.py::_include_experience_routers()` 在 `exec_module` 前补 `sys.modules[module_name] = module`，失败时 pop 清理后原样上抛（不留半执行模块）。**选型论证**：

- 这是 importlib 官方文档明载的动态加载契约，修的是装载机制而非某个模型——一次性根治全部 closeout router 的同类隐患（`understanding_router` 的请求体模型引用枚举、同样是字符串注解，同病；`community_router` 因无 `from __future__ import annotations` 幸免）。
- **否决方案 a**：goal_router 模块尾补 `model_rebuild()`——在未修复的 loader 下它同样解析失败且会把 ImportError 提前到应用启动（路由整体不注册、端点 404 化，比 500 更糟）；在修复后的 loader 下它是冗余代码。
- **否决方案 b**：loader 改走 `importlib.import_module("app.api.v1.experience.<stem>")` 包内导入——更"正统"但改变了 closeout 挂载的模块命名与既有守卫的观测面（`experience/__init__.py` 目前只导出 readouts，closeout glob 装载是独立生效路径），侵入大于收益；sys.modules 注册 3 行封顶，行为面其余不变。
- 副作用披露：同一文件现以两个模块名各加载一份（closeout 副本继续是路由 owner；包内副本仅供测试直调与守卫 introspection），无跨副本 isinstance 依赖，风险可控。

### NBP-3：复用匹配键二级扩展 + subject 自愈回填（侵入最小）

`_find_reusable_sprint_plan` 主键**原样保留**；主键未命中时新增兜底 `_find_goal_linked_sprint_plan`：

```
identity = (user, SPRINT, is_active, 未软删, target_date == exam_date,
            goal_id 非空 且 join 的 Goal 为同 user、goal_type=='exam'、未软删)
同日多目标取最新创建（与迁移 intakeidx_20260922 存量收敛口径「保留最新」一致）
```

**选型论证**：

- **否决「goal 建计划时回填 subject」单方案**：回填值只能取 goal 标题或启发式抽取（如「离散数学期末 7 天冲刺：及格冲 70+」vs 表单「离散数学」），与 intake 表单自由文本 subject 的等值匹配天然脆弱，修不干净；且对账本中已存在的 NULL subject 存量行无能为力。它作为主方案的**伴生自愈**被吸收：intake 兜底命中后把表单 subject 回填到 plan（`get_db` 成功路径自动提交），此后同表单复跑走 BP-7 主键，该计划也被纳入 INTAKE-IDX 唯一索引的 DB 级并发保护——幂等语义自愈收敛。
- **边界严格性**（两个负例测试锁死）：不同 `exam_date` 不复用（不同考试=不同目标）；非 exam 型 goal（`goal_type != 'exam'`）的同日计划不复用。兜底分支要求 `goal_id` 非空 + join Goal，而 intake 自建计划 `goal_id=NULL`，两分支零交集——**BP-7 intake-vs-intake 幂等与 INTAKE-IDX 竞态语义完全未被触碰**。
- 文档一致性：函数 docstring 已同步更新两级同一性语义；`_find_reusable_sprint_plan` 签名未变，INTAKE-IDX 并发测试对它的类级 monkeypatch 继续成立。

## ③ 红→绿统计

| 卡 | 新测试（先红后绿） | 红 | 绿 |
|---|---|---|---|
| NBP-2 | `test_goal_detail_route_shadowing.py::TestResponseModelRuntime` | `test_every_closeout_experience_model_is_fully_defined`（complete=False 断言炸红）；`test_goal_detail_get_via_testclient_returns_superset`（**TestClient 全栈 500 复现生产故障**） | 修复后 2/2 绿 |
| NBP-3 | `test_exam_sprint_intake_service.py` 新增 3 例 | `test_intake_reuses_goal_created_plan_when_subject_is_null`（以 QuotaExceededError 探针炸红：兜底缺失即走创建路径）；2 负例（不同 exam_date / 非 exam goal 不复用）红态即通过（锁现状语义），修复后须与主红同绿 | 3/3 绿 |

- NBP-2 守卫族：修复前 **2 failed / 9 passed**（9 个既有守卫全绿证明无遮蔽回归）→ 修复后 **11 passed**。
- NBP-3 intake 族：修复前 **1 failed / 5 passed** → 修复后 **6 passed**。
- 真实 app 终验：修复后 `app.main.app` 装配面 `response_model.__pydantic_complete__ == True`（修复前 False）。

## ④ 守卫与幂等族结果（全绿）

- **GOAL-ROUTER 9 用例守卫 + 2 新运行面用例**：11/11 绿（注册面/形状面/功能面无回归；运行面从缺位到 2 例）。
- **INTAKE 幂等测试族**：6/6 绿（含 BP-7 同表单复跑复用既有 plan 主案例 + NBP-3 三例）。
- **INTAKE-IDX 6 路并发测试族**：`test_exam_sprint_intake_concurrency.py` + `test_intakeidx_..._migration_sqlite.py` **5/5 绿**（索引语义边界、竞态败者回退、6 路真并发恰好 1 plan 全员同 id）。
- **回归面**：goal/experience/exam_sprint 家族 11 文件 **77 passed**；closeout 机制另一消费方 community 守卫 `test_community_accountability_route_shadowing.py`+`new_guest_500.py` **4/4 绿**（loader 修复对其无副作用）。
- **基线既有红（非本卡引入，已用 `git clone` 克隆基线单独复跑证实）**：`test_experience_actuator.py::test_experience_actuator_auto_retrieves_user_material_grounding`——测试与 `_ground_with_user_materials` 签名漂移（`include_group_documents` kwarg），orchestration 域，与本卡改动零交集，留给主会话派单。

## ⑤ 收工核查

- [x] 全部修改仅在 wt116 内：`backend/app/api/v1/router.py`、`backend/app/services/exam_sprint_intake_service.py`、两个测试文件（`git status` 仅此 4 项 modified + 本目录 2 项 untracked 交付物）。
- [x] 主仓零写入：`backend/app/gen`（gitignored 生成物，wt116 缺失导致无法装配）**只读拷贝自主仓**，已核对主仓 proto 与 wt116 proto 逐字节一致（仅 .DS_Store 差异）。
- [x] /tmp 已清：基线克隆 `/tmp/wt116-baseline` 已删；无其他临时产物。
- [x] 无残留进程/构建产物：未起 Docker/模拟器/长驻进程；pytest 全串行（LIGHT 负载，未触发 HEAVY 门）。
- [x] 无 commit/push；`changes.patch`（4 文件 451 行）+ 本报告落于 `v3-output/NBP23/`。
- [x] lint：两个测试文件与 intake 服务 ruff 全绿；router.py 仅剩**基线既有** I001（超大 import 块历史问题，修它会造成与本卡无关的 400 行 churn，不越界）。新增行超 120 者仅 3 处尾部 `# type: ignore` 注释行（black 不可拆分、与既有同款）。

## 冲突面 / 待主会话事项

- 本卡未触碰 wt115（WS 记忆，memory/orchestration 域）、wt117（gateway SSE 超时）的文件；`router.py` 与 `goals.py` 均无交叉。
- 移动端无需改动：`GoalDetailPayload` 形状未变，只是端点从 500 变 200；建议下一轮 LOOP 驱动器对 goal-detail 直测 200（本卡已给 TestClient 全栈用例，真机验收留给实机轮）。
- `test_experience_actuator` 既有红需要独立小卡（orchestration 域签名漂移）。
