# WT654 · B-03 跨端 Journey Simulator Harness 基线（v2 统一化收口）交付报告

- 日期：2026-09-27 ｜ 执行：wt654 ｜ 状态：**READY_FOR_REVIEW**（静态可证部分完成；运行级待验清单见 §7）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt654-b03`，分支 `agent/node-b/wt654/b03`
- base SHA：`05141fb6`（main 当时 HEAD）｜ final SHA：见 §8（commit 后生成 changes.patch）
- 权威卡面：`v3/07_tasks/cards/B-03.md`（该卡 2026-09-19 曾以 ee885386 首轮 ACCEPT；本轮为 v2 统一化收口，不重建已有权威）

## 0. 一句话结论

在既有三端 harness（ee885386）之上补齐任务卡 work#2 的三个统一化缺口——**仿真/真实数据 schema 区分契约**（红线）、**persona library 接入**、**网络切换统一步 + test clock 裁决块**——全部静态可证并配 24 个钉测试；三端可重复启动脚本/非零退出/不许绕过 UI 三条验收在当前 HEAD 逐条复核仍成立。未做任何运行级宣称。

## 1. 卡面验收逐条对照

| 卡面验收 | 状态 | 证据 |
|---|---|---|
| 三平台可重复启动脚本或明确 unsupported 原因；run 产出 build SHA/device/time/screenshots/log refs | **成立（v1 已建，v2 复核+增强）** | 脚本：`run_macos_journey.sh`/`run_web_gj01.sh`/`run_android_shell.sh`；unsupported 原因矩阵在 HARNESS.md §4.4（v2 新增 4 行：android 限速/macos/api 网络切换/受控时钟）；manifest 字段 v2 扩为 schema/lane/SHA/device/time/persona/clock/build（HARNESS.md §3） |
| 失败返回非零，不允许"没找到模拟器=PASS" | **成立，且新增端到端钉测试** | runner `driver_start` 失败落 FAIL+退出码 1；本轮新增 `test_cli_failure_exits_nonzero`（子进程真跑 CLI，网关不可达→退出码非零）与 `test_api_run_unreachable_gateway_is_honest_fail`（FAIL 证据落盘三件套） |
| 文档说明 simulator 不得绕过 UI | **成立** | HARNESS.md §0.1（逐 backend 通道说明）+ `drivers/base.py` 红线 docstring；api lane 双通道标注（lane 字段+summary） |

## 2. work#1 盘点（v2 刷新）

全表见 HARNESS.md §8。要点：macos_journey_test.dart=macOS 权威真 UI（复用）；Android instrumentation 基线只做壳（ui_steps unsupported 诚实声明）；Web=CDP 语义树真 UI；`scripts/journey_smoke.sh`/CI simulation-benchmark 是后端测试线（同名不同物）；`SeedExtractor` 是**产品仿真训练功能**（`backend/app/services/simulation/`），不是测试仿真器，harness 不依赖不重建；`real_drive.py`（ns001）是真实驱动权威仪器，只读参照其 schema 精神，未触碰其文件与 /tmp 运行态。

## 3. 本轮变更（work#2 统一化缺口收口）

1. **仿真/真实数据区分契约（红线，schema/标记层面）**：
   - `run_manifest.json` 顶部自标识 `schema=sparkle.journey.simulator.run.v1` + `lane=simulator-ui|simulator-nonui`（结构化，替代 v1 只藏在 summary 文本的 non-ui 注记）；
   - `steps.json` 改为 envelope `{"schema": "sparkle.journey.simulator.step.v1", run_id/journey_id/backend/lane/ok, steps[]}`（v1 为裸数组；仓内无脚本消费者，历史 run 目录不受影响）；
   - 账号命名约定成文：仿真 `jh_` 前缀 vs 真实驱动 `northstar_` 前缀（HARNESS.md §1）；
   - 与 `sparkle.northstar.real-drive.*` 的互斥由钉测试直接对账 `real_drive.py` 源码 schema 常量守护。
2. **persona reset 统一**：`loader` 接入 `v3/05_metrics_eval/persona_library.json`（路径可 `JOURNEY_PERSONA_LIBRARY` 覆盖）；journey 声明 `"persona"`（GJ01/GJ08=P04、GJ04=P01，按 goal 对齐选择）；加载期校验（未知 id=ValueError 不吞）；persona 全量入 `run_manifest.persona` 与 journey_definition 快照。步参数化（`{{persona.goal}}`）留 TODO §6.3。
3. **网络切换统一步 `set_network`**：web=CDP `Network.emulateNetworkConditions`（offline/online/slow，Slow-3G 同源档可覆盖）；android=系统飞行模式（offline/online，`airplane_mode_on` 回读确认）；macos/api=诚实 unsupported 并登记原因（§4.4）。模拟生命周期=driver 进程生命周期，不跨 run 泄漏。
4. **test clock 裁决块**：`run_manifest.clock={"mode":"wall","controlled_advance":"unsupported","reason":…}`——裁决权威=real_drive.py「时间语义裁决方案 c」（产品无时钟 seam，假钟撕裂一致性+伪造时间戳）。钉测试守护：静默引入受控时钟必先改测试=强制重裁决，FIX-330/333 同族纪律（不伪造、不无源宣称）。
5. **HARNESS.md v2**：§1 区分契约、§3 manifest 字段、§4.4 unsupported 矩阵扩容、§5 统一化现状刷新、§6 TODO 重排、§8 盘点刷新；Web GJ01 阻塞缺陷 V3-FIX-17 已修（FIXED@77b3cb31）状态同步。

## 4. 与既有仿真基建的复用关系

不重建任何已存在权威：macOS 继续包装 `macos_journey_test.dart`；web/CDP、api lane（acceptance_memory_revival 模式）原样保留；本轮只做**增量统一**（models/loader/runner/evidence/四 driver 共 8 文件 + 3 个 journey JSON 的 persona 声明 + 3 个新测试文件），未动 tests_e2e/、CI workflow、northstar 文件、/tmp 运行态。

## 5. 静态验证（全部本轮实跑）

- 定向测试：`backend/.venv/bin/python -m pytest scripts/devtools/journey_harness/tests/ -q` → **24 passed**（loader 10 / markers 7 / policies 7；含 CLI 端到端非零退出、schema 互斥对账、clock ratchet、SELECT-only 只读纪律钉）。
- ruff（/tmp/ruff112/bin/ruff）触达目录 `scripts/devtools/journey_harness/`：**All checks passed**（serve_web.py:109 的 noqa 格式 warning 为既有，未触碰）。
- mypy：棘轮口径=`cd backend && mypy app`，本卡零 backend/app 触达，不可能推高基线。
- 守卫套件 `bash scripts/run_all_rule_guards.sh`：**82/83 组通过**；`BG` 初红系 worktree 缺 gitignored Go gen（按先例 cp -RL 主仓 backend/app/gen、mobile/lib/gen、backend/gateway/gen 后 **PASS**）；`BA-ROUTES`、`COMM-LB` 为 **base 05141fb6 既有红**——wt647 lint 批四将 gateway registerREST 改单参形态，而守卫适配提交 `12eafcdb`（「三守卫适配 wt647 registerREST 单参形态」）在 base 之后才落 main（`git merge-base --is-ancestor` 实证不在 base），base 树内旧守卫脚本对新形态必然红；两守卫在 main（8a0a868f）实跑 PASS。与本卡零文件交集（本卡 diff 无任何 backend/gateway 或 scripts/guards 文件）。守卫清单无任何 journey/harness/simulator 相关条目。

## 6. 并行卡避让确认

未触碰 mypy（wt648）、analytics、纯审计（wt652）、north_star 文件（wt653）任何文件；harness 面与四卡零交集。新开 FIX 号：本轮未发现需登记的新产品缺陷，未占用 FIX 号。

## 7. 运行级待验清单（交主会话；本地栈升明晨 day7 窗口后可执行）

1. **三端 GJ01/GJ01S 重跑产出 v2-schema 证据**（macOS 访客 journey / Web GJ01S / Android 壳），验证新 manifest/steps envelope 落盘与 `jh_` 前缀账号——一次性覆盖验收第 1 条的运行级面。
2. **Web GJ01 全 18 步复验**：V3-FIX-17 已修（77b3cb31），submit_register 应首次走通——若仍红即为产品回归，独立登记。
3. **set_network 运行级**：web CDP emulation（offline 断网→错误态→online 恢复）与 android 飞行模式回读，各一跑即可（GJ13 offline 场景可作首个消费者）。
4. 守卫 `BA-ROUTES`/`COMM-LB` 在集成 HEAD（含 12eafcdb 守卫适配，≥该提交）应为绿；若红说明集成头早于 12eafcdb，属 wt647 序列问题非本卡。
5. day7 终门（明 08:00）不受本卡影响（零产品代码触碰）。

## 8. 交付物

- `scripts/devtools/journey_harness/`：models/loader/runner/evidence + 4 driver + 3 journey JSON + `tests/`（3 文件 24 用例）
- `v3-output/B-03/HARNESS.md` v2（单一权威手册，原地更新）
- `v3-output/WT654-B03/REPORT.md`（本文件）+ `changes.patch`（`git diff --binary main...HEAD`，commit 后生成）
