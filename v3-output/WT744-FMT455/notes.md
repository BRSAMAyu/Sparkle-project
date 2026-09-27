# WT744 — V3-FIX-455 fusion_engine.py ruff format 既有漂移收口（P4 微卡）

- 分支：`agent/node-b/wt744/fmt455`（base = main@be7c5fcf）
- 修复 commit：`93f9ea6a`（仅 `backend/app/services/evidence/fusion_engine.py`，+9/−4）；台账/本 notes 为后续 docs commit
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt744-fmt455`（`backend/app/gen` 按先例主仓 `cp -RL`，不入库；`.venv/bin/python` 按主仓同形 symlink → `/opt/homebrew/bin/python3.11`，不入库）

## 修法（纯格式，不发明）

环境 ruff 0.15.8（`backend/requirements.txt` 仅钉 `ruff>=0.1.9` 未锁版，口径分叉见 455 行面）对 fusion_engine.py `ruff format --diff` 输出恰为 455 行面登记的 4 hunks，逐 hunk 同型；`ruff format` 单文件收口：

1. **:157 幂空格形**：`self.SAME_SOURCE_CONFIDENCE_DECAY ** group_index` → `self.SAME_SOURCE_CONFIDENCE_DECAY**group_index`（幂运算符空格收紧，AST 不变）
2. **:209 timestamp_bucket 三元未折行**：
   ```python
   # 修前
   timestamp_bucket = evidence.timestamp.replace(microsecond=0).isoformat() if evidence.timestamp else "unknown_time"
   # 修后
   timestamp_bucket = (
       evidence.timestamp.replace(microsecond=0).isoformat() if evidence.timestamp else "unknown_time"
   )
   ```
3. **:386 mode_stability_reason 三元未折行**：`"mode_stability_reason": mode_stability.get("reason") or router_snapshot_payload.get("mode_stability_reason"),` → `or` 右支按悬挂缩进折行（字典值内换行，AST 不变）
4. **:664 outcome_strength 三元未折行**：
   ```python
   # 修前
   trace["outcome_strength"] = "weak_heuristic" if is_weak_heuristic else trace.get("outcome_strength", "strong")
   # 修后
   trace["outcome_strength"] = (
       "weak_heuristic" if is_weak_heuristic else trace.get("outcome_strength", "strong")
   )
   ```

全文 `git diff` 仅上述 4 处（4 hunks，+9/−4），零语义：改形只涉幂运算符空格与括号折行/悬挂缩进，不改任何 token 序、字符串字面量与求值序。

## 邻域盘点（只列不扩面修）

`ruff format --check app/services/evidence/`（fusion 邻域 7 文件）：修后余 6 文件仅 **outcome_evidence_adapter.py** 1 文件 Would reformat——1 hunk：:54-55 `route_history_decision_id`/`routing_outcome_signal_id` 两行 `or` 链式取值超 120 列口径未折行。同漂移族（同源未锁版口径分叉），本批未触达，登记为 **V3-FIX-471**（预分配号 471 grep 全台账 0 命中、472 备用未占用，在册最高 461）。

背景口径（不占号不扩面）：`ruff format --check app/` 全仓 870 文件 Would reformat / 483 已格式化，系 FIX-286 行已披露的「全仓口径漂移为基线既有」同一事实，整体消分叉属工具链治理（锁 ruff 版本或专项 sweep），不在 455/471 行面。

## 测试面（find 先行，全绿零回退）

find 先行圈定 fusion/belief/contract/claim/adapter 7 文件，一次跑绿：

- `tests/unit/test_belief_fusion_engine.py` + `tests/unit/test_belief_observation_models.py` + `tests/unit/test_belief_trace_inspector.py` + `tests/unit/test_belief_recovery_simulator.py` + `tests/contract/test_event_registry_contract.py`（wt736 61 绿面）+ `tests/unit/test_fusion_engine_cross_process_claim.py`（wt736 新测试 4 例）+ `tests/unit/test_outcome_evidence_adapter.py`（471 漂移文件自身 3 例）
- **合计 68 passed in 1.20s，零 fail/error/skip**
- 运行形态：隔离 worktree 无 `.env`（防 demo 库 TEST-DBGUARD 拒连），env 注入安全占位 `SECRET_KEY`（32+ 字符非默认值）+ `DATABASE_URL=sqlite+aiosqlite://`；测试落 sqlite 面（conftest `TEST_DATABASE_URL` 内存 sqlite），凭据不入库

## 门禁

- **ruff check**：触达文件 `fusion_engine.py` All checks passed
- **ruff format**：触达文件 `1 file already formatted`（--check 净）
- **mypy 不回涨**：干净缓存全量 `mypy app`（cache-dir 置 /tmp 不入仓）——分支 **133** = 基线 be7c5fcf **133**（同环境同命令），逐行 error 集 **diff 为空**（基线经 stash 对照实测：stash 后跑基线、pop 后跑分支，同 worktree 同工具链）；`fusion_engine.py`/`outcome_evidence_adapter.py` 均 0 error。任务口径「132」与基线实测 133 差 1 系缓存/环境抖动（wt736 同款披露），以「与基线逐行 diff 为空」为准零回涨

## 披露（不隐藏）

1. **主仓 main tip 在本批运行期间前进**：开工时 base=be7c5fcf，期间 wt738 的 V3-FIX-426/428（含 `rate_limiting.py` 改动）落 main（c4f4d59f）。若拿现 main tip 当基线会看到 `rate_limiting.py:76→:128` 一条 mypy 行号漂移——该漂移属 wt738 已落改动，与本批无关；故回涨判据取我分支真实 base be7c5fcf 的 stash 对照（逐行 diff 为空）。集成合并时 471 行与 447/449/461 行追加区按行合并即可（455 行就地改 Status 格）
2. **ruff 未锁版口径分叉本卡未动**：455 行面修复方向二选一中的「requirements 锁 ruff 版本」属工具链治理另议，本卡只按「独立质量批统一 ruff format 该文件」方向收口 fusion_engine.py 单文件
3. **真 redis 面**：wt736 的 `test_belief_shadow_real_redis`（环境门 `SPARKLE_RUN_REAL_REDIS_TESTS=1`）本批未跑——纯格式批不触行为，测试面以 fusion 单测+契约+claim+adapter 68 绿为准

## 台账

- `v3/06_agent_fleet/DYNAMIC_ISSUES.md`：V3-FIX-455 → `OPEN；FIXED@93f9ea6a`（Status 格内追加，OPEN 历文保留，含修法/验证/披露摘要）；新增 V3-FIX-471（P4，OPEN，outcome_evidence_adapter.py 1 hunk 同族漂移）
- `scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md`：**verify 通过，零 FAIL**（工具口径 321 行 V3-FIX 行、裸管分布 {8: 321} 全形、ID 无重号、状态枚举合法；grep 行首口径 319→320，本批净增 1 行=471）
