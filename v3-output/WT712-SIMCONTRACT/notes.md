# WT712-SIMCONTRACT · SimulationEngine db=None 流式契约收口笔记（2026-09-27）

- 分支：`agent/node-b/wt712/simcontract`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt712-simcontract`，base = main tip 4b5b351f）
- 修复 commit：`b2c1f22a`；台账 commit：`V3-FIX-415` 登记 FIXED@b2c1f22a（台账行随本目录同批入库）
- 任务来源：wt670 执行中暴露并留档的 SimulationEngine db=None 流式契约问题（补位卡，预占号 415/415 取用、416 仍备用）

## 1. wt670 留档出处考证（先证后动，如实记录）

**台账无独立登记行**。全仓 grep 证据：

- `v3/06_agent_fleet/DYNAMIC_ISSUES.md`：`grep 'wt670\|WT670'` 与 `grep 'SimulationEngine\|simulation_engine\|db=None'` 均 **0 命中**（fix 前基线）。
- `v3-output/`：无 WT670 目录（ls 实证；wt670 的 worktree 亦已移除，`git worktree list` 实证）。
- 唯一留档痕迹两处：
  1. `v3/.sparkle_v3_fleet_state.json:776`（主会话轮 #205）：「……补位 wt712=wt670 留档 SimulationEngine db=None 流式契约（预占 415/416）。」
  2. wt670 唯一触及本文件的存活 commit `87e3cf24`（mypy 棘轮批三 266→226），对 `simulation_engine.py` 的改动恰是**行为上下文 enrich 补 self.db 非空卫**：`_stream_from_checkpoint` 内 `if user_id is not None:` → `if user_id is not None and self.db is not None:`（commit message 自述「行为上下文 enrich 补 self.db 非空卫（enrich 本为 try/except 尽力语义）」）。

**推断（如实标注为推断）**：wt670 在为 mypy arg-type 处理 `PredictiveService(self.db)`（self.db 为 `AsyncSession | None`）时，被迫对「db=None 时流式行为」作出局部裁决（跳过 enrich），由此暴露整条 db=None 流式路径的契约并未钉死，留档为补位卡。原始复现细节无更多存档，本卡按代码事实重证（见 §2）。

## 2. 当前代码事实（fix 前基线，main 4b5b351f）

### 2.1 调用方普查（先 find 后动手）

| 构造点 | db 实参 | 性质 |
|---|---|---|
| `backend/app/api/v1/simulation.py:135/163/203/223/242`（5 个端点） | `Depends(get_db)` 真会话 | 生产 |
| `backend/app/tools/simulation_tool.py:53`（QuickSimulationTool） | `db_session` 真会话 | 生产 |
| `backend/tests/unit/test_theater_seed_and_accuracy.py:303/361/398/1559` | `SimulationEngine(db=None)` | 测试（含唯一的全链 stream/continue_stream 测试，user_id=None） |
| `backend/tests/unit/test_mirofish_wiring_finish.py:394/450/486/516` | `SimulationEngine()` 默认 None | 测试（单元碎片级） |

→ 生产恒传真 db；db=None 只在测试在场，且已有多处直接依赖（8 处构造点）。

### 2.2 self.db 全部解引用点与守卫现状（fix 前 7 处）

| 行（fix 前） | 方法 | 守卫 |
|---|---|---|
| :269/:569 | `generate_participants(db=self.db)`（preview/stream） | 生成器内部 :30 `and db and` 守卫（db None 跳过知识图谱路径） |
| :391 | `_resolve_anchor_context` | `self.db is None or user_id is None or 空 topic` → no_anchor 诚实回退 |
| :429 | `_find_related_error_anchors` | `not topic_lower or self.db is None` → `[]`（wt340 批五补，注释自称「既有守卫口径」） |
| :483 | `_find_related_concept_anchors` | 同上 |
| :707 | `_stream_from_checkpoint` 行为上下文 enrich | `user_id is not None and self.db is not None`（**wt670 87e3cf24 所补**，即本卡留档起点） |
| :1526 | `_get_user_mastery_gaps` | `self.db is None` → `[]`（wt340） |
| :1675/:1700 | `_persist_checkpoint_to_db` / `_load_checkpoint_from_db` | `user_id is None or self.db is None` → 不持久化/None（wt340） |

**结论**：db=None 时「读 DB/写 DB」分支守卫完备（wt340+wt670 已封）；**未钉死的是两处非直读 DB 的契约洞**（§2.3），及全部守卫行为零测试锁（现有测试只覆盖 user_id=None 纯内存态碎片）。

### 2.3 两处实测契约洞（探针真实运行，非推测）

洞 ①（混合态幽灵信号，「或反之」向）：`SimulationEngine(db=None)` + `stream(user_id=<uuid>)` 跑到完成——完成路径 `if user_id is not None:` 无 db 检查，`_persist_simulation_insights`（事件总线）与 `_persist_session_update`（SystemUpdateService.enqueue）**照发**；而同态 `_persist_checkpoint_to_db` 拒绝持久化、完成路径本就无任何 DB 写。实测输出：

```
EVENTS: ['status', 'participants', 'round', 'insight', 'round', 'insight', 'complete']
publish.await_count = 1        # SimulationGapRevealed 幽灵事件
enqueue.await_count = 1        # 「学习仿真已完成」系统更新
```

后果：运行零持久落盘（仅进程内 local checkpoint + 6h TTL cache），重启后会话 404，而用户已收到「仿真已完成/暴露盲区」的持久性通知与事件——下游信号引用一个不存在的会话。

洞 ②（完成路径 cache 清理裸调）：`cache_service.delete` 是完成路径唯一未包裹的基础设施调用（同路径 `_load_checkpoint` 的 get、`_persist_checkpoint` 的 set 均 try/except best-effort）。monkeypatch delete 抛错的实测输出：

```
STREAM RAISED: RuntimeError redis connection lost
EVENTS BEFORE CRASH: ['status', 'participants', 'round', 'insight', 'round', 'insight']
```

后果：全部轮次已生成、流在 `complete` 事件前崩掉——调用方（SSE 端点）只收到 error，已产出的轮次全部丢弃。

## 3. 裁决（两态都写明）

**裁决：db=None 是合法形态——纯内存模拟、诚实降级。** 依据（仓内口径优先）：

1. **既成守卫体系**：fix 前 7 处 self.db 解引用点全部带 db 缺席守卫，其中 4 处注释自称「既有守卫口径」——仓内既成事实把 db=None 当一等形态对待（诚实回退，非报错）。
2. **调用方证据**：8 处测试直接用法依赖 db=None（纯内存模拟是测试与 `preview` 轻量路径的真实能力）；生产 6 处构造点恒传真 db，显式拒绝不影响生产但会破坏既有能力。
3. **公共签名既成**：`def __init__(self, db: AsyncSession | None = None)` 是既成公共契约，改为必填属破坏性签名变更，超出本卡问题定价。

**被否决的替代态——非法（显式拒绝）**：构造时或流式入口 fail-loud。否决理由：破坏 2.1 表 8 处既有用法与纯内存能力；`_load_checkpoint` 混合态（db=None+user_id，本地 checkpoint 命中）是既有测试锁定的合法行为（`test_simulation_engine_load_checkpoint_falls_back_to_local_storage`）；且「拒绝」并不能自动给出生产行为改善（生产不走该形态），只有迁移成本。混合态的**子面**（不可持久化的运行不得发持久性信号）按 C2 收口，属契约钉死而非形态拒绝。

钉死后的契约三态：

- **C1 纯内存态**（db=None + user_id=None）：流式全链诚实完成，锚点回退 `no_anchor`，不因外部设施缺席崩溃。
- **C2 混合态**（db=None + user_id≠None）：运行不可持久化（与 `_persist_checkpoint_to_db` 同口径），完成路径**不得**发出持久性下游信号（SimulationGapRevealed / simulation_session_ready 系统更新）；运行本体仍诚实完成（COMPLETED 事件照常 yield）。
- **C3 基础设施尽力语义**：完成路径 cache 清理与同路径 get/set 同为 best-effort，Redis 抖动不得打断 complete 事件。

## 4. 修复 diff（commit b2c1f22a，2 文件 +187/−2）

| 文件 | 改动 |
|---|---|
| `backend/app/services/simulation/simulation_engine.py` | ① 完成路径 `if user_id is not None:` → `if user_id is not None and self.db is not None:`（C2 调用点卫语句，带注释锚 V3-FIX-415；`_persist_simulation_insights`/`_persist_session_update` 私有方法本体**不动**——`test_simulation_engine_persists_gap_events` 等既有直接调用单测零影响）；② `cache_service.delete` 包 try/except + `logger.warning`（C3，与 `_load_checkpoint`/`_persist_checkpoint` 内 get/set 口径对齐） |
| `backend/tests/unit/test_simulation_engine_db_none_stream_contract.py` | 新增 4 测（见 §5）：C1 钉子、C2 红→绿、C3 红→绿、db=None continue 未知会话 404 语义钉子 |

产品语义迁移为零：生产路径（db 恒真）行为逐位不变；改动的只是生产不可达的混合态与故障态语义。

## 5. 红→绿实录

修前（真实输出，`pytest tests/unit/test_simulation_engine_db_none_stream_contract.py`）：

```
test_db_none_stream_pure_memory_completes_with_honest_anchor PASSED [ 25%]   # 规格钉（修前即绿）
test_db_none_stream_with_user_id_does_not_emit_durable_signals FAILED [ 50%]
    assert publish.await_count == 0, "db=None 运行不可持久化，不得发布 SimulationGapRevealed 幽灵事件"
E   AssertionError: db=None 运行不可持久化，不得发布 SimulationGapRevealed 幽灵事件
E   assert 1 == 0
test_db_none_stream_survives_cache_cleanup_failure FAILED [ 75%]
E   RuntimeError: redis connection lost
test_db_none_continue_stream_unknown_session_raises_value_error PASSED [100%]  # 规格钉（修前即绿）
========================= 2 failed, 2 passed in 0.56s ==========================
```

修后：

```
test_db_none_stream_pure_memory_completes_with_honest_anchor PASSED [ 25%]
test_db_none_stream_with_user_id_does_not_emit_durable_signals PASSED [ 50%]
test_db_none_stream_survives_cache_cleanup_failure PASSED [ 75%]
test_db_none_continue_stream_unknown_session_raises_value_error PASSED [100%]
============================== 4 passed in 0.47s ===============================
```

## 6. 验证汇总（真实运行）

| 门 | 结果 |
|---|---|
| 新契约测试 | 修前 2 红 + 2 规格钉绿 → 修后 **4/4 绿**（0.47s） |
| 既有 simulation 测试 | `test_theater_seed_and_accuracy.py` + `test_mirofish_wiring_finish.py` + `test_stage38_d3_persistence.py` = **85 passed**（44s，零回退） |
| 既有 journey 测试 | `test_a06_gj08_calibration_journey` / `test_j05_stuck_journey_migration_sqlite` / `test_j06_hybrid_journey` / `test_j06_hybrid_journey_migration_sqlite` / `test_stage33_journey_events` / `test_stage35_journey_smoke_helpers` = **37 passed**（41s，零回退） |
| mypy | `mypy app`（本地 venv mypy 1.20.2，带 gen 口径）修前 **159** errors / 修后 **159** errors——`git stash` 对照实证**零漂移**；触达文件 simulation_engine 在输出中 **0 错**。注：本机基线 159 与任务书集成态数字 158 差 1，系环境既有差异（stash 对照已证非本卡引入），如实披露 |
| ruff | 触达 2 文件 `All checks passed!`（test 文件 1 处 I001 import 排序已 --fix） |
| black | 新增行零 flag；engine 文件 black --diff 的 5 个 hunk（@@288/@@450/@@1126/@@1427/@@1796）全部位于 base 既有漂移区（本卡 hunk 在 @@853 邻域），按先例不碰 |
| 台账 | `python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md` → **verify 通过（exit 0）**：297 行 V3-FIX 行、裸管分布 {8: 297}、ID 无重号、状态枚举合法、零冲突标记 |

## 7. 测试环境与铁律遵守声明

- 测试进程环境：worktree 内**不放 .env**（TEST-DBGUARD 拒演示库；按其指引隔离 worktree 运行），pytest 以 `SECRET_KEY=<测试专用串> DATABASE_URL=sqlite+aiosqlite://` 内联注入；`backend/app/gen` 按先例 `cp -RL` 自主仓供本地运行，**不入库**（gitignore 实证）。
- 无 Mock 冒充：红测走真实 `stream()` 全链（LLM 依赖 monkeypatch 钉住、侧效应用 AsyncMock 计数），两处洞另有未 monkeypatch 的裸探针实测（§2.3 输出即裸跑结果）。
- 不 push；全部 commit 在 `agent/node-b/wt712/simcontract`。
