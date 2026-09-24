# WT337 · plan name「TOUR 冲刺 {run}」第三形态 token 清洗（wt334 遗留）— REPORT

日期：2026-09-25 ｜ 卡源：wt334 报告 §五 遗留节
分支：`wt337-plan-nameclean`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt337-plan-nameclean`）

## 一、溯源（plan name 生成点与消费链）

1. **生成点**：`backend/tests/northstar_eval/feature_tour.py` S7 攒光子阶段
   （:806-807）`create_sprint_plan_with_tasks(..., name=f"TOUR 冲刺 {run}")`，
   `run = f"{run_id}-{i}-{uuid4().hex[:6]}"`。证据样本
   `TOUR 冲刺 d91d5df0-10-5dc70d` = TAG `TOUR` + 空白 + 「冲刺」 + 空白 + run
   token。name 无唯一键约束（token 纯为 harness 可读去重），与 wt330/wt334
   同判：**源头不删，展示面清洗**。形态精确定义＝「TAG + `\s+` + 冲刺 +
   `\s+` + token run」，与任务标题（专题N…: 尾）和科目（TAG 贴科目无空白）
   均不同，既有两形态正则不覆盖。
2. **消费/展示面**（grep 全链，`plan.name` 全部消费点分类）：
   - REST plan 列表/详情/创建/active/today：`_serialize_plan` `"name"` 字段
     （plans.py:155，主展示面）。
   - 状态通知 toast：`notify_plan_deleted/archived/restored` 的
     `plan_name`（「✅ 已归档计划：{name}」等，state_notification_service.py
     :85/:150/:208 插值）+ 归档时 `new_primary_plan` 标量。
   - 任务派生：`POST /plans/{id}/generate-tasks` `topic = subject or plan.name`
     → 任务标题用户可见。
   - Aurora 每日简报兜底链两处（today_focus :253、「备考{X}的第 N 天」:2014）
     + 回访/comeback 兜底链（:421，落 `subject=` 进简报 payload）。
   - 星图生成侧：里程碑 `_extract_plan_galaxy_concepts` 概念节点 `"name"`（脏星）
     ；`GalaxyPlanConsumer`（plan.created）`seed_from_goal(learning_goal=plan.name)`
     （播种星图根目标）。
   - 星图读取面：节点详情 `relatedPlans[].title`（galaxy.py:682，learning_path
     来源计划）。
   - 聊天工具：`plan_tools.py` create_plan 回包 `"title"`（卡面）+ fallback
     topic 的 name 腿（:422）；`task_query_tool.py` 两处 `"plan_title"`。
3. **不接线面（沿 wt334 判例，LLM/低频/功能性）**：context_builder、
   plan_context、plan_review_service、planning_workflow、checkpoint_runtime
   user_model_snapshot、simulation seed_extractor、progress_narrative、
   report_tools（均 LLM/报告上下文，非用户展示面）；plan_resolution 的 name
   匹配是**功能性**用法（按名找计划），清洗反而破坏匹配，必须保 raw；
   community 分享/导入（wt334 已列低频遗留）；discovery_manager plan_preview
   （discovery 自建计划，harness 不经此链）。plan_tools fallback topic 的
   subject 腿（wt334 形态）未动，属 wt334 遗留清单。

## 二、修复（只加不改，title_sanitizer 单一实现第三形态）

**`backend/app/services/galaxy/title_sanitizer.py` 受测扩展**（前两形态正则、
函数签名、既有接线零改动）：
- 新增冲刺形态：`_SPRINT_NS = TAG\s+冲刺`、`_SPRINT_RUN`（首段 + ≥1 后继段，
  每段须含数字）+ `_qualifying_sprint_spans`（≥2 段且至少一段 ≥6 位 hex 形态
  才认定内部 token，与 wt334 科目形态同级护栏）——「冲刺期末复习」「7天冲刺
  计划」「TOUR 冲刺计划」「TOUR 冲刺 2024」「TOUR 冲刺 2024-2025赛季」、缺
  TAG 的「冲刺 d91d5df0-…」、单段/无数字段形态全部零改写。
- `strip_internal_tokens` 追加冲刺形态 inline 剥离（既有 `_strip_subject_tokens`
  之后）→ wt330 已接线的 schemas/galaxy.py 投影、galaxy API/gRPC 存量兜底
  **自动**获得冲刺形态覆盖（未碰其接线）。
- 新增 `clean_display_plan_name(name)`：纯 token → 空串；嵌入形态剥 token；
  正常命名零改写；None/空 → 空串。
- 新增 `sprint_plan_fallback_name(created_at)`：按创建日兜底命名
  「冲刺计划·M月D日」（None → 「冲刺计划」）。

**纯 token 兜底策略选择（写明理由）**：subject 纯 token → 空串成立，因为每个
subject 消费方已有「无科目」文案链（「这场考试」「你已经走在正确路上了」）；
plan name 是列表/详情的**主标题**，无对应文案链，空标题会渲染空行，且 name
还是 generate-tasks topic 的回退输入（空串会劣化任务派生）。故选择**按创建日
「冲刺计划·M月D日」**：带日期后缀可区分多个归档评测冲刺（eval 会造多个），
且确定性稳定（同一计划每次渲染同名，不闪烁）。生成侧两处不用兜底名而直接
跳过/清洗（celery 概念：纯 token 名 → 整条概念跳过——为一次性评测冲刺造
「冲刺计划·9月25日」星同样是噪声，同 wt334 纯 token 跳过 subject 连接判法；
new_primary 通知标量：纯 token → None）。

**接线点**（读取侧兜底 + 可控生成侧，库值不动；共 8 文件）：
- `app/api/v1/plans.py`：`_plan_display_name` 新助手（clean or 兜底命名）→
  `_serialize_plan` name 字段、generate-tasks topic、deleted/archived/restored
  三个通知 `plan_name`；archived 的 `new_primary_plan` 标量清洗。
- `app/aurora/runtime_v1/service.py`：简报 today_focus 兜底（:258）、「备考{X}」
  兜底（:2021）、回访链 name 腿（:427）三处 `_strip(plan.name)` →
  `clean_display_plan_name`（剥空即落既有下游兜底「今天的核心任务」「这场考试」
  「你的计划」）。
- `app/core/celery_app.py`：概念节点 `"name"` 走清洗，纯 token 整条跳过。
- `app/api/v1/galaxy.py`：节点详情 `relatedPlans[].title` 清洗 + 兜底命名。
- `app/consumers/galaxy_plan_consumer.py`：`seed_from_goal(learning_goal=…)`
  清洗 + 兜底命名（播种链路保持可用，不吞播种行为）。
- `app/tools/plan_tools.py`：create_plan 回包 `"title"` 清洗 + 兜底命名；
  fallback topic 的 name 腿清洗 + 兜底命名（subject 腿未动）。
- `app/tools/task_query_tool.py`：两处 `"plan_title"` 清洗 + 兜底命名。

## 三、测试（红测先行，全部先红后绿）

- 红测实录（接线前）：plan 详情 `name` 字段原样透出
  `TOUR 冲刺 d91d5df0-10-5dc70d`；celery 概念 `"name"` = token 串；aurora
  简报含 token；consumer `learning_goal` = token 串；generate-tasks topic =
  token 串；归档通知 `plan_name` = token 串。**6 failed / 1 passed → 绿**。
- `tests/services/galaxy/test_title_sanitizer.py` 追加冲刺形态 8 例（红测：
  先 ImportError 后行为绿）：纯 token 名 → 空、嵌入剥离、9 种正常冲刺命名
  零改写（含缺 TAG/单段/无 ≥6 位段/无数字段边界）、None/空、三形态互不
  干扰、三形态混合块、fallback 命名 3 例。全文件 34 passed。
- `tests/api/test_plans_api.py` 追加 5 例：存量脏 name 详情/列表走兜底命名
  且正常科目零波及；正常「7天冲刺计划」零改写；归档通知 plan_name 清洗
  （monkeypatch 捕获）；generate-tasks topic 双 token（subject+name）→ 兜底
  命名（monkeypatch executor 捕获）；celery 概念纯 token 名跳过 + 里程碑保留
  + 干净名透传。
- `tests/aurora/test_daily_startup_message.py` 追加 1 例：subject 与 name
  双 token 时简报/message/today_focus 全程无 token（兜底链逐级剥空）。
- `tests/integration/test_stage38_journey_subscribers.py` 追加 1 例：
  plan.created → `seed_from_goal` learning_goal 无 token、走兜底命名。
- 定向回归：plans API + galaxy services 目录 + aurora 全目录 + stage38
  （168 passed）；task_galaxy_coupling + gRPC 三面 + graph shield（95 passed）
  ；task_complete outbox + exam sprint intake + phase4 galaxy services +
  bootstrap seed weights（43 passed）；aurora 全目录（351 passed）。
  **合计 657 passed, 0 failed**。
- 已知环境限制（沿 wt330/wt334 记录，非本卡回归）：
  `tests/unit/test_galaxy_concurrency.py` 需 live Postgres，worktree+sqlite
  下不可跑，本卡未碰其表/引擎路径。

## 四、三形态总表（本卡完成后 sanitizer 形态覆盖清单）

| 形态 | 证据样本 | harness 生成点 | 触发条件（完整形态才触发） | 纯 token 处置 | 清洗入口 |
|---|---|---|---|---|---|
| ① 专题标题（wt330） | `TOUR 专题7-d91d5df0-10-5dc70d: 真题演练与错因回看` | feature_tour.py:806 任务标题 | (TAG)? 专题/Topic N + token run + 冒号 | `clean_display_title` →「专题 N」 | `strip_internal_tokens` / `clean_display_title` |
| ② 科目（wt334） | `TOUR科目-d91d5df0-10-5dc70d` | feature_tour.py:808 subject | TAG 贴科目/Subject（无空白）+ ≥2 段含数字 run 且一段 ≥6 位 | `clean_display_subject` → 空串（调用方无科目文案） | `strip_internal_tokens` / `clean_display_subject` |
| ③ 冲刺名（本卡） | `TOUR 冲刺 d91d5df0-10-5dc70d` | feature_tour.py:807 plan name | TAG + 空白 + 冲刺 + 空白 + run（每段含数字、≥2 段、一段 ≥6 位） | `clean_display_plan_name` → 空串 → `sprint_plan_fallback_name`「冲刺计划·M月D日」或调用方文案链 | `strip_internal_tokens` / `clean_display_plan_name` |

形态③加入 `strip_internal_tokens` 后，wt330 读取侧接线（galaxy schemas 投影、
galaxy API 节点详情、gRPC）对存量脏计划名**自动**获得兜底，无需改其代码。

## 五、验收门

| 门 | 结果 |
|---|---|
| ruff check 被碰 12 文件 | 0 问题（--fix 两处 I001：galaxy.py 注释断行导入、stage38 存量 import 漂移） |
| 冷缓存 mypy（rm -rf .mypy_cache） | **1375 = 基线**（零漂移） |
| run_all_rule_guards.sh | **exit 0（83 rules）**（首次 BG 假失败＝worktree 缺 gateway/mobile gen，cp -RL 拷齐后过） |
| 定向 pytest | 新增红测 7 例先红后绿 + 回归 657 passed, 0 failed |

## 六、记录与移交

- harness `feature_tour.py` 本身未改（name token 无唯一键用途，纯评测可读
  去重；与 wt330/334 同判：源头不删）。三形态源头均在 eval harness S7，若
  未来 harness 退役，sanitizer 形态自动失效为无操作（零改写纪律保证）。
- Forbidden 区核查：未重构前两形态既有正则与接线（sanitizer 只加
  `_SPRINT_*`/`_strip_sprint_tokens`/`_qualifying_sprint_spans` 与两个新公开
  函数，`strip_internal_tokens` 仅追加一次调用）；未碰 growth dashboard/
  chat_mode/goal 链；未碰 mobile/gateway 代码（gen 三件套拷贝属环境件，
  gitignored 不入库）；无 migration、无改库；未碰 sparkle-cosmos；主仓只读。
- 观察遗留（不在本卡，供卡池）：plan_tools fallback topic 的 **subject 腿**
  （`getattr(plan, "subject", None)` 未过 clean_display_subject，wt334 形态
  遗留）；plan_resolution 功能性 name 匹配依赖 raw name（若未来做「按干净名
  匹配」需另行设计，勿直接清洗）；community 分享摘要（wt334 已列）。
- 收工清理：/tmp 自产探针日志已删（wt337_guards*.log）；worktree 保留待主
  会话验收合入。
