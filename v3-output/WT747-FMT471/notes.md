# WT747 — V3-FIX-471 outcome_evidence_adapter.py ruff format 既有漂移收口（P4 微卡）

- 分支：`agent/node-b/wt747/fmt471`（base = main@62e75576，含 455 已修，未用旧基线）
- 修复 commit：`bbddaea5`（仅 `backend/app/services/evidence/outcome_evidence_adapter.py`，+4/−2）；台账/本 notes 为后续 docs commit
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt747-fmt471`（`gen/`/`.venv` 未建未入库——纯格式批单测经主仓 venv python + `PYTHONPATH` 指向本 worktree 运行，导入路径实证加载本 worktree 副本，见下）

## 修法（纯格式，不发明）

环境 ruff 0.15.8（`backend/requirements.txt` 仅钉 `ruff>=0.1.9` 未锁版，口径分叉同 455 行面披露）对 outcome_evidence_adapter.py 先 `ruff format --diff` 取证（输出恰为 471 行面登记的 1 hunk）再 `ruff format` 单文件收口：

- **:54-55 两 `or` 链未按 120 列折行**：
  ```python
  # 修前
  "route_history_decision_id": event.get("route_history_decision_id") or metadata.get("route_history_decision_id"),
  "routing_outcome_signal_id": event.get("routing_outcome_signal_id") or metadata.get("routing_outcome_signal_id"),
  # 修后（各拆为括号内两行，or 右支悬挂缩进）
  "route_history_decision_id": event.get("route_history_decision_id")
  or metadata.get("route_history_decision_id"),
  "routing_outcome_signal_id": event.get("routing_outcome_signal_id")
  or metadata.get("routing_outcome_signal_id"),
  ```

全文 `git diff` 仅上述 1 hunk（@@ -51,8 +51,10 @@，+4/−2），零语义：只涉换行/悬挂缩进，不改任何 token 序、字符串字面量与求值序；`ast.dump(ast.parse(...))` 修前（`git show HEAD~1` 版本）修后**等价实证 True**。

## 测试面

- `DATABASE_URL='sqlite+aiosqlite:///:memory:' SECRET_KEY=v pytest tests/unit/test_outcome_evidence_adapter.py -q`：**3 passed in 0.55s**（按任务口径命令逐字执行；SECRET_KEY=1 字符仅触发启动日志 warning，不阻断测试）
- 导入路径核验：同 env 下 `import app.services.evidence.outcome_evidence_adapter` 的 `__file__` 解析为 `/Users/brsama/code/GitHub/Sparkle-sysrev/wt747-fmt471/backend/app/...`——测试实跑在本 worktree 代码，非主仓影子

## 门禁

- **ruff check**：触达文件 `outcome_evidence_adapter.py` All checks passed
- **ruff format**：触达文件 `1 file reformatted`，`--check` 复核 `1 file already formatted`
- **mypy**：本批未重跑（纯格式批；AST 修前修后等价实证 + 471 行面已有 wt744 实证该文件零 mypy error，语义面无变化通道）

## 邻域复扫

`ruff format --check app/services/evidence/`（fusion 邻域 7 文件）：**7 files already formatted，全净无新发现**——预分配号 477/478 grep 复核全台账 0 命中、未占用（本批无新发现故不占号）。

## 台账

- `v3/06_agent_fleet/DYNAMIC_ISSUES.md`：V3-FIX-471 → `OPEN；FIXED@bbddaea5`（Status 格内追加，OPEN 历文保留，含修法/验证/邻域摘要）
- `python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md`：**verify 通过，零 FAIL**（323 行 V3-FIX 行、裸管分布 {8: 323} 全形、ID 无重号、状态枚举合法）

## 披露（不隐藏）

1. **主仓 main tip 在本批运行期间前进**：开工时 base=62e75576（轮#234，含 455 已修，符合开工口径），期间轮#235 wt743 集成落 main（ef3cb03e，`gateway/internal/cqrs/worker/base.go`+台账+notes）。本批不 chase，不 rebase（先例 WT744 同款披露）；分支自身 diff 对真实 base 62e75576 恰 3 文件（adapter 修复/471 行 Status/本 notes），集成合并时 471 行与 wt743 的 461/469 行追加区按行合并即可
2. **ruff 未锁版口径分叉本卡未动**：471 行面修法方向二选一中的「requirements 锁 ruff 版本」属工具链治理另议，本卡按「独立质量批 `ruff format` 单文件收口」方向执行
3. **mypy 未重跑**：纯格式批 AST 等价实证（修前修后 `ast.dump` 一致），语义面无变化通道；471 行面已有 wt744 实证该文件零 mypy error
