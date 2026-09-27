# WT750 — day7 终门前合并态跨卡联跑回归报告

- 执行体：wt750（回归验证 Agent）
- 日期：2026-09-28 00:10–00:40 (+0800) 前后
- 目的：本窗集成约 20 卡（community 门族 419/449、streak 表三入口 451/457、evidence 格式 455/471、gateway 426/427/428/461/469）此前均单卡验证，按「合并态必须联跑跨卡重叠文件组合」纪律做一次全量组合回归，供 09-28 07:35 升栈、08:00 gate 参考。
- **总裁决：三段全绿，零失败。无需登记（V3-FIX-483/484 保持空闲），未创建 worktree、未产生任何 commit/push。**

## 1. 环境与基点

- 仓：`/Users/brsama/code/GitHub/Sparkle-project`（工作树 main，只读纪律：除本报告文件外未创建/修改/删除任何文件，未 commit）
- **联跑起点 tip：`0c0b4f4f`**（state(fleet): 轮#236 wt747 集成记账+补位 wt750，2026-09-28 00:00:25 +0800）
- **联跑中途 main 前进 8 提交至 `a1ab24c9`**（详见 §3；其中 1 提交触及本联跑测面：wt749 的 V3-FIX-469 修复 `52383b48`，改 `backend/gateway/internal/cqrs/outbox/repository.go` + 新增 `repository_test.go`）。**该 8 提交对 backend Python 面与 mobile/ 面零改动**（仅 gateway Go + docs + fleet state），Phase 1/3 结果在两 tip 间可转移；Phase 2 已在 `a1ab24c9` 定点重跑取单一 SHA 裁决（§4）。
- 工具链：Python 3.11.15（`backend/.venv`，pytest 9.0.2）｜go1.25.7 darwin/arm64｜Flutter 3.41.3 (stable)
- Backend 命令口径（按任务逐字）：`cd backend && DATABASE_URL='sqlite+aiosqlite:///:memory:' SECRET_KEY=v ./.venv/bin/python -m pytest <paths> -q`
- 主仓工作树在联跑开始前已存在的他人改动（非本 Agent 产生，未触碰）：`v3-output/WT401-Q03-VISUAL/` 下 3 个 probe json 处于 modified 态（其中 `contrast_probe_longtail.json` 在联跑中途新出现，同为并发 Agent 所为）。

## 2. Phase 1 — Backend 组合（四段，全部 EXIT=0）

| 段 | 面 | 文件数 | 通过 | pytest 时长 |
|---|---|---|---|---|
| 1a | community 门族（419/449）+ community api/security 面 | 10 | **85 passed**, 0 failed, 0 skip | 22.54s |
| 1b | streak 表三入口（451/457）+ achievement + inventory + shop + guest seed | 16 | **112 passed**, 0 failed, 0 skip | 30.18s |
| 1c | evidence 格式（455/471）+ belief/fusion/claim/adapter/event registry 契约 | 7 | **68 passed**, 0 failed, 0 skip | 1.02s |
| 1d | 幂等/error_handler 面（find by name） | 9 | **46 passed**, 0 failed, 0 skip | 12.47s |
| 合计 | | **42** | **311 passed** | ~66s |

各段明细：

- **1a community**：`tests/api/test_comment_faces_gates_softdel_block.py`、`test_post_write_gates_softdel_block.py`、`test_post_comments_cohort_filter.py` + `find tests -path '*community*'` 的 api/security 子集：`test_community_accountability_new_guest_500.py`、`test_community_accountability_route_shadowing.py`、`test_community_feed_cohort_filter.py`、`test_community_group_file_sharing_api.py`、`test_s04_community_outcome_evidence.py`、`test_s05_community_reconnect_retract_two_account_e2e.py`、`tests/test_community_security.py`。
- **1b streak/achievement/inventory**：`tests/unit/test_inventory_consumable_effect_wiring.py` + `tests/unit/test_achievement_{contract_weekend,engine_phase3,engine_regression,event_consumer,event_publishers,observability_api,system_alignment,transparency_meta}.py` + `tests/unit/test_streak_{engine_local_day_freeze_max,quality_local_today,quality_service,weak_persistence}.py`、`test_growth_streak_local_clock.py` + `tests/unit/test_shop_service.py` + `tests/services/test_guest_seed_service.py`（路径均 find 先行核实）。
- **1c evidence**：`tests/unit/test_belief_{fusion_engine,observation_models,recovery_simulator,trace_inspector}.py` + `test_fusion_engine_cross_process_claim.py` + `test_outcome_evidence_adapter.py` + `tests/contract/test_event_registry_contract.py`。`tests/integration/test_belief_shadow_real_redis.py` 未跑（`SPARKLE_RUN_REAL_REDIS_TESTS=1` 环境门，不碰真实运行栈纪律；与 WT744 单卡口径一致）。
- **1d 幂等/error_handler**：`tests/integration/test_shop_purchase_idempotency.py`、`tests/services/test_event_idempotency_isolation.py`、`tests/unit/test_{error_mastery_idempotency,event_bus_group_scoped_idempotency,idempotency_middleware,intervention_feedback_idempotency,scene_idempotency,v3_fix336_intent_stable_idempotency}.py`、`tests/unit/test_v3_fix217_error_handler_uid.py`（`*idempoten*`+`*error_handler*` find-by-name 全集，无遗漏文件）。

## 3. Phase 2 — Gateway 全量（go test + go vet）

- **运行 1**（Phase 2 时段，tip 在 `0c0b4f4f..a1ab24c9` 间不可辨）：`go vet ./...` exit 0 零输出；`go test ./...` exit 0，12 测试包全 ok（cqrs/worker 走缓存），689 PASS / 0 FAIL / 31 SKIP，wall 36.04s。
- **运行 2（定点重跑，裁决基准）**：运行前 `git rev-parse HEAD` = `a1ab24c9`、运行后复核同值，期间无再前进。`go vet ./...` exit 0；`go test ./... -count=1`（绕缓存）exit 0，**692 PASS / 0 FAIL / 32 SKIP**，wall 35.92s（-v 全量复核实录于 `/tmp/wt750/p2_test_rerun_v.log`）。
- 与运行 1 的 +3 PASS / +1 SKIP 差 = wt749 于中途落 main 的 `repository_test.go` 新测试面（含 1 条真库门控 SKIP，见其登记「真库门控用例无库如实 SKIP」），方向吻合。
- **469 状态注记**：联跑开始时台账 V3-FIX-469 为 OPEN（processed_events 幂等闸 uuid.Parse 失效）；中途 `6fe3001f` 登记 FIXED@060d541f。本报告 Gateway 绿含该修复及其新增测试。**台账顺带新登记的 V3-FIX-481（processedIDs sync.Map 无界增长）仍 OPEN**——现测试面不触达、不会使套件变红，晨门相关方应知此为已知开放邻接项，非本联跑发现。

## 4. Phase 3 — Flutter

- `flutter analyze`：**No issues found!**（0 error / 0 warning / 0 info），analyze 12.6s（wall 19.99s）。
- `flutter test`（全量，一次跑完 559.08s ≈ 9:19 < 20 分钟，无需分段）：**+2636 passed, ~23 skipped, 0 failed — "All tests passed!"**，EXIT=0。
- 联跑中途 8 提交不含 `mobile/` 改动，结果对 `a1ab24c9` 有效。

## 5. 与既有基线的差异说明

- **mypy 132–133 暖冷缓存差**：已知事项（WT744-FMT455 notes.md 实录：干净缓存基线 133 vs 任务口径 132 差 1 系缓存/环境抖动，判据以「与基线逐行 diff 为空」为准）。mypy 不在本联跑三段命令范围内，本报告只记录该已知差，未新跑 mypy，无新增信息。
- **单卡 → 合并态对照**：
  - 1c evidence **68 passed 与 WT744-FMT455 单卡基线（68 passed in 1.20s）完全一致**，合并态零回退。
  - 1d 含 461 邻接面（`test_event_idempotency_isolation` 等）全绿，与 wt749 登记「461 不回退」一致。
  - 1a/1b 与 WT741-CMT449、WT742-INV457、WT737-FIRST451 各自单卡绿一致；合并态新增跨文件同进程组合顺序暴露面，未见任何冲突/串扰。
- **Flutter**：analyze 与 WT737 等单卡披露的「触达文件 0 新增」口径相符；本次为合并态全量 `flutter test`（2636/23），可作为本窗合并态基线数记录。
- **异常输出摘录**：无——三段全程零 FAIL/零 ERROR；全部原始日志存 `/tmp/wt750/`（p1a_community.log、p1b_streak_ach_inv.log、p1c_evidence.log、p1d_idem.log、p2_vet*.log、p2_test*.log、p3_analyze.log、p3_test.log）。

## 6. 查证面与边界（零发现亦如实记录）

- 已查证：Backend 42 文件（311 例）合并态组合、Gateway 全仓 12 测试包（692 例）+ vet、Flutter analyze 全量 + test 全量（2659 例进出）。合计约 **3662 用例全绿 / 55 skip（全部为既有环境门控或条件跳过）/ 0 fail**。
- 未跑/超范围（如实披露）：mypy 与 ruff/black 门禁（不在三段命令范围，且有 §5 已知缓存差口径）；真实 PG/Redis/MinIO 运行栈（纪律禁止）；`test_belief_shadow_real_redis`（环境门）；CI 在航长尾（本联跑为本地合并态视角，与 CI 互补，不重跑）。
- 本报告与日志文件是本次运行对主仓的唯一写入（本报告为 v3-output 下新建未跟踪文件，按 fleet 惯例交集成记账收编）；未 commit、未 push、未建 worktree（登记条件未触发）、未触碰 docker/状态文件/他人 modified 文件。

## 7. 登记情况

- **无失败，无登记。** 预分配号 V3-FIX-483/484 经 grep 台账复核空闲（开工时与收尾时均无占用），保持空闲可用。
