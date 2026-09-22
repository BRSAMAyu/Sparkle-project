# INTAKE：exam-sprint intake 修复报告

- 卡：**INTAKE**（plan_id UUID bug + BP-7 非幂等 403）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt102`（基线 main@db9e9fd8）
- 交付物：`v3-output/INTAKE/changes.patch`（仅 2 个跟踪文件）+ 本报告
- 状态：完成，未 commit / 未 push

## ① 根因（各一句）

1. **plan_id UUID ValueError**：mock/真实分叉——真实生成器 `_generate_plan_and_tasks` 返回 `str(plan.id)`（plans.id 是 GUID 列，恒为 UUID），而存量红测试的 mock 返回假字符串 `"plan_123"`；服务层后来为北极星指标加的 `UUID(generated.plan_id)`（intake :155）对假字符串必然抛 `badly formed hexadecimal UUID string`。上游（PlanService.create）从未产出非 UUID id。
2. **BP-7 非幂等 403**：`intake()` 无条件走 `PlanService.create`，后者经 `PlanQuotaService.check_and_raise` 在用户已有 3 个 active 计划时抛 `QuotaExceededError`（全局映射 403「已达计划数量上限(3个)」）；LOOP1 证据（`v3-output/NORTHSTAR-LOOP1/evidence/steps/B3*.json`）显示 B2 建目标已产出一个冲刺计划，B3 复跑 intake 又试图造第二个——配额已满则 403，未满则静默双计划。

## ② 幂等语义裁决：**同目标幂等返回既有（reuse），不做受控重建**

- **目标同一性键**：`(user, type=SPRINT, subject, target_date=exam_date, is_active, 未软删)`，取最新一条。
- 命中 → 复用既有 plan 及其 Day-1 任务（`order_index ∈ [1000,2000)`）重建 launch bundle，**跳过** plan/task 创建；未命中（不同 subject 或不同考试日 = 不同目标）→ 走原创建路径，配额语义原样生效。
- **论证**：(a) 北极星剧本把断线重连/重复提交列为一等场景，该形态是同表单重放，重建只会产出等价内容并消耗配额；(b) 重建会新开一组 task 行，用户在旧任务上已有的进度/状态被静默作废，属破坏性操作；(c) 「改主意」的重参数诉求属于计划调整流（planning 会话/plan 调整接口）职责，intake 只需保证可重入；(d) 北极星 intake 指标是按 plan_id 的 `_upsert_event`，复用复跑不会重复计数；planning session 键在 redis 中按 conversation 覆盖写，profile 写为 upsert——intake 其余副作用天然幂等，唯一的非幂等点就是 plan/task 创建，现已关闸。
- 侧写证明：`strategy_preview.first_day_focus/output` 从既有 Day-1 任务的 `guide_json.objective / output_action` 还原，响应形状零变化。

## ③ 红→绿统计

| 测试 | 修复前 | 修复后 |
|---|---|---|
| `tests/unit/test_exam_sprint_intake_service.py::test_exam_sprint_intake_saves_session_and_returns_launch_payload`（存量红，双克隆 bisect 已证存量；本 wt 基线复现：`1 failed, 1 passed`，栈在 :155 UUID ValueError） | FAIL | PASS |
| `…::test_exam_sprint_intake_reuses_existing_plan_for_same_goal`（本卡新增：预置同目标 active sprint plan + Day1/Day2 任务，把 `_generate_plan_and_tasks` 打成抛 `QuotaExceededError` 的地雷；断言复用既有 plan、生成器未被调用、无新计划） | FAIL（地雷引爆，复现 BP-7 403 链路） | PASS |

**回归（pytest 全绝对路径，SECRET_KEY 以内联 env 注入，未落任何 .env）**：

- exam_sprint 核心六文件 = **33 passed**（intake 3 + review 11 + diagnose_api 1 + diagnostic_service 8 + policy 3 + api 7），与 P0-1 后基线 33+8 构成吻合，P0-1 诊断面零回退
- dashboard 2 + north_star_metrics 3 → **38 passed**（85.7s）
- 其余 sprint 命名套件（pack_loader / pack_registry / galaxy_mastery / daily_reminder）→ **51 passed**（26.0s）
- 风格：ruff check、black --check(120) 双绿；治理守卫 `run_all_rule_guards.sh` 全绿除 **BG**（proto 跨语言生成物缺失）——已用规范允许的克隆基线法证明：`git clone <wt102> /tmp/wt102-intake-baseline` 后 BG 在干净 HEAD 上同样失败 exit 1（fresh worktree 从未跑过 `make proto-gen`，缺 Dart/Go 生成物），与本卡 2 个 Python 文件零交集，判存量环境性失败。
- K/Z 两守卫曾在首轮失败：原因是主仓 `backend/app/gen/proto/error_book/` 下存在**指向主仓绝对路径的自引用 symlink**，`cp -R` 复制生成物时被原样带入 worktree，守卫 resolve 后越界崩溃；已把 3 个 symlink 替换为真实文件副本，K/Z 转绿。主仓侧该 symlink quirk 建议另行立卡。

## 红线面 / 冲突面

- **API 契约零变化**：`ExamSprintIntakeResponse / ExamSprintLaunchPayload` schema 未动；wire 上 `plan_id` 仍是 UUID 字符串（仅把 UUID→str 的序列化点收敛到 launch 边界），`plan_route` 形状不变。BA-ROUTES 守卫绿（349 网关路由 ↔ 959 引擎路由）。
- **mobile 消费面零变化**：`mobile/lib/features/plan/domain/entities/sprint_statistics.dart` 等以 `String planId` 消费 `plan_id`，形状不变，无需 gateway/mobile 同步。
- **冲突面**：全仓 grep 确认 `GeneratedPlanBundle` 仅 intake 服务与本测试引用；无并行卡触碰 exam_sprint（P0-1 诊断面只增不改 intake 路径）。

## 改动清单（= changes.patch）

1. `backend/app/services/exam_sprint_intake_service.py`
   - `GeneratedPlanBundle.plan_id: str` → `UUID`（DB 原生类型贯穿；列类型 GUID 故选原生 UUID 而非字符串规范化），真实生成器直接传 `plan.id`，launch 边界 `str()` 序列化；`intake` 不再对字符串二次 `UUID()` 解析（该 bug 类永久关闸）
   - 新增 `_find_reusable_sprint_plan`（同目标 active sprint plan 查询，含 `deleted_at` 过滤）与 `_bundle_from_existing_plan`（Day-1 任务带还原 focus/output）
   - `intake()` 生成前先查复用，命中即跳过 plan/task 创建
2. `backend/tests/unit/test_exam_sprint_intake_service.py`
   - mock `plan_id="plan_123"` → `uuid4()`（对齐真实契约），断言 `UUID(response.launch.plan_id) == mocked_plan_id`
   - 修正两处**被 155 行早死掩盖的存量断言腐化**：redis planning session 键实为 `planning:session:{user_id}::{chat_session_id}`（`PLANNING_SESSION_PREFIX` 自带尾冒号 + `save_session` 的 user_prefix 再补一个，双冒号是现网真实格式），且缺 user 作用域段
   - 新增 BP-7 幂等红测试（见③）

## 残留与建议（不阻塞合入）

1. **并发窗口**：同 user 同目标的两个**并发** intake 仍可能各自创建（查询-创建间无唯一约束）；顺序重放（剧本场景）已完全幂等。根治需 `(user_id, type, subject, target_date)` 部分唯一索引（Alembic 迁移），超出本卡 LIGHT 范围，建议立卡。
2. 双冒号 redis 键格式建议后续统一（现网读取/写入同格式自洽，非 bug，但易踩坑）。
3. BG 守卫在 fresh worktree 恒红：建议守卫 runner 对缺失生成物给出「先跑 make proto-gen」的显式提示或在 wt 初始化脚本里自动生成。

## ④ 收工核查

- [x] worktree 内无构建产物入库：未产生 `mobile/build`、`.dart_tool`、venv、node_modules
- [x] `/tmp` 自清：`/tmp/wt102-intake-baseline`（基线克隆）已删除；调试脚本 `test_zz_debug_tmp.py`、`/tmp/wt102_debug_test.py` 已删除
- [x] 未起模拟器 / Gradle / 浏览器实例，无 HEAVY 任务，无遗留进程（pytest 串行跑完即退）
- [x] 未创建任何 `.env`（SECRET_KEY 全部内联 env 注入）
- [x] 主仓只读未动：仅 `cp -R` 读出 `backend/app/gen`（gitignore 生成物）供测试基座使用
- [x] git status 干净度：仅 2 个预期修改文件 + `v3-output/INTAKE/`（本卡产物）；守卫运行刷出的 `stage22_prompt_coverage_baseline.md` 时间戳 churn 已 `git checkout --` 单文件还原
- [x] 未 commit / 未 push
