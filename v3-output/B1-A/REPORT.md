# 批1-A · 信任地基 · 施工报告（wt90）

> 交付物：`v3-output/B1-A/changes.patch`（17 文件，+828/−130）+ 本报告。
> 基线：wt90-v3，基于 main@905e99f2。零 commit / 零 push / 零模拟器 / 零构建。
> 红证存档：`v3-output/B1-A/s7_red_proof.txt`（实现落地前 14 failed）。

---

## 1. S7 「今日任务」单一事实源（severity 5）

### 根因（含施工期新发现）

TRIAGE §1.2 已证：arb 双 key 的两消费者同源，纯 i18n 重复债；真矛盾是三源口径互不相认。施工期进一步定位到三源各自的判定代码：

| 消费面 | 位置 | 修复前口径 |
|---|---|---|
| home 快照/指挥台（`next_task` pill） | `backend/app/api/v1/experience_readouts.py` `_next_task` | **无 today 过滤**，状态集含 PAUSED，排序 priority 优先 |
| goal 详情「今日最小下一步」 | `backend/app/api/v1/experience/goal_router.py` `_todays_next_task` | **无 today 过滤**，状态集排除 PAUSED，排序 in_progress 优先 |
| 客户端任务看板 | `task_board_provider.dart` | 头部汇总 `isSameDay(dueDate) \|\| isSameDay(completedAt)`，与正文今日分组（仅 dueDate==today 且未完成）口径不一致 |

同一目标状态下：一条「PAUSED 且今天到期」的任务 → home 说有、goal 说没有；一条「无到期日」的任务 → 两引擎面都说有、看板说无（V12/V17 现象与代码完全对上）。

**新发现（本卡不处置，见「遗留」）**：`backend/app/api/v1/router.py:206-207` 的 `_include_router_if_new()` 去重使 `experience/goal_router.py` 整个 router（含 goal-detail GET 与 criteria-status PUT）被先注册的 `experience_readouts` **完全遮蔽**——goal 详情移动端解析器（`goal_detail_provider.dart`）按 goal_router 载荷形状编写，而线上实际返回 readouts 形状，故 goal 详情屏的达标线/瓶颈/今日一步长期退化为空态。这正是 AUDIT S7「home 说有数据、goal 详情说空」跨屏矛盾的另一条结构性根因。该发现需主会话单独裁决（改路由 or 改解析器），涉及面超出本卡。

### 修法与裁决理由

**事实源定在引擎 goal 域新模块 `backend/app/services/goal_today_view.py`。** 理由：
1. 两处引擎消费面（快照/详情）都是引擎查库得出「有无任务」，裁决点放引擎可让两 surface 从同一函数取数，结构上不可能各说各话；
2. 客户端看板数据（/tasks 列表）本就是同一 task 表的投影，客户端只保留**展示分组**，其判定函数改为与引擎字面同口径并在注释双向声明；
3. 放 service 层符合「handler 走 service 层」硬规则。

口径裁决：**「今日待执行」= `due_date == today` 且状态 ∈ {PENDING, IN_PROGRESS, PAUSED, STUCK, RESTORE}**（即未完成未放弃、到期日为今天）。选择理由：与客户端看板分组口径字面一致（分组仅排除 completed/abandoned）；「无到期日/未来任务」不属于今日，与 UI 的「无日期/明天/本周」分组语义自洽；PAUSED/STUCK 到期仍算「待执行」（用户视角它们还欠着）。下一步选取顺序统一为：进行中 → 优先级降序 → order_index → created_at。

- `experience_readouts._next_task` 改为委托 `fetch_todays_next_task` + `todays_task_payload`（保留 plan 为 None 时用户全局回退语义）；
- `goal_router._todays_next_task` 改为委托同一函数；
- 客户端 `task_board_provider.dart`：抽取公共 `tasksDueOn()` 单一定义点，头部汇总改为「到期日为今天（含当天完成、排除已放弃）」，与今日分组/逾期分组共用；删除死代码 `TaskBoardTodaySummary.label`（无消费者，且其用词正是重复 key `taskBoardTodayNoTasks`）。

**行为变化申报**：home 快照的「下一步」pill 与 goal 详情的「今日一步」从此严格 today 口径——此前 home 会展示任意日期的下一任务，现在无今日任务时显示「今天没有待执行任务」的诚实空态（该空态本就存在）。渲染代码零改动。

### 测试证据（红→绿）

- 新增 `backend/tests/unit/test_goal_today_view.py`（14 用例，先于实现编写）：
  - 红证：实现前 `14 failed`（SSOT 模块不存在，见 `s7_red_proof.txt`）；
  - 绿证：实现后 `14 passed`；
  - 覆盖：两消费面在 9 个场景矩阵上判定一致（含 TRIAGE 指出的 PAUSED/无到期日误判场景）、SQL 条件与纯判定互为镜像、两 surface 实际 DB 查询编译参数携带同一 today+状态集、取数层端到端（conftest 内存 SQLite，非业务库）。
- 回归：`test_b2_criteria_status_endpoint.py` 基线即绿、改后仍绿（4 passed）。

### arb 双 key 合并 + 今日任务 l10n 迁移

- 删除 `taskBoardTodayNoTasks`（app_zh.arb/app_en.arb），保留语义 key `taskBoardTodayNoTasksToday` 的唯一形态 `taskBoardNoTasksToday`；`flutter gen-l10n` 已跑，生成文件已更新。
- goal 域「今日任务/任务状态」相关硬编码迁入 arb（zh+en）：`goalDetailNoTodayStep`、`goalDetailStart`、`goalDetailStartedSnack`、`goalDetailUndo`、`goalDetailEstimated`、`goalDetailMinutes`（带占位符元数据）、`goalDetailStatus`；同时从 `goal_detail_l10n.dart` 删除已被 arb 遮蔽的死定义（goalDetailTodayStep/Complete/CompletedTitle/CompletedBody/Cancel）——`goal_detail_screen_a6_l10n_test.dart` 回归 2 passed，行为零变化（这些 getter 本就被 arb 实例成员遮蔽）。其余 30+ 条目留给 S2 词典批，未扩面。

---

## 2. S11 空态悬空「确认」主 CTA（severity 4）

- **根因**：`minimum_criteria_card.dart` 的按钮块 `if (!criteria.isConfirmed)` 独立于 emptiness 渲染，thresholds 为空时「还没有最低达标线」文案下仍挂「确认」FilledButton。
- **修法**：按钮块条件改为 `!criteria.isConfirmed && criteria.thresholds.isNotEmpty`（D9：空态=为何空+单一明确 CTA 或无 CTA；本页无「添加达标线」独立流，goalDetailModifySnack 明示修改入口保留给收口整合，故空态取纯文案 `goalDetailNoCriteria`——文案已回答「为什么空+现在能干什么」）。
- **测试证据**：新增 `mobile/test/features/goal/presentation/minimum_criteria_card_test.dart`（3 用例）：空达标线无 FilledButton 且有解释文案；有达标线未确认有「Confirm」；已确认无按钮。3 passed。
- 附注：若主会话采纳「遗留」第 1 条（goal 详情数据源修复），真实用户会开始看到有内容的达标线卡，本修复与之正交。

## 3. S13 假保存按钮（severity 3）

- **根因**：`unified_settings_screen.dart` AppBar「确定」ghost 按钮 onPressed 只 `context.pop()`；本页为即时生效模型（每项开关即写 provider，无脏状态概念）。
- **修法**：按 D9「表单提交与即时生效不混用」**删除按钮**（而非改名「完成」——改名仍是假提交语义），AppBar 注释声明原因；返回入口由既有左上角返回箭头承担。确认无任何代码/测试依赖该按钮的状态（全仓 grep `.label`/`l10n.confirm` 均无 settings 相关消费者）。
- **测试证据**：新增 `mobile/test/widget/unified_settings_no_fake_confirm_test.dart`：AppBar 无「确定」、标题「个人偏好」在、返回箭头在（1 passed）；`unified_settings_bgm_test.dart` 回归 2 passed（证明删按钮未破坏设置页渲染与开关持久化）。

## 4. galaxy 测试污染隔离

- **根因**：`test_galaxy_concurrency.py` 直接 `AsyncSessionLocal` 写业务库，全文件无 cleanup，节点名直出星图。
- **修法**：`seeded_ids` fixture（asyncio auto 模式）——种子统一 `galaxy_concurrency_test` 前缀（用户名/邮箱/节点名，未来泄漏可唯一识别）；teardown 按精确 ID 逆序删除 `user_node_status` → `knowledge_nodes` → `event_outbox`（aggregate_type='galaxy_node_mastery' AND aggregate_id=本测试 user_id）→ `event_sequence_counters`（同键）→ `users`。outbox 两张表是施工期新发现：`GalaxyService.update_node_mastery` 会写 mastery outbox 事件，此前方案若只清三张主表会漏。**必须连 PostgreSQL**（C1 原子 UPDATE 依赖 FOR UPDATE/RETURNING 行锁，SQLite 无法验证真并发），故无法用 conftest 内存库。
- **测试证据（含净零足迹验证）**：
  - 修复后 3 passed（concurrent/sequential/stale 全绿）；
  - 运行前后业务库计数完全一致：`concurrency_%` users 24→24、`并发测试节点%` nodes 24→24、新前缀 0→0、outbox 残留 0——**本卡运行净零新增污染**。

### 存量清洗 SQL（只上报，未执行——红线遵守）

已污染存量（读数确认）：24 个 `concurrency_*` 用户 + 24 个 `并发测试节点-*` 知识节点及配套 user_node_status。建议主会话裁决后由 devtools 一次性脚本执行：

```sql
-- ① 预检：确认待删清单（应各为 24）
SELECT id, username FROM users
 WHERE username LIKE 'concurrency\_%' ESCAPE '\' OR username LIKE 'galaxy_concurrency_test%';
SELECT id, name FROM knowledge_nodes WHERE name LIKE '并发测试节点%' OR name LIKE 'galaxy_concurrency_test%';

-- ② dry-run 计数（三者应相等且等于预检数）
SELECT count(*) FROM user_node_status s
 JOIN users u ON u.id = s.user_id
 JOIN knowledge_nodes n ON n.id = s.node_id
 WHERE (u.username LIKE 'concurrency\_%' ESCAPE '\' OR u.username LIKE 'galaxy_concurrency_test%')
   AND (n.name LIKE '并发测试节点%' OR n.name LIKE 'galaxy_concurrency_test%');

-- ③ 正式清洗（事务内，顺序：子表→主表；含 outbox 残留）
BEGIN;
DELETE FROM user_node_status s USING users u, knowledge_nodes n
 WHERE s.user_id = u.id AND s.node_id = n.id
   AND (u.username LIKE 'concurrency\_%' ESCAPE '\' OR u.username LIKE 'galaxy_concurrency_test%')
   AND (n.name LIKE '并发测试节点%' OR n.name LIKE 'galaxy_concurrency_test%');
DELETE FROM event_outbox WHERE aggregate_type = 'galaxy_node_mastery'
   AND aggregate_id IN (SELECT id FROM users WHERE username LIKE 'concurrency\_%' ESCAPE '\' OR username LIKE 'galaxy_concurrency_test%');
DELETE FROM event_sequence_counters WHERE aggregate_type = 'galaxy_node_mastery'
   AND aggregate_id IN (SELECT id FROM users WHERE username LIKE 'concurrency\_%' ESCAPE '\' OR username LIKE 'galaxy_concurrency_test%');
DELETE FROM knowledge_nodes WHERE name LIKE '并发测试节点%' OR name LIKE 'galaxy_concurrency_test%';
DELETE FROM users WHERE username LIKE 'concurrency\_%' ESCAPE '\' OR username LIKE 'galaxy_concurrency_test%';
COMMIT;
```

风险提示：`knowledge_nodes` 可能被 `task_documents`/`study_records`/星图边表外键引用，执行前需按预检 id 补查引用表；若 24 个节点已被真实用户点亮（mastery 交互），建议改为「打测标隐藏」而非删除——由主会话裁决。

---

## 测试统计汇总

| 套件 | 结果 |
|---|---|
| `backend/tests/unit/test_goal_today_view.py`（S7，先红后绿） | 红 14 failed → **绿 14 passed** |
| `backend/tests/unit/test_b2_criteria_status_endpoint.py`（回归） | **4 passed**（基线即绿） |
| `backend/tests/unit/test_galaxy_concurrency.py`（隔离改造后，真实 PG） | **3 passed**，净零足迹已验证 |
| mobile 新增 3 测试文件（S7 口径 2 + S11 3 + S13 1） | **6 passed** |
| mobile 回归（bgm 设置 2 + goal A6 l10n 2） | **4 passed** |
| lint | ruff 全绿；flutter analyze 受触达 lib 文件 info 数与 HEAD 基线持平（75→75），新增测试文件经 `dart fix` 后 0 issue |

## 触达文件清单（17）

引擎（5）：`app/services/goal_today_view.py`（新）、`app/api/v1/experience_readouts.py`、`app/api/v1/experience/goal_router.py`、`tests/unit/test_goal_today_view.py`（新）、`tests/unit/test_galaxy_concurrency.py`
mobile（12）：`features/home/presentation/providers/task_board_provider.dart`、`features/goal/presentation/widgets/minimum_criteria_card.dart`、`features/goal/presentation/widgets/goal_detail_l10n.dart`、`features/user/presentation/screens/unified_settings_screen.dart`、`l10n/app_zh.arb`、`l10n/app_en.arb`、`l10n/app_localizations{,_en,_zh}.dart`（gen-l10n 产物）、`test/features/home/presentation/providers/task_board_today_test.dart`（新）、`test/features/goal/presentation/minimum_criteria_card_test.dart`（新）、`test/widget/unified_settings_no_fake_confirm_test.dart`（新）

## 遗留与移交

1. **goal-detail 双端点遮蔽（新发现，severity ≥4）**：`router.py:206-207` dedup 使 `experience/goal_router.py` 全 router（goal-detail GET + criteria-status PUT）不可达；移动端 goal 详情屏解析器按被遮蔽形状编写 → 达标线/瓶颈/今日一步常驻空态、确认 PUT 404。建议独立卡片二选一：(a) 调整注册顺序/拆路由让 typed 端点生效；(b) 让 `goal_detail_provider.dart` 兼容 readouts 形状并把 criteria-status 迁到 readouts。本卡未动（红线：home/goal/task 现有渲染；架构裁决属主会话）。
2. goal_detail_l10n.dart 其余 ~30 条硬编码待 S2 文案词典批全量迁移（本卡仅迁今日任务相关 7 条 + 清 6 条遮蔽死定义）。
3. 引擎 SSE heartbeat（S12 残余）不在本卡。
4. 会话内构建产物：`backend/app/gen`、`mobile/lib/gen`（gitignored，为跑测试自主仓只读复制）；收工清理清单见文末声明。

## 收工核查声明

- 零模拟器、零 iOS/Android 构建、零浏览器实例；flutter test 全程 `--concurrency=1`；pytest 仅单测级。
- 主仓只读：仅 `rsync` 读取主仓 gen 产物与 `git show` 对比，未写主仓任何路径。
- 未 commit / 未 push；worktree 改动以 `v3-output/B1-A/changes.patch` 交付。
- `/tmp` 残留已清（ext_keys.txt/arb_keys.txt 已删）；mobile/.dart_tool 与 build 产物删除；galaxy 测试对业务库净零足迹已用前后计数证明；未执行任何对既有数据的删除/修改（清洗 SQL 仅上报）。
