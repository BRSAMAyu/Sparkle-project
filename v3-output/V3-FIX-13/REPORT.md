# V3-FIX-13 REPORT — fresh 库可用性包（组员验证成果收编）

> 执行：V3 Fleet Worker（wt6，base 43942d23）｜日期：2026-09-19｜依据：成员三在旧基线 387993f 的 fresh-DB 验收发现（主会话逐项对照 main 后下发 4 项）

## 0. 结论

**READY_FOR_REVIEW（4 项中 2 项"已在 HEAD 存在"、2 项本次红绿补上）**。按红绿纪律在我方链上独立复现的结果与任务预设不同：D-14 与 D-11 在当前 HEAD **无法复现**（前置轮次已收敛，证据见 §3/§4，故**不加**重复迁移、**不改**无红可依的种子代码）；D-12 与 D-15⑦ 真实存在，已红→修→绿，并通过 docker 内 scratch PG 从零 `alembic upgrade head` + guest 种子 dry-run 全链验证。

## 1. 与组员报告对照表（核心交付）

| 项 | 组员在 387993f 的发现 | 我方 HEAD（43942d23）实况 | 本次动作 |
|---|---|---|---|
| **D-14（P1）t34 迁移缺失** | `SharedResource` 声明 adoption_count/negative_feedback_count/quality_score/quality_hidden 4 列但迁移从未创建，fresh 库 guest 种子必挂（UndefinedColumn→毒化→登录 500） | **已存在**：`gfix01_shared_resources_fv22_20260918.py`（mergepoint，down=r20807+sr8r2g2）恰好补齐这 4 列（注释自述同一症状）；`alembic heads` 单头 `x01_20260919`，gfix01 在其祖先链上。scratch 从零迁移后 `information_schema` 实证 4 列齐全（integer/0、integer/0、double precision/0、boolean/false，均 NOT NULL） | **不加 t34v3**。fresh 库上再 add_column 会 duplicate_column，反而炸纯迁移链。以"已在 HEAD 存在"归档（§4 表 A） |
| **D-11（P1）成就枚举大小写错位** | type/rarity 需按 Python enum member name（大写）持久化；populate 需显式枚举转换+commit=False；achievementtype 枚举缺大写 PLANNING | **主项不复现**：① `achievementtype` 已被 `r20807_achievementtype_lowercase_20260918`（R2-08-07）**特意收敛为 11 值小写契约（含 planning）**——组员"补大写 PLANNING"方向与我方设计相反，任务已预置"若已含则跳过"条款，我方枚举含小写 `planning`，**跳过并说明**；② `achievementrarity` 走 SQLAlchemy member-NAME 契约（DB 端 COMMON/RARE/EPIC/LEGENDARY），种子裸字符串经 SQLAlchemy **按值 coercion**（"common"→`AchievementRarity.COMMON`→落盘 `COMMON`），fresh PG 实测 39 成就+6 皮肤+37 装扮全部按各表契约正确落盘（achievements.type 小写 / rarity 大写 / visual_elements 三列小写） | **不改 populate 枚举转换**（红测做不出失败=无红不修；钉装 SQLAlchemy 2.0.48 下 coercion 正确）。**commit=False 部分属实**，随 D-12 落地（§2/§3） |
| **D-12（P2）guest 种子事务毒化** | 登录事务内同步种子，任一失败毒化整个登录 | **存在（结构性）**：`sync_achievement_definitions` 在登录事务中途擅自 `commit()`（部分种子无法被调用方回滚）；`seed_guest_user_data` 无 SAVEPOINT 隔离，异常直接上抛（auth.py 兜底需整体回滚+重试）。auth.py 的"登录不 500"兜底本次核实**已存在**，毒化面=部分提交的脏种子+重试churn | **已修**：种子整段包 `begin_nested()`（SAVEPOINT），失败回滚到 SAVEPOINT 并降级告警（种子是 best-effort 演示数据，不阻断登录）；`sync_achievement_definitions(db, *, commit=True)` 新增 commit 形参，guest 路径传 `commit=False` 保留调用者事务。红 2 → 绿 3 + PG 探针（§3/§4） |
| **D-15⑦（P2）executor locale** | executor ~347-359 无条件向工具 `execute()` 传 locale，无签名探测 | **存在且影响面大于预期**：25 个注册工具中 **23 个** `execute` 无 `locale` 形参（create_task / query_all_tasks / web_search_pro / get_persona_snapshot / translate / batch_create_tasks 等，盘点清单见 §3.3）；每次经 executor 调用即 `TypeError: unexpected keyword argument 'locale'`，被兜底 except 吞成"工具执行失败"。`PersonaTool` 是现成实例（定义于 `app/tools/persona_tools.py`，未挂注册表） | **已修**：`ToolExecutor._accepts_kwarg()`（inspect 签名探测，含 `**kwargs` 通配与 KEYWORD_ONLY）→ `locale` 与 long-running 分支的 `progress_callback` 均探测后再传。红 2 → 绿 3（§3/§4） |

## 2. 改动文件

| 文件 | 改动 |
|---|---|
| `backend/app/data/populate_achievements.py` | `sync_achievement_definitions(db, *, commit=True)`：新增 commit 形参（默认 True 保留 CLI populate 与 achievement_engine 自愈路径原行为；False 时不提交、数据留在调用者事务）+ docstring 说明 |
| `backend/app/services/guest_seed_service.py` | ① `seed_guest_user_data` 改为公开包装：进入前先取 `user.id/username` 纯值（SAVEPOINT 回滚会把实例置过期，避免回滚后同步上下文懒加载炸 MissingGreenlet），整段 `async with session.begin_nested()` 包裹原实现（重命名 `_seed_guest_user_data`），失败 `logger.warning` 降级、不再上抛；② `_ensure_achievements` 改调 `sync_achievement_definitions(session, commit=False)` |
| `backend/app/orchestration/executor.py` | 新增 `ToolExecutor._accepts_kwarg(func, name)`（`inspect.signature`，POSITIONAL_OR_KEYWORD/KEYWORD_ONLY 命中或 VAR_KEYWORD 通配视为接受；签名不可读则保守不传）；`_execute_tool_call_with_session` 装配 `execute_kwargs`：`locale`、long-running 分支 `progress_callback` 均探测后再传，`tool_call_id` 恒传（BaseTool 契约） |
| `backend/tests/services/test_guest_seed_savepoint.py` | 新增 3 测：种子中途失败不毒化登录事务（不抛出+用户存活+零部分残留）；`commit=False` 不 commit 且随调用者回滚消失；默认 `commit=True` 行为不变 |
| `backend/tests/unit/test_executor_tool_locale_signature.py` | 新增 3 测：无 locale 形参工具不再被硬传打挂（忠实复刻生产签名，无 `**kwargs`）；带 locale 工具照常收到 runtime_context.locale（防回退守卫）；long-running 分支 progress_callback 探测 |

**迁移链：零改动**（不加新迁移，head 仍为 `x01_20260919`，理由见 §1 D-14 行）。改动统计：3 个 app 文件 +61/-8，2 个新测试文件。

## 3. 红绿证据

### 3.1 RED（实现前，`tests/services/test_guest_seed_savepoint.py` + `tests/unit/test_executor_tool_locale_signature.py`）

```
FAILED test_executor_tolerates_tool_without_locale_kwarg        # TypeError: unexpected keyword 'locale' → 兜底吞成 success=False
FAILED test_executor_long_running_branch_signature_probe       # 同上（progress_callback+locale 双硬传）
FAILED test_guest_seed_failure_does_not_poison_login_transaction # RuntimeError 逃逸出 seed_guest_user_data
FAILED test_sync_achievement_definitions_commit_flag_preserves_caller_transaction  # TypeError: unexpected keyword 'commit'
4 failed, 2 passed  （2 passed = 带 locale 工具守卫 + 默认 commit 行为守卫，防修坏既有能力）
```

### 3.2 GREEN（实现后）

同套件 **6/6 passed**；修复过程中发现并修掉一个次生坑：SAVEPOINT 回滚使 `user` 过期，异常日志里 `user.id` 触发同步上下文懒加载 → MissingGreenlet（改为进入前取纯值）。

### 3.3 D-15⑦ 影响面盘点（修复前实测）

`tool_registry.get_all_tools()` 共 25 个，其中 23 个 `execute` 签名为 `(params, user_id, db_session, tool_call_id)` 无 locale 无 `**kwargs`：query_error_history, record_error, get_intervention_track_record, record_intervention_feedback, get_persona_snapshot, get_plan_state, get_task_detail, get_task_summary, get_user_behavior_patterns, generate_learning_report, run_quick_simulation, get_task_details, modify_plan_task, query_all_tasks, query_plan_tasks, batch_create_tasks, breakdown_task, create_task, suggest_quick_task, update_task_status, launch_prediction, translate, web_search_pro。

## 4. scratch 库验证（docker 内 sparkle_db，库用完即删）

`sparkle_fix13_scratch`：drop→create→`alembic upgrade head` 从零 145 个迁移全链成功（~5.6s，末段 m01a→x01）：

| # | 探针 | 版本 | 结果 |
|---|---|---|---|
| A | D-14：`information_schema` 查 shared_resources 4 列 + `enum_range(achievementtype)` 11 小写值（含 planning）+ `enum_range(achievementrarity)` 4 大写值 + alembic_version=x01_20260919 | 修复前 HEAD | **已在 HEAD 存在**（4 列齐全；契约见 §1） |
| B | D-11/D-14：`sync_achievement_definitions` 全量种子直跑 fresh PG | 修复前 HEAD | **NO-ERROR**：39 成就+6 皮肤+37 装扮落盘，抽样行 type=小写、rarity=成员（DB 端大写）→ D-11 不复现的实证 |
| C | 全链 guest 种子 dry-run（`seed_guest_user_data`，含 accountability 成就/共享资源/群组/星图/聊天种子） | 修复前 HEAD | **GREEN**：achievements=47, user_achievements=6, shared_resources=4, groups=6, nodes=54, flame=15, photon=1000 |
| D | 重建 scratch 后 D-12 失败注入（`_ensure_galaxy_skins` 注入 RuntimeError） | 修复后 | **GREEN-CONTAINED**：seed 不上抛、commit 后用户存活、partial_achievements=0、partial_user_achievements=0（首次同库连跑时全局成就行被探针 B 预提交污染出假红，重建后单跑定案——过程教训记录在案） |

日常库 `sparkle` 全程只读（仅 `docker inspect` 取连接串与 `docker port`）；迁移未对 sparkle 执行，留待 Leader 合入窗口统一 apply（本次无新迁移，sparkle 侧无需动作）。

## 5. 回归

定向串行 pytest（sqlite 内存库，`SECRET_KEY` 注入）共 **75 passed, 0 failed**：既有 guest_seed_service 3、achievement 系统对齐 3、achievement_engine 别名 4/可观测 1/回归 5/契约周末 23/问责时区 1、achievement_api 7、executor 执行观察 2/可观测 3、guest_500 回归 2、auth 登录 7，+ 本次新增 6。风格：新文件 black(120)+ruff 全绿；3 个存量 app 文件 HEAD 即非 black-clean、ruff B023（executor:790）为 HEAD 既有债务，未越权代改。

## 6. 备注 / 建议（不阻塞）

1. **裸字符串落库依赖 SQLAlchemy 按值 coercion**：D-11 虽不复现，但 `populate_achievements` 直赋种子字符串的正确性由 `enum(value)` coercion 兜着（SQLAlchemy 2.0.48 实测正确）。若未来升级 SQLAlchemy 或引入校验更严的方言，可加显式枚举转换作为加固——需先造出红再动，本次不做。
2. **achievement_engine.py:320** 以默认 `commit=True` 调 `sync_achievement_definitions(self.db)`，在请求态会话上存在与 D-12 同类的中途提交面；不在本任务四项内未动，建议后续轮次评估改 `commit=False`。
3. auth.py 既有"rollback→重试→放弃"兜底保留原样，作为 SAVEPOINT 之外的第二道防御（若 seed 内部已吸收失败，该路径成为死代码但无害）。
4. 组员 t33/t34 编号未占用、未使用；其 fork 若后续合入需重新对链。

## 7. 清理记录

`sparkle_fix13_scratch` 已 drop；`/tmp/fix13*`（探针脚本/导出 reqs）已删；worktree 内 `backend/.venv` 已删（uv 全量装回约 1 分钟，见 §4 环境注：pyproject `[tool.uv]` 阿里云镜像对部分 wheel 403，需 `uv export` + 官方/清华索引旁路安装）；无驻留进程。未 commit/push，改动以 `changes.patch` 交付。

STATUS: READY_FOR_REVIEW
4 项红绿结论：D-14 在 HEAD 已存在（gfix01_20260918 在链上，fresh 迁移 4 列实证，故不加 t34v3 以免 fresh 库 duplicate_column）；D-11 不复现（r20807 已收敛小写契约含 planning、rarity 大写契约下 SQLAlchemy 按值 coercion 正确，fresh PG 种子全绿，故不改无红可依的代码）；D-12 已红（异常逃逸+中途 commit）转绿（整段 begin_nested SAVEPOINT + commit=False，sqlite 6/6 + PG 失败注入 GREEN-CONTAINED）；D-15⑦ 已红（23/25 注册工具 TypeError）转绿（_accepts_kwarg 签名探测，locale 与 progress_callback 双分支，带 locale 工具守卫不回退）。迁移挂链：零新增迁移，单头 x01_20260919 不变，gfix01 为既有祖先。scratch 验证：sparkle_fix13_scratch 从零 upgrade head 全链通过 + 种子 dry-run 47 成就/4 共享资源/54 节点，定向回归 75 passed，日常库 sparkle 只读未动，scratch 与 /tmp 已清理。
