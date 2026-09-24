# WT344-SKILLS-RED — skills 两测试存量红：定性+处置 报告

- **base SHA**: `9c9279d7`（main，含 wt343 批次）
- **工位**: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt344-skills-red`
- **触碰面**: 仅 2 个测试文件（+8/−0）：`backend/tests/unit/test_skills_api.py`、`backend/tests/unit/test_skill_share_service.py`。**零产品代码改动**；skill_share/skill_store/stage21 产品代码、mobile、gateway、galaxy/aurora/kill_switch 战区全部未触碰。

## 一、复现（逐字，开工未动一行先跑=存量实证）

`DATABASE_URL="sqlite+aiosqlite:///:memory:"`（backend/.venv python，worktree 无 .env，SECRET_KEY 走环境变量）跑两文件：**2 failed, 1 passed**，失败集与卡面完全一致：

| 测试 | 失败断言 | 实际 vs 期望 |
|---|---|---|
| test_skills_api.py::test_skills_api_crud_extract_and_share_flow | L91 `len(shared_list.items)==1` | `0 != 1`（share 返回 200 但 `shared_skill_id=None`，/skills/shared 目录空） |
| test_skill_share_service.py::test_skill_share_pipeline_publishes_and_withdraws | L45 `result["status"]=="approved"` | `'pending' != 'approved'` |

## 二、定性证据链 → (a) 测试装配错误（出生即带错装配，非产品缺陷/非过时/非环境错位）

1. **失败机制（唯一根因）**：`submit_share_request` 仅在 `share_mode == "live" and settings.SPARKLE_SKILL_SHARE_MOCK_REVIEW_ENABLED` 时走 mock 自动过审并发布（skill_share/service.py:73）。该 flag 默认 **False**（settings.py:960），故默认产物语义=入人工审核队列，返回 `pending`/`shared_skill_id=None`——两测试的失败点全部由此一条链导出（API 测试 L86 的 200 断言过、L87 拿到 None、L91 目录空）。
2. **测试补丁打错了旋钮（smoking gun）**：两测试 monkeypatch 的是 `SPARKLE_SKILL_SHARE_ENABLED=True`——stage21 kill_switch 绑定里的 legacy 布尔（aurora_stage21_kill_switch_service.py BINDINGS），而它**默认本来就是 True**（settings.py:959）=空操作；真正卡发布的 `SPARKLE_SKILL_SHARE_MOCK_REVIEW_ENABLED` 全仓测试无一人补丁（grep 仅 settings.py 定义 + service.py:73 消费）。tri-state 模式门也不缺：`AURORA_STAGE21_SKILL_SHARE_MODE` 默认 `"live"`（settings.py:326），redis=None 时 read_mode 回落 settings 即得 live。
3. **出生即红、从未绿过**：两个测试文件与 service、flag 定义同在 clean-slate 初始 commit `1722e6dc`（2026-09-15）落地（`git log --diff-filter=A` 四文件同源单 commit），此后两测试文件零改动——不存在"合法演进而测试没跟上"，是**出生装配即错**。
4. **排除 (c) 产品真缺陷**：pending-by-default 是有意的安全设计——UGC 匿名分享默认进人工审核队列（enqueue_for_moderation 无条件入队，review_and_publish 是独立审核动作），`MOCK_REVIEW_ENABLED` 按名即是 dev/test 环境免人审的 mock 通道，生产默认 False 正确；若为迁就测试把发布改成无条件反而是产品缺陷。
5. **排除 (d) 环境错位**：失败与环境无关——本地 sqlite 与 CI（PG+Redis service）同态：CI env 不设该 flag（ci.yml 逐行核过），且 pytest 不起 lifespan→`cache_service.redis=None`（init_redis 仅 lifespan/celery 调用，wt341 已核全部测试赋值 try/finally 恢复 None），kill switch 读路径两环境同走 settings 默认。
6. **对照实验（单一变量闭环）**：仅以 env `SPARKLE_SKILL_SHARE_MOCK_REVIEW_ENABLED=true` 复跑 → **3/3 绿**，证明该门是唯一根因、门后无其他潜伏破坏；反向变异实验（把 service.py:73 条件短路为 False）→ 两测试**即红**，证明修复后断言保护力完整（发布→目录→fork→撤回全链路仍被真实拦截），非为绿而绿。

## 三、CI 行为判定：**会红（一旦真跑到）；从未观测=恰好从未跑到**（卡面"早于 51% 取消点"假设被证据推翻）

| 入口 | 判定 | 依据 |
|---|---|---|
| ci.yml `backend-test`（push 触发） | **必红** | 环境同定性 §二-5（redis=None、flag 缺省 False、mode=live）→ 与本地同失败集。**但从未执行到**：决胜 run 36015155771（commit 1c5f2d8d）job 107708947681 日志经 gh 全文拉取核验——6084 条结果 **0 FAILED**，于 51% 取消，最后执行测试=`tests/unit/test_conflict_resolver_categories.py::test_f7_epistemic_guard_skip_is_metric_counted`；本仓 12334 项全量收集序中该测试位于第 6329 位（**51.3%**，与日志 `[ 51%]` 互证），而 test_skill_share_service/test_skills_api 位于第 11026/11030 位（**≈89.4%**）——**在取消点之后 38 个百分点**。此前所有 run 要么更早被 concurrency cancel-in-progress 取消（舰队 run 中推批），要么 3-5 分钟内在前置 job 即失败，无一到达。交接文档"Backend Tests 是最后一关"（两次取消后冻结）即 systemic 原因 |
| ci-pr.yml `python-checks`（PR 触发） | **从未运行** | `gh run list --workflow ci-pr.yml` 全史为空——舰队直推 main 不开 PR，该入口一次都没跑过；即便跑，`-x` 也会在首个 unit 失败（wt338/341/343 清尾后即为 test_skill_share_service）处中止变红 |

两测试文件本身无任何 skip 门/模块级钥匙（逐行核过）——卡面三假设（skip 门/钥匙/没跑到）中成立的是**恰好从未跑到**。

## 四、处置（装配错误 → 修测试装配，非"为绿而绿"）

- 两文件各加一行 `monkeypatch.setattr("...settings.SPARKLE_SKILL_SHARE_MOCK_REVIEW_ENABLED", True)`（monkeypatch 逐测自动恢复，无状态泄漏），注释写明依据：该门是产物有意的 mock 过审通道、legacy 布尔补丁为何是空操作但保留（mode 默认被改时仍经 `resolve_settings_mode` 兜底保证 live）。
- 断言零放宽：`approved`/`shared_skill_id`/目录条数/fork/withdraw 全部原样保留（见 §二-6 变异验证）。
- **不修产品的理由**：pending 默认=人工审核安全默认（§二-4），改产品即违反定调令。

## 五、回归与顺藤排查

- 两目标文件：**3 passed**（含存绿 rejects_pii 不回归）。
- skills 相邻批（`find tests -name '*skill*'` 全部 8 个真实路径文件，含 spine/test_skill_lifecycle.py）：**86 passed, 0 failed**。
- 同族扩展扫描（grep 全 tests 引用 submit_share_request/SPARKLE_SKILL_SHARE 的其余两文件 test_memory_admin_api.py + test_stage21_kill_switch.py）：**11 passed**。
- **顺藤结论：零新增存量红**——skills 全家族（含 API/service/schema/extract/selection/store/lifecycle/admin/stage21）在本批后全绿，无 wt343 式清尾新暴露项，时间盒未动用。

## 六、收工门

| 门 | 结果 |
|---|---|
| `bash scripts/run_all_rule_guards.sh` | **EXIT 0**（83 条；gen 三件套已 cp -RL：backend/app/gen、gateway/gen、mobile/lib/gen） |
| 冷 mypy（`rm -rf .mypy_cache && mypy app --ignore-missing-imports --no-error-summary \| grep -c 'error:'`） | **1278 = 棘轮基线 quality/mypy_baseline.txt，零漂移**（零产品代码改动） |
| ruff（被碰 2 文件） | **0**；black(120) clean（新产行格式化，存量零触碰） |
| 环境纪律 | 全程 sqlite-only 内存库；未连本地 sparkle_db/PG/Redis；禁用模拟器/Gradle/flutter/浏览器 |

## 七、/tmp 自产清理

删除：/tmp/wt344_backend_tests_run36015155771.log、/tmp/wt344_collect_full.txt、/tmp/wt344_collect_flat.txt、/tmp/wt344_c1.txt、/tmp/wt344_c1err.txt、/tmp/wt344_c2.txt、/tmp/wt344_guards.log、/tmp/wt344_mypy_cold.txt。
