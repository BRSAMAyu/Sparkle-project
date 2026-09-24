# WT312 · S-04 报告 — Community Artifact Feedback → Outcome/Evidence（Stream: COMMUNITY）

- **Base SHA**: `7624ec6a`（main HEAD，worktree 创建点）
- **Final SHA**: `47c2a53c`（worktree 分支 `wt312-s04-artifact-evidence`）
- **Patch**: `v3-output/WT312-S04/changes.patch`（`git diff --binary main...HEAD`，164,134 bytes，29 files）

## 一、Evidence 采纳链路图（产品目标①②③的落地）

```
同伴视角（feedback 不自动成为 mastery）
  同伴在我的群/私享看到共享 artifact（S-03 成果反馈段）
    → POST /community/shared-resources/{id}/feedback {verdict: helpful|insightful|applied, comment?}
        · SharedResourceFeedbacks 表 upsert（唯一约束 shared_resource_id+feedback_by）
        · event_bus "community.feedback_given"（flywheel 事件，无 mastery 副作用）
        · 守卫：不能给自己反馈；GALAXY mastery / Goal.mastery / Goal.progress 一概不动

主人视角（显式采纳 = 唯一成长系统入口）
  卡片 isOwn && unadoptedFeedbackCount>0 → 反馈面板（GET .../feedback）
    → POST .../feedback/{feedback_id}/adopt
        ① Goal.metadata_payload["community_evidence"] 追加轨迹回执
           （goal 解析链：显式 goal_id → Goal.plan_id → Plan.goal_id → Task→Plan.goal_id）
        ② services/evidence 既有链（best-effort，无 Redis 诚实降级 0）：
           build_peer_feedback_evidence（EvidenceTarget=EXECUTION_CAPACITY，INCREASE，
           metadata.truth_class="self_reported"——社会证据非服务器观察，与 outcome_ledger
           「声明不构成证明」哲学同口径）→ FusionEngine.update_user_state（Redis 信念面）
        ③ event_bus "community.feedback_adopted" + SystemUpdate「同伴反馈已采纳」
        ④ 幂等：重复采纳返回 already_adopted，不重复注入证据

GJ16 轨迹面（从 check-in 回到 Goal trajectory）
  打卡（可选 goal_id，后端校验归属）→ content_data + CheckinResponse 带回 goal_id/goal_title
    → hub 成功回执「查看轨迹」一键跳 /goals/{goalId}（GoRouter 在同步期捕获，规避失效 element）
    → Goal 详情 community_evidence 卡：采纳回执 + 撤回态如实展示
```

## 二、撤回传播实现（验收②）

`POST /community/shared-resources/{id}/retract`（主人限定，语义对齐既有 revoke 链：软删+广播）：
1. `SharedResource.deleted_at` 落值（读面既有 not_deleted 过滤自动失效；adopt/retract 二次进入按「不存在」拒绝）；
2. 活跃反馈行打 `retracted_at`（不可再采纳，行保留供审计）；
3. 主人所有 Goal 轨迹中引用该共享的已采纳回执 `status→retracted` + `retracted_at`（**派生引用更新，不静默消失**）；
4. `event_bus "community.resource_retracted"`（flywheel）+ WS `share_retracted` 广播到目标群/用户。
读模型消费面：goal 详情卡如实渲染 retracted 态（有测试钉住）。

## 三、与既有权威真源的关系（Forbidden 对照）

- **不重建 evidence 真源**：采纳复用 `services/evidence` 既有 adapter+FusionEngine 链，新增
  `build_peer_feedback_evidence` 是对既有 `outcome_evidence_adapter` 的扩展（同 `_evidence` 工厂）；
- **不新建证据真源表**：`shared_resource_feedbacks` 是社群表面记录（MessageReport 同级先例），
  非五源/信念真源；Goal 轨迹回执落既有 `Goal.metadata_payload` 字段；
- **不 mock 冒充**：全部走真实表/接口/WS；S-03 已把孤儿 SharedResourceCard 接回真源接口，本卡在其上加深；
- **既有行为不动**：`handle_resource_shared` 的 knowledge_node 分享加 mastery +5 属分享侧激励
  （与 peer feedback 不同语义），本卡未触碰、未新增任何自动 mastery 路径，并有守卫测试
  （feedback/adopt 后 galaxy/goal mastery 逐值断言不变）钉住「feedback ≠ mastery」。

## 四、测试证据（命令 + 数字）

| 检查 | 命令 | 结果 |
|---|---|---|
| 后端新增 | `pytest tests/test_s04_community_feedback_evidence.py` | ✅ 9/9（no-mastery 守卫/upsert/采纳链/撤回传播/checkin 链接/轨迹投影/adapter） |
| 后端回归 | `pytest tests/test_community_e2e.py tests/test_fv22_resource_quality.py tests/unit/test_signal_spine.py` | ✅ 1003 passed（两次全绿：schema 修改前后） |
| flutter 定向 | `flutter test --concurrency=1 test/features/goal/goal_detail_screen_a6_l10n_test.dart test/widget/shared_resource_card_test.dart test/features/community/presentation/widgets/groups_hub_view_test.dart` | ✅ 20/20（含 3 个 S-04 hub 流程 + 3 卡片契约 + 1 goal 证据卡） |
| analyze 门 | `python3 scripts/check_flutter_analyze_gate.py` | ✅ ERROR=37 / WARNING=17 / INFO=598（与 S-03 基线一致） |
| 治理守卫 | `bash scripts/run_all_rule_guards.sh` | ✅ exit 0，**83 rules 全过**（含 K/Z/AT/BG/BA-ROUTES/UX-COMP/SPACING-RHYTHM/AX） |
| mypy 棘轮 | `mypy app`（cold-cache，main repo venv 解释器） | ✅ **1796 = baseline 1796**（quality/mypy_baseline.txt 未动） |
| 内存门 | 每次 flutter test 前 `sysctl vm.swapusage` | ✅ 均在 free≥1.2G 放行（最低一次 1607MB；--concurrency=1） |

## 五、验收对照

- [x] GJ16 能从 check-in 回到 Goal trajectory：打卡可选关联 Goal（归属校验）→ 回执一键跳 goal 详情 → 详情页社群证据卡（契约级 widget 测试钉住，含真实 GoRouter push 断言）。
- [x] 撤回后派生引用更新：反馈行 retracted_at + Goal 回执 retracted + WS 广播 + 撤回/采纳/反馈事件入 flywheel（事件总线发布对齐 CommunitySignalBridge 既有形态）。
- [x] feedback/ack 不自动成为 mastery：服务层代码路径不触任何 mastery 面 + 逐值守卫测试。
- [x] 分享 artifact/check-in 关联 Goal/Action：artifact 经共享的 plan/task→goal 链在采纳时解析；check-in 显式 goal_id。

## 六、风险与边界

1. **采纳解析链依赖既有外链**：共享 resource 若无 plan/task 或链上无 goal，采纳要求显式 `goal_id`（400 带引导文案）；knowledge_node 等无结构化 goal 关联的类型必须显式指定——产品上可接受（否则无法落到轨迹）。
2. **信念面 best-effort**：无 Redis（或融合异常）时采纳回执（DB 真源记录）照常落，evidence_count=0 并留 warning 日志；与 task_event_consumer 既有降级口径一致。
3. **SparkleSnackBar 长文案+动作在 390 宽会溢出 ~15px**：本次以紧凑回执文案规避；组件级修复（action 换行/省略）留 UI 卡，未在本卡扩散改动。
4. **WS `share_retracted` 的移动端消费**：本次在 hub 以 `ref.invalidate(sharedResourcesProvider)` 回真源（拉取面已滤软删行）；WS 事件驱动的实时卡片灰化未做，留 realtime 卡（S-01 Locks）。
5. **/tmp 与进程清理**：见第七节，无模拟器/浏览器/独立端口进程遗留；worktree 内 `backend/app/gen`、`backend/gateway/gen`、`mobile/lib/gen`、`mobile/.dart_tool` 为主仓拷贝的 gitignored 产物，随 worktree 回收。

## 七、收工清理

- 删除：/tmp 下 wt312_* 日志与探针文件；无 build/.dart_tool 入库项（gitignored）；未启动模拟器/浏览器；
- 留存：本报告 + `changes.patch`（`v3-output/WT312-S04/`，规范目录）；正式代码改动 29 files 已 commit。

## 八、UNVERIFIED（如实申报）

- **两账户实时（WS 推送反馈/撤回的端到端）**、**Android/iOS 模拟器实测**：按舰队内存纪律（LIGHT，禁模拟器）未执行，GJ16 的 simulator run_mode（V3-224）留待 integration HEAD 阶段或 S-01 realtime 卡；已以真实接口契约级 widget/pytest 测试替代。
- **Alembic 迁移仅经 sqlite create_all 路径验证**（模型↔迁移字段一致性人工核对 + 迁移头链 `gseed_20260923 → s04_20260924` 单头确认）；PG 真库升级留集成窗口执行。
