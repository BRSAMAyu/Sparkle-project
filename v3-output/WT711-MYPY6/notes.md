# WT711 · mypy 棘轮烧减批六 notes

分支：`agent/node-b/wt711/mypy6`（main @ dc740d50 起 worktree）
口径：`cd backend && ./.venv/bin/python -m mypy app --ignore-missing-imports`（app/gen 在场，自主仓 proto-gen 产物同步拷贝）。

## 基线漂移（如实记）

- 任务书口径：合并态基线 **158 错**（批五 wt691 d95c0192 收于 159，口径差 1 属收尾降基线流程差）。
- 本卡实测（main HEAD dc740d50 新开 worktree）：**159 错 / 129 文件**。
- 漂移 = +1（159 vs 任务书 158），本卡不改 quality/mypy_baseline.txt（随收尾流程另行降基线，沿批五判例）。

## 簇选择（2 簇，单卡不贪多）

1. **Sequence/Row 方差与 SQLAlchemy 结果类型簇 ×12**：`Sequence` 协变面误声明为 `list`、`Result.all()` 返回 `Row[T]` 直灌 tuple 位、dict 值型不变。全部注解层债务，零运行时语义变化。
2. **blend_sector_colors 3 元组窄化簇 ×2**（node_sector_service）：生成器 `tuple(...)` 产出 `tuple[int, ...]` 直灌 `tuple[int, int, int]` 形参。真窄化修复，值与序完全不变。

## 逐处修法分类（注解=纯声明修正｜窄化=类型面收窄·零行为变化｜真 bug=0 处）

| # | 文件:行(修前) | 错误码 | 修法 | 说明 |
|---|---|---|---|---|
| 1 | app/services/task_document_service.py:40 | arg-type | 注解面（SQLAlchemy typing-only API） | `list(result.all())` → `list(result.tuples().all())`；`TupleResult` 官方注释明言「typing only class, Row acts like a tuple in every way already」，运行时同一对象 |
| 2 | app/services/task_document_service.py:163 | return-value | 窄化 | `ensure_focus_documents` 改先 `result = await db.execute(...)` 再 `existing = list(result.scalars().all())`；Sequence→list 显式物化，返回契约 `list[TaskDocument]` 保形 |
| 3 | app/services/exam_sprint_review_service.py:1125 | assignment | 注解 | `current_status_rows: list[UserNodeStatus]` → `Sequence[UserNodeStatus]`（体内仅迭代读取）；补 `collections.abc.Sequence` import |
| 4 | app/services/exam_sprint_review_service.py:1624 | arg-type | 注解面（同 #1） | `list(result.all())` → `list(result.tuples().all())` |
| 5 | app/services/focus_service.py:752 | arg-type | 注解面（同 #1） | `dict(task_result.all())` → `dict(task_result.tuples().all())` |
| 6 | app/services/simulation/participant_generator.py:126 | arg-type | 注解面（同 #1）+注解 | `.all()` → `.tuples().all()`；`_normalize_graph_candidates` 形参 `list[tuple[...]]` → `Sequence[tuple[...]]`（体内仅 for-unpack 迭代） |
| 7 | app/services/simulation/participant_generator.py:153 | arg-type | 同 #6 | fallback_rows 同款 |
| 8 | app/services/error_book_service.py:951 | arg-type | 注解 | `_attach_knowledge_links(records: list[ErrorRecord])` → `Sequence[ErrorRecord]`（逐 hunk 自审：体内对 `records` 只迭代、`insert` 作用于新建 `linked_ids` 非 `records` 本体，读侧宽化安全）；补 Sequence import |
| 9 | app/core/plan_context.py:368 | arg-type | 注解 | `_derive_insights_from_patterns(patterns: list)` 裸 `list` → `Sequence[BehaviorPattern]`（体内仅列表推导/`.count()` 只读）；TYPE_CHECKING 下补 `from app.models.cognitive import BehaviorPattern`（未来注解，零运行时 import 变化） |
| 10 | app/services/idiographic_association_service.py:224 | arg-type | 注解（mypy 官方建议向） | `correlate_dimensions(series_by_dim: dict[str, Sequence[float | None]])` → `Mapping[str, Sequence[float | None]]`；Mapping 值型协变，`dict[str, list[...]]` 调用方天然合法（同款判例：source_state_encoder note 指路），体内仅 `sorted`/`.values()`/`[dim]` 只读 |
| 11 | app/services/node_sector_service.py:213 | arg-type | 窄化 | 生成器 `tuple(int(channel / total) for channel in rgb_sum)` → 显式 3 元组 `(int(rgb_sum[0] / total), int(rgb_sum[1] / total), int(rgb_sum[2] / total))`；`rgb_sum` 恒为 3 元素列表，值/序逐项等价 |
| 12 | app/services/node_sector_service.py:214 | arg-type | 窄化（同 #11） | glow_sum 同款 |

**修法分类统计：注解 8 处（含 4 处 SQLAlchemy typing-only API 对齐）｜窄化 4 处｜真 bug 0 处｜cast/Any 糊弄 0 处｜新增 type: ignore 0 处。**

## 前后清单对照

- 修前清单：159 错（`mypy app --ignore-missing-imports`，清单存 wt711 会话 /tmp/wt711_mypy_base.txt，不入库）。
- 修后：**147 错 / 122 文件**。
- diff 核验：删除 13 行 = 烧减 12 错 + 1 行号平移（exam_sprint_review_service 787→788，系新增 import 行所致同一错误移位，非烧减）；**新增 0 错**。
- 净烧减：**159 → 147（-12）**。

## 验证

- mypy：147（<158 棘轮目标达成，且相对实测基线 159 严格下降）。
- 受影响模块测试（路径先 find 后跑，SECRET_KEY 沿 scripts/run_all_rule_guards.sh 同款合成测试键；worktree 无 .env，DBG 合规落 sqlite）：
  - 批一 `tests/unit/test_rolling_correlator.py tests/core/test_plan_context.py tests/services/test_error_book_service.py tests/unit/test_node_sector_backfill_dedup.py tests/test_api/test_task_document_api.py tests/unit/test_exam_sprint_review_service.py tests/services/test_exam_sprint_dashboard_service.py tests/unit/test_focus_service_memory.py` → **56 passed**
  - 批二 `tests/unit/test_idiographic_daily_vector_local_day.py tests/unit/test_idiographic_kill_switch.py tests/services/test_simulation_runner.py tests/unit/test_focus_heatmap_service.py tests/unit/test_prompt_plan_context.py tests/test_api/test_error_book_api.py` → **12+3 passed**
  - 重构后复跑 `test_task_document_api + test_node_sector_backfill_dedup` → **9 passed**；合计触达面全绿，零失败。
- ruff：8 触达文件 `ruff check` **All checks passed**；触达 hunk 逐块 black(120) 复核清洁（`ruff format --check` 所报 6 文件整文件漂移经 HEAD 对照实证为**既有**，不夹带整文件重排）。

## 台账

- 未新开 FIX 行（本卡零真 bug，V3-FIX-413/414 不占）；完整前后对照以本 notes 为卷宗。
- `python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md` → **verify 通过：296 行 V3-FIX 行，8 裸管形态合法，ID 无重号，状态枚举合法，零 FAIL**。
