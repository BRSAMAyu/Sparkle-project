# AURORA-LABEL — `label` 坏引用 + planning-experiment 指标静默丢失（PROD-LOG2 top4 收尾件）

- 卡号：AURORA-LABEL（北极星全旅程战役 · C 纵队生产级线）
- worktree：wt215（基线 `5437c9c6`）；日期：2026-09-23
- 缺陷依据：主仓 `v3-output/PROD-LOG2/REPORT.md` ②-6 / ②-7（新问题 top4 第 4 项拆两件）
- 交付物：本报告 + `changes.patch`（同目录）；**零 commit / 零 push / 零凭据**

---

## ① 根因 + 修法（两处主缺陷）

### 1. Aurora `label` 坏引用（②-6，`context_builder.py:1161`）

**根因**：`_build_llm_profile_bundle` 内的 Aurora 集成块读了 `rel_state.label`，而 `SparkleRelationshipState`（`backend/app/aurora/schemas/primitives.py:286`）的真实字段是 `relationship_maturity / communication_style_emergent / interaction_count / last_interaction_at / shared_history_highlights / bound_policy_version`——**无 `label`（也无 `title`，`title` 属于 `DistilledStrategy`，报告原文稍有不确）**。每次调用必然抛 `AttributeError`，被外层 catch 吞成一行无栈 warning（PROD-LOG2 窗口 ×6）。

**实际爆炸半径（实测修正报告原文）**：赋值按行序执行，1161 行抛错时 `aurora_profile_summary` 与 `relationship_maturity` 已写入 bundle（下游 `prompts.py:1979/1983` 仍能消费）；真正静默丢失的只有 **`relationship_label` 键**（`prompts.py:1984` 取到 None，`- 协作者关系状态:` 提示行永远不渲染）+ 每轮一条假 warning。

**修法**（`backend/app/orchestration/context_builder.py`）：
1. 把 Aurora 集成块**提取为模块级纯函数** `_collect_aurora_relationship_profile_data(user_id, ledger=None)`——属性契约可单测（同病不再无声复发）；`ledger` 可注入，测试不碰磁盘路径。
2. label 改用 **aurora 域自己的公共派生**：`derive_state` → `derive_view`，取 `RelationshipDerivedView.maturity_label`（exploring/forming/stable/trusted，单一事实源在 `aurora/relationship_state.py:_maturity_label`），杜绝再次手猜字段。
3. catch 升级为**可观测三件套**：ERROR 级 + `logger.opt(exception=True)` 全栈 + 新计数器 `sparkle_aurora_profile_integration_failure_total`（对齐 17f4b5df EXC-TRACEBACK 手法；该站不在原 234 站之列，正是 PROD-LOG2 ① EXC-TRACEBACK 判定里建议纳入的那类）。

### 2. planning-experiment 指标静默全丢（②-7，`experiments.py:415/:458`）

**根因（为什么静默）**：Go 网关 `ab_test_middleware.go:getDefaultExperimentID` 把车道映射到 **slug** 实验 id（`/api/v1/plans` → `planning-experiment`，另有 `default-chat-experiment` / `recommendation-experiment` 同病）。Python 侧 `assign_variant` 见非 UUID → 直接回退 control（`variant_id="control"` 字符串）；网关随后把这对 slug+control 回传 `/metrics`，`record_metric` 的「非 UUID 即跳过」分支再次命中——**两站都是「WARN 一条 + 返回一个看似正常的 200」，无计数、无指标、无告警**，评估面拿到的是全部 control + 零指标的假阴性。不是异常被吞，是**上报面条件对 slug 永不满足**（接口只认 UUID，而网关只有 slug）。

**修法**（`backend/app/api/v1/experiments.py`，Python 侧桥接，网关不动——分层红线：网关不持业务）：
1. 新增 `_ensure_uuid_backed_experiment(db, redis, slug)` 解析桥：
   - 先按名字精确解析既有实验（操作者手工建的实验优先，不 Shadow）；
   - 白名单（三个网关车道 slug，封闭集）内缺失则**幂等补建** UUID 后端记录：control/treatment 50/50、`metrics=[success,latency]`、`created_by=None`、状态 `created`（诚实可见，实验 API 可 list/get/后续接管）；redis `SET NX EX 15` 锁防并发重复建行；
   - 白名单外 slug（如客户端乱发 `X-Experiment-ID`）**永不建行**，防表污染与基数爆炸。
2. `assign_variant`：非 UUID → 解析桥 → 拿真实验走原framework指派（真 variant UUID、确定性分桶）；解析失败才回退 control。
3. `record_metric`：variant 非 UUID → 跳过但**计 **`sparkle_ab_experiment_metric_skip_total{reason="non_uuid_assignment"}`**；experiment 是 slug → 解析桥转 UUID 后真落库（**指标真上报**）；解析失败 → 跳过 + `{reason="unresolved_experiment"}` 计数。**上报失败全量可观测**。
4. 新计数器 `sparkle_ab_experiment_slug_resolution_total{slug,outcome}`（resolved/provisioned/provision_failed/unknown_slug；slug 维度只在白名单内取值，其余记 `unknown`，防任意头值打爆基数）。

### 3. 同型扫描挖出的第三个生产 bug（同文件族，一并修）

**`ab_test_framework_enhanced.py:234`：`not ABExperimentAssignment.is_excluded`** —— 对 SQLAlchemy 列对象做 Python `not`：列恒真值 → `not` 得 Python `False` → `and_()` 把它编译成 **SQL `false` 字面量**，指派去重查询等价 `WHERE … AND false`，**永不命中**。后果：每次 `assign_variant` 都插入重复 assignment 行（表无限膨胀）且 `is_new_assignment` 恒 True——正是本卡「指标真上报」的语义地基（assignment 是变体归因键）。修法：`~is_excluded`（SQL NOT）。
同型扫描全库仅另一处：**`core/security_monitor.py:420` `not LoginAttempt.success`** —— `get_security_stats` 的失败登录计数恒 0（安全统计面板假阴性；PROD-LOG2 ③ 的「爆破零告警」分析部分源于此失真）。修法：`~LoginAttempt.success`。两处均已修，红证=新幂等测试修前 `is_new_assignment` 恒 True（见 tests）。

---

## ② 同型扫描结果（context_builder 幽灵属性面）

对 `context_builder.py` 全文件 + aurora 同族（`rel_state.` / `relationship_state.` 全仓 orchestration/services/api）扫描：

| 检查对象 | 结论 |
|---|---|
| `rel_state.*`（context_builder.py:1160-1161） | **`label` 是全文件唯一幽灵属性**（已修）；`relationship_maturity` 真实 |
| `llm_profile.*` ×7（:1104-1111） | 全部真实（`services/personalization/profiles.py:LLMProfile`） |
| `prefs.version`（:1103） | 真实（engine.py:375 同源） |
| `translation.summary` | 真实（`ProfileTranslationResult.summary`） |
| `plan.id/name/type/target_date/progress/plan_stage/subject/is_active` | 全部真实（`models/plan.py`） |
| `rel_state.` / `relationship_state.` 全仓引用 | 除 1161 外全部真实（`profile_translator.py` 4 处 + `relationship_state.py` 自身） |
| 登记不修 | `memory.summary`/`item.summary`（:177/:630）位于 stage33/34 运行时 envelope（`Any` 型、部分字段已防御式 `getattr`）——非 aurora 域，维持现状登记 |
| `not <column>` 同型（全库 grep） | 上述 2 处（framework + security_monitor），其余 0 |

---

## ③ 实现清单

| 文件 | 改动 |
|---|---|
| `backend/app/orchestration/context_builder.py` | 提取 `_collect_aurora_relationship_profile_data`（derive_view 驱动 + 真实 label）；catch 升级 ERROR+traceback+计数；metrics import 扩展 |
| `backend/app/api/v1/experiments.py` | slug→UUID 解析桥（白名单+幂等补建+redis 锁）；assign/record_metric 两站接入；跳过/解析结果全量计数 |
| `backend/app/core/metrics.py` | +3 计数器：`sparkle_aurora_profile_integration_failure_total`、`sparkle_ab_experiment_slug_resolution_total`、`sparkle_ab_experiment_metric_skip_total` |
| `backend/app/learning/ab_test_framework_enhanced.py` | `not col` → `~col`（指派去重复活，附注释） |
| `backend/app/core/security_monitor.py` | `not col` → `~col`（失败登录统计复活，附注释） |
| `backend/tests/unit/test_context_builder_aurora_relationship_label.py` | **新增** ×5：schema 无 label 回归守卫 / 空 ledger 全键 / 派生 label / 高成熟度爬梯 / 脏 payload 不投毒 |
| `backend/tests/api/test_experiments_slug_uuid_bridge.py` | **新增** ×5：slug 补建 UUID 实验 / 幂等+确定性 / **指标真落库** / 操作者实验优先不被 shadow / 未知 slug 回退+计数+零建行 |

## ④ 红证与回归（对比法零新增）

**红证（修前实测）**：
- label：venv 直跑 `derive_state(...).label` → `AttributeError: 'SparkleRelationshipState' object has no attribute 'label'`（与生产日志逐字一致）；
- 指标：`test_experiments_slug_uuid_bridge.py` 修前 **5/5 FAIL**，且 pytest 捕获日志逐字复现生产双 WARNING（`Experiment planning-experiment is not UUID-backed; falling back to control cohort` / `Skipping metric for non-UUID experiment assignment`）；
- 修后：**5/5 PASS**。

**绿证（修后定向回归，全串行）**：
| 套件 | 修后 |
|---|---|
| 新增两文件 | 10/10 pass |
| `tests/aurora`（349）+ `test_ab_test_framework` + `test_experiments_api_access` + security 三件套（18） | **374 pass = 基线 clone 同套件 374 pass，逐一对齐，零新增失败** |
| context 邻接（cache_versioning / source_contract / phase_b_prompt_sections / prodfix1） | 47 pass |
| 合计终轮 | **420 passed**（`--timeout` + sqlite in-memory env，一次一个套件串行） |

工具面：改动文件 `py_compile` 全过；`ruff check` 全绿；两个**新增**文件 black 120 干净（5 个既有文件 black 漂移系基线已有，与本次 hunk 无关，未做全文件重排以免污染 diff）。

## ⑤ 冲突面声明

- 本卡动：`context_builder.py`（:28 import / :69 helper / :1182 aurora 块）、`experiments.py`（assign/metrics 两端点+模块头 helper）、`metrics.py`（追加 3 计数器）、`ab_test_framework_enhanced.py`（:234 单行）、`security_monitor.py`（:420 单行）、tests 新增 ×2。
- **wt206 CHAT-VISIBLE 已合入 context_builder（`_persist_user_message` 挂 session 头）**：已核对，本卡三个 hunk（@@ -28 / @@ -65 / @@ -1113）与其分属不同区域，无重叠。
- wt207（onboarding/趋势/光子面）、wt214（concurrency/settings）：与本卡文件无交集；`security_monitor.py` 若他人同轮在动（未收到声明），改动仅 :420 一行一处。

## ⑥ 收工核查

- [x] 禁 commit/push：交付=本 REPORT.md + `changes.patch`（`git diff HEAD` + 两新增测试文件 --no-index 合成）
- [x] 零凭据（测试 SECRET_KEY 为临时哑值，不落任何配置文件；未创建/复制任何 `.env`）
- [x] pytest 带 `--timeout`，sqlite in-memory env，套件串行，无宽扫（全部定向文件/目录）
- [x] /tmp 清理：`/tmp/wt215-aurora-label-baseline`（对比法基线 clone）已删；无其他本卡 tmp 产物
- [x] worktree 内无构建产物残留（`app/gen` 为 `make proto-gen` 生成且 gitignore，不入 patch）
- [x] 未动 DB / 未重启任何共享进程；全程 LIGHT（无模拟器/Gradle/浏览器）
