# WT334 · plan 链路 subject_name 的 TOUR 内部 token 残留清洗 — REPORT

日期：2026-09-25 ｜ 卡源：wt330 遗留节（v3-output/WT330-SEEDCLEAN/REPORT.md §五）
分支：`wt334-plan-subjectclean`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt334-plan-subjectclean`）

## 一、溯源（plan subject 生成与消费链）

1. **生成侧**：生产代码不拼 token 进 subject——subject 唯一 token 源是评测
   harness `backend/tests/northstar_eval/feature_tour.py:808`
   `subject=f"TOUR科目-{run}"`。subject 参与 `uq_plans_user_sprint_goal_active`
   唯一键（user+subject+target_date，plans.py TOUR-FIX 注释），token 是重跑安全
   去重手段——与 wt330 对任务标题 token 同判：**源头不删，展示面清洗**。
   形态与任务标题不同：`TOUR科目-d91d5df0-10-5dc70d` = TAG 直接贴「科目」（无
   空白）+ token 段，无「专题 N: 尾」结构 → wt330 正则不覆盖，需受测扩展。
2. **消费/展示面**（均原样透出 `plans.subject` 库值）：
   - REST plan 详情/列表/创建/active/today：全部经 `_serialize_plan` →
     `subject` 字段（wt330 报告所称「详情接口 subject_name」即此字段；mobile
     plan_routes.dart:76-78 以 subject/subject_name 参数消费）。
   - day_highlights 推荐文案：`f"{subject} 的第一步就稳下来了"`（plans.py
     `_build_day_recommendation`）。
   - 任务 why_now：`_serialize_task_for_plan_detail` 把 subject 交给
     `build_rule_based_why_now`（diagnostic_triage/diagnostic_map 模板插值）。
   - 任务派生：`POST /plans/{id}/generate-tasks` `topic = plan.subject or plan.name`。
   - Aurora 每日简报：`「备考{subject}的第 N 天」`+ today_focus 兜底
     （aurora/runtime_v1/service.py 原 :250/:2005；红测实录：
     「夜深了，今天是你备考TOUR科目-d91d5df0-10-5dc70d的第 2 天。」）。
   - **生成侧泄漏（节点命名链）**：里程碑触发 `update_knowledge_galaxy`
     （celery_app.py）以 `plan.subject` 造 subject 主线连接
     （`create_or_update_link(source_name=plan.subject)` 会新建名为
     「TOUR科目-…」的脏星）+ 概念节点 `tags=[plan.subject]`。
3. **不涉面**：Subject 表只 seed 干净默认行（plan.subject 不建行）；
   galaxy node detail 的 `subject_name`（api/v1/galaxy.py:595）来自 Subject
   表，不承接 plan subject token。

## 二、修复（复用 wt330 sanitizer，单一实现）

**`backend/app/services/galaxy/title_sanitizer.py` 受测扩展**（不改既有函数签名，
wt330 接线零改动）：
- 新增科目 token 形态：TAG贴「科目/Subject」+ ≥2 段含数字 token 段且至少一段
  ≥6 位（hex 形态）——「AI科目-期末」「CS科目-exam1」「IT科目-2024-2025」
  等正常命名零改写。
- `strip_internal_tokens` 增加科目形态 inline 剥离 → wt330 已接线的
  schemas/galaxy.py 投影**自动**获得科目形态存量兜底（未碰其接线）。
- 新增 `clean_display_subject(subject) -> str`：纯 token 科目 → 空串（调用方
  走既有「无科目」文案兜底）；嵌入形态剥 token；正常科目零改写；None/空 → 空串。

**接入点**（读取/投影 + 生成侧收口，库值不动）：
- `app/api/v1/plans.py`：`_serialize_plan` subject 字段（纯 token → None）；
  `_build_day_recommendation` subject_tail；`_serialize_task_for_plan_detail`
  why_now subject；`_stored_day_recommendation` 存量文案兜底；
  `generate_tasks_for_plan` topic。
- `app/aurora/runtime_v1/service.py`：`_daily_startup_message` 简报 subject、
  today_focus 兜底、`_stored_day_recommendation` 存量文案。
- `app/core/celery_app.py`：`_extract_plan_galaxy_concepts` 从任务内嵌**无行为
  变化提升为模块级**（原函数无闭包依赖，为受测）；tags 走清洗（纯 token → 空）；
  `subject_label = clean_display_subject(...)`，纯 token 置 None → 跳过
  subject 主线连接、`create_node(subject=None)`——不再造 token 脏星。

## 三、测试（红测先行，全部先红后绿）

- `tests/services/galaxy/test_title_sanitizer.py` 追加 6 例：纯 token 科目 → 空、
  嵌入文案剥离、8 种正常科目零改写、None/空、科目形态不波及 wt330 标题行为、
  专题+科目混合块。初版正则无「≥6 位段」约束，红测钉出「IT科目-2024-2025」
  误伤后收紧。
- `tests/api/test_plans_api.py` 追加 3 例：存量脏 subject 的详情/列表/
  day_highlights/why_now 四面无 token + 正常科目零改写 + celery 概念提取
  tags 清洗。红测实录：详情 subject 字段原样透出 `TOUR科目-…`。
- `tests/aurora/test_daily_startup_message.py` 追加 1 例：tokened subject 的
  每日简报无 token（红测实录见上）。
- 定向回归：plans API 全文件 14 过；galaxy services 目录 + task_galaxy_coupling
  + gRPC 三面 + contribution stats + node history/document API + sprint galaxy
  mastery + task_complete outbox + shield invalidation + exam intake（写
  day_highlights 面）+ aurora 简报 = **共 585+ passed, 0 failed**。
- `tests/unit/test_galaxy_concurrency.py` 3 failed/3 error：真实
  `AsyncSessionLocal/engine` 需 live Postgres，worktree+sqlite 下
  `no such table: user_node_status`——wt330 报告 §五已记录的同款环境限制，
  非本卡回归（未碰其表/引擎路径）。

## 四、验收门

| 门 | 结果 |
|---|---|
| ruff check 被碰 7 文件 | 0 问题（aurora I001 已 --fix） |
| 冷缓存 mypy（rm -rf .mypy_cache） | **1449 = 基线** |
| run_all_rule_guards.sh | 见 §五收工记录（exit 0） |

## 五、记录与移交

- harness `feature_tour.py` 本身未改（token 是评测去重合法手段，与 wt330 同判；
  harness 属 eval 资产不在产品链）。
- **观察遗留（不在本卡，供卡池）**：计划 **name** 同被 harness 填
  `f"TOUR 冲刺 {run}"`（feature_tour.py:806），plan 列表/详情 name 字段与
  `_extract_plan_galaxy_concepts` 的概念节点名原样透出/落库——name 形态
  （「冲刺」非「专题/科目」）需第三种 sanitizer 形态，波及 plan name 全展示面，
  建议独立成卡。
- 其余 plan.subject 消费点（learning_paths entity card payload、community
  分享摘要、plan_review/context_builder 的 LLM 上下文）未改：entity card 不渲染
  subject（只 title/description）；LLM 上下文非用户展示面；community 分享摘要
  属低频面，如需可后续卡统一收口。
- Forbidden 区核查：未改 galaxy_service/schemas 既有清洗接线（sanitizer 走受测
  扩展、签名未动）；未碰 growth dashboard/chat_mode/goal 创建链；无 migration、
  无改库；未碰 mobile/gateway；未碰 sparkle-cosmos；主仓只读。
- worktree 无 .env 属正常；pytest 统一
  `DATABASE_URL="sqlite+aiosqlite:///:memory:" SECRET_KEY=… ENVIRONMENT=test`
  前缀运行（复用主仓 venv）。
