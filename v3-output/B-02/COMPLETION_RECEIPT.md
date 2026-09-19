# Completion Receipt
- Task: B-02 · 数据真实性、Mock 污染与指标 Lineage 基线（Stream: BASELINE / Gate: V3-0 / Risk: high / Resource: LIGHT）
- Agent: Worker 卡 B-02（Sparkle V3 Fleet）
- Base SHA: f01f4ae81ebd645b8f313afd2e9a243cfe83a3f0
- Final SHA: f01f4ae81ebd645b8f313afd2e9a243cfe83a3f0（未 commit，按指示保持工作树；新增文件见下）
- Status: READY_FOR_REVIEW
- User-value change: 无直接用户可见变更（BASELINE 盘点卡）。产出阻断假数据进入 V3 的事实基线：字段级 lineage（lineage.csv）、mock/seed 污染面清单（data_truth_inventory.csv/json）、两条可复现的高严重度污染证据（排行榜 cohort 污染、IsPro×游客种子）、1 个红测钉住 mock→Isar 生产缓存路径。
- Files/components:
  - 新增 v3-output/B-02/lineage.csv（22 个用户可见数字的 UI→repo/API→service→DB/formula 字段级溯源 + 真实性评级）
  - 新增 v3-output/B-02/data_truth_inventory.csv 与 .json（14 项 mock/seed/污染面清单 + DB cohort 事实）
  - 新增 v3-output/B-02/FINDINGS.md（证据 SQL、复现步骤、后续任务映射建议 T-truth-*）
  - ~~新增 mobile/test/core/statistics/mock_statistics_guard_test.dart（红测，当前 RED，预期内）~~ **复核修订 C1**：红测文件**未随收编入库**（沙箱 flutter test 基建挂起、CI 已关停，文件仅存工作沙箱已随 worktree 回收）；污染机制以代码链路 + `dart run` 探针实证（见同目录 REVIEW_RECEIPT 断言 3）。
- Tests executed + results:
  - 主仓 DB 只读查证（docker exec sparkle_db psql，只 SELECT）：users 分布 guest 160/email 52/seed 7；user_node_status 8135 行中 guest 占 8050（98.9%）；user_streak_stats guest 最长 30 天 vs email 最长 1 天；user_achievements guest 944 行 vs email 3 行；understanding_depth_daily 149 行（2026-09-18，score 0.275–0.933，avg 0.384）。
  - 排行榜同权重复算 SQL：top-50 = 100% guest 账号，top_score 132.5（见 FINDINGS.md F1，可直接复现）。
  - 红测（复核修订 C1：**文件未入库**）：测试逻辑为源码契约守卫，对当前 `_generateMock` 实现必然 FAIL（RED）；沙箱内 `flutter test` 无法完成 loading（见 Known limitations），RED 判定由下行 `dart run` 探针确定性验证。
  - 红测逻辑独立验证（`dart run` 纯 Dart 探针，等价断言逻辑）：三个 `fetchFromApi` 实现体中共 25 个生成 mock 标记（focus 8 / capsule 10 / agent 7）→ 守卫判定 RED（当前违反 D20，预期内）。
  - `flutter test test/core/statistics/mock_statistics_guard_test.dart`：在沙箱环境 loading 阶段挂起至 12 分钟 invoker 超时（`+0 -1: Some tests failed`，TimeoutException in loading）。对照实验：**既有**小测试 test/unit/hash_utils_test.dart 同样在 loading 挂起超时 —— 证明是本沙箱 `flutter test` 基建问题（测试 isolate 无法完成加载），与红测内容无关。
  - 网关/引擎存活：:8080/healthz 200、:8000/health 200；/api/v1/insights/understanding-depth、/dashboard/status、/leaderboards 未授权均 401（隔离正常）。
- Simulator/device journey + results: 不适用（LIGHT 盘点卡；未运行模拟器，符合磁盘纪律）。
- Screenshots/video: 无（无 UI 变更）。
- Trace IDs / actual model / latency / usage (if AI): 不适用（本卡无 AI 调用；understanding-depth 为离线聚合指标，非本卡产生）。
- Negative/failure cases:
  - 排行榜 SQL 复算先用错权重（10/5/3/2）得出 top_score 833，已按 leaderboard_service.py 实际权重（1.0/0.5/2.0/1.5）修正复算为 132.5，两次结论一致（top-50 全 guest）。
  - 移动端未发现 /insights/understanding-depth 的消费端（后端先上线），已在 lineage 标注。
  - 未对网关做带鉴权的写路径实测（避免向生产库写入游客/数据），改以 DB 只读 + 401 探测替代。
- Known limitations:
  - 静态审读为主，部分评级（如 weekly_stats_service、achievement_engine 内部分支）基于代码链路而非端到端 API 实测（无测试账号凭据，且红线禁止向主仓 DB 写入）。
  - 本机 IsarCore 测试环境有预存 segfault（test/unit/sync_engine_test.dart @Skip），故红测采用源码契约守卫而非真实 Isar 集成断言；污染机制由 hybrid_statistics_repository.dart 代码路径实证。
  - `flutter test` 在本沙箱对所有测试（含既有测试）在 loading 阶段挂起超时（对照实验证据见上）。红测的 RED 判定由等价逻辑的独立 `dart run` 探针确定性验证（25 个 mock 标记）；Reviewer 在正常环境运行该单测文件应得到 1 个 failure（= RED）。
- Rollback/kill switch: 本卡无运行时行为变更；删除 v3-output/B-02/ 与 mobile/test/core/statistics/ 即完全回退。未 commit。
- Suggested reviewer checks:
  1. 独立执行 F1 排行榜复算 SQL（FINDINGS.md 第二节），确认 top-50 全为 registration_source='guest'。
  2. 打开 backend/app/services/leaderboard_service.py 确认无 registration_source 过滤；gateway internal/service/user_context.go:129 确认 IsPro=FlameLevel>=3。
  3. ~~运行 mobile/test/core/statistics/mock_statistics_guard_test.dart 确认 RED~~（复核修订 C1：文件未入库）；改为对照 hybrid_statistics_repository.dart:330-354 的 _putInWarmCache/isFullySynced 路径与三个 provider 的 _generateMock* 实现（Reviewer #1 已代码级实证，见 REVIEW_RECEIPT 断言 3）。
  4. 抽查 lineage.csv 中任意 3 行（建议：streak、understanding-depth、galaxy_mastery）沿 UI→API→service→DB 亲自走一遍。
  5. 核对 data_truth_inventory.json 的 DB 事实数字与本机 sparkle_db 一致。
