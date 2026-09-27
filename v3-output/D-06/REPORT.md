# D-06 · WVPL 北极星查询与事实 JSON — 独立复验与证据包（wt653）

- **base SHA**: `af936c03`（main @ 2026-09-25 开工时）
- **工位**: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt653-d06`（分支 `agent/node-b/wt653/d06`）
- **日期**: 2026-09-25 ｜ 性质：**复验+证据补全**，零生产代码改动
- **实现已在库**（本会话前合入，非本轮产出）：
  - `c90641c0` feat(D-06)：core 契约 `app/core/north_star_wvpl.py`（frozen schema `north_star.wvpl.fact.v1` + 口径 `wvpl.caliber.v1`）+ `app/services/north_star_wvpl_service.py`（确定性 SQL 聚合，零 LLM）+ golden 冻结（R2 PASS）
  - `0484727b` wt352：`GET /api/v1/admin/north-star/wvpl-fact` 只读暴露端点（superuser，handler 零后处理直通服务）
  - `4fab591d` wt609/V3-FIX-319：focus.end_time 跨钟同钟修复（±8h 错桶）
- **本会话发现的证据债（已闭）**：`backend/tests/golden/test_north_star_wvpl_golden.py` docstring 声称变异证据「见 v3-output/D-06/REPORT.md」，但 `c90641c0` 提交清单**不含任何 v3-output 文件**，该路径在全仓不存在——承诺证据未入库（wt306/wt313 同族交付物未 commit 事故的静默形态）。本报告以**当前集成 HEAD 的全新实跑复验**补齐，所有数字为本次实跑产出，非转抄历史声明。

## 一、卡面验收逐条对照

### 验收 1 ｜ 固定 fixture 得到确定结果；边界（跨周/重复 event/撤销 outcome）测试 —— **完成（测试级）**

| 面 | 证据（`backend/tests/`） | 结果 |
|---|---|---|
| 固定 fixture 确定结果 | `golden/north_star_wvpl_fixture.py`（全实体 id 冻结 `_fid(n)`）+ `test_north_star_wvpl_golden.py`（sha256 `f5ced526…` 钉死 + canonical JSON 逐字节比对） | 3 passed |
| 逐数字断言 | `test_fixed_fixture_deterministic_numbers`（分母 3/分子 1/ratio 0.3333/loops 2/by_source 五源/truth_coverage 4=3+1/conversion 1.0/cohort 分离） | passed |
| 跨周（半开窗口） | `test_cross_week_half_open_boundary`（起点含/终点=as_of 不含）+ `test_as_of_anchor_moves_window_membership`（as_of 锚点移动窗口成员） | passed |
| 重复 event | `test_duplicate_events_and_reruns_never_double_count`（多条回声+复跑逐字节一致，loop 身份=`(task_completion, task_id)`） | passed |
| 撤销 outcome | `test_revoked_outcome_drops_loop`（文件证据 revoked → actual 回落 self_reported → loop 消失，查询时诚实重算） | passed |
| 空态不伪造 | `test_empty_db_no_fabricated_numbers` + API `test_wvpl_fact_empty_db_honest_state`（分母 0 → 比率 None） | passed |
| 零模型参与 | `test_query_layer_has_zero_llm_participation`（源码 pin 禁词表） | passed |

### 验收 2 ｜ 可在 staging 真实跑并追溯 event IDs —— **静态面完成，运行级待验（见 §四）**

- 暴露面在码：`app/api/v1/north_star_wvpl.py`（superuser 依赖，router.py:85,258 挂载；网关 `/api/v1/admin` catch-all 代理自动透传+引擎侧二次校验，分层不破）。
- 事件可溯在码：事实 JSON `loops.samples[]` 每条携带 `outcome_id`（D-02 `derive_outcome_id` 幂等 id，`outc_` 前缀）+ `source_ref=task://<id>` + `task_id/plan_id/goal_id/occurred_at/evidence_kinds`；API 测试第三例逐字段比对服务产出。
- **staging 真实跑未执行**：本地栈当前为旧二进制（明日升栈），按派单纪律不以旧栈运行冒充 staging 证据、不伪造运行输出。

## 二、本轮实跑验证结果（全部 `DATABASE_URL='sqlite+aiosqlite:///:memory:' SECRET_KEY=v`，主仓 venv）

| 批次 | 路径 | 结果 |
|---|---|---|
| 卡核心 | `tests/services/test_north_star_wvpl_service.py` + `tests/unit/test_north_star_wvpl_api.py` + `tests/golden/test_north_star_wvpl_golden.py` | **22 passed**（3 连跑稳定） |
| 消费面·X08 | `tests/services/test_x08_outcome_ledger_gj.py` + `tests/unit/test_x08_outcome_capture.py` | **19 passed**（4 处经 `build_fact` 交叉消费） |
| 消费面·O07 | `tests/unit/test_o07_budget_matrix_and_ux.py -k "wvpl or cost"` | **4 passed**（cost/WVPL gauge 快照+失败计数面） |
| 变异红绿 | 见 §三 | **4/4 红，复原后 41 passed** |
| OpenAPI 契约 | `scripts/export_openapi_snapshot.py` vs `docs/contracts/openapi_snapshot.json` | **899==899 路径，0 新增/0 消失漂移**；`/api/v1/admin/north-star/wvpl-fact` 已在快照（wt357 重冻结捕获），本卡零契约面变化 |
| ruff/mypy | 触达文件 = 本报告（纯 markdown），树内零代码改动 | N/A |

## 三、变异红绿复验（本会话重新产出，非转抄 c90641c0 声明）

对 `app/services/north_star_wvpl_service.py` 逐一施加单点变异→跑 golden+服务套件→`git checkout` 复原（sha256 校验 `695bf173…` 逐次通过）：

| 变异 | 内容 | 结果 |
|---|---|---|
| M1 | 丢弃 state update 腿（`window_loops = candidate_loops`） | **红**：golden 逐字节比对 + fixture 数字 + as_of 锚点 3 处失败 |
| M2 | 半开窗改闭区间（`< end` → `<= end`） | **红**：`test_cross_week_half_open_boundary` 抓获（2≠1）。golden 保持绿属预期——fixture 无恰在边界的事件，边界面由专测把守 |
| M3 | 分母剔除反转（`not_in(seed_subq)` → 恒真） | **红**：3 连跑均红（失败集 4–7 处浮动，含 golden+fixture+seed cohort 面） |
| M4 | 比率舍入放宽（4 位 → 2 位） | **红**：golden（0.3333→0.33）+ fixture 数字 2 处失败 |

M3 失败集浮动的根因（已查清，**非套件抖动**）：该变异使 `where()` 收到裸列，SQL 渲染成对 user_id 原始 UUID 串的 SQLite 布尔真值——固定 id 用户（`_fid`，十六进制前导 0）恒假，随机 uuid4 id 用户随首字符是否为非零数字而真值漂移。原套件无此问题：pristine 3 连跑 19 passed 全稳，`db_session` 为每测试独立 sqlite 内存引擎（conftest.py:273）。

## 四、运行级待验清单（交主会话，明晨升栈后补验；不伪造运行证据）

1. **staging/新栈真实跑**：superuser 凭据 `GET /api/v1/admin/north-star/wvpl-fact` → 200 + `schema=north_star.wvpl.fact.v1` + 真实非零数字（或诚实空态）。
2. **事件追溯闭环**：取响应 `loops.samples[]` 任一条 → 以其 `task_id` 回查 tasks/study_records 行、以 `outcome_id` 复算 `derive_outcome_id` 一致、`goal_id` 经 plans.goal_id 可回溯——三步各留一帧证据。
3. **JOURNEY NS001 消费面**（明日 day7 终门）：northstar_jrn 用户窗内真实 loop 应出现在事实 JSON（真实驱动 → 北极星链路的端到端证明）；同时确认 `provenance.truncated=false`。
4. **cost/WVPL worker**：celery beat `refresh_cost_wvpl_metrics` 单次真实执行日志 `cost_wvpl refreshed`，`COST_WVPL_REFRESH_FAILURES_TOTAL{stage="wvpl_fact"}` 不增。

## 五、裁决与注记

- **卡面 path seeds vs 实际位置**：卡面种子写 `backend/app/services/analytics` + `backend/app/api`；实际实现落位 `app/core/north_star_wvpl.py`（契约）+ `app/services/north_star_wvpl_service.py`（服务，不在 `services/analytics/` 下）+ `app/api/v1/north_star_wvpl.py`。按派单纪律亲证消费面后按实际代码裁决：落位合理（查询层非周期统计批处理），不迁移。
- **V3-10 门「是否由 proactive intervention 启动」**：v1 事实 JSON 以独立面（`proactive.lifecycle_events_by_type` / `started_by_execution_mode`）报告，未做 loop↔intervention 逐条归因 join（需 D-05 lifecycle→task 关联，v1 limitations 未宣称）。若评审按逐 loop 归因解读该条，属后续增口径（需 bump caliber version 走重冻结流程），本卡不动。
- **`app/services/north_star_metrics_service.py` 是另一物**：用户级 exam/goal 产品趋势（`/api/v1/analytics/north-star/trends`），与 D-06 WVPL 事实 JSON 无消费关系，勿混认。
- **D-02 翻页语义已亲证**：`outcome_ledger_service.py` 五源查询均 `order_by(occurred.desc(), <id>.desc())`——有界 walk「最新优先」声明与代码一致。
- **Forbidden 遵守**：未重建真源（服务只读消费 D-02/D-05/生产表公开面）；未引入 mock/seed 冒充（seed cohort 单列 demo face 有专测）；未弱化任何守卫（零代码改动）。
- 状态口径：worker 不自行 DONE。卡实现此前已 R2 PASS 合入；本轮为独立复验+证据补全，运行级验收留待 §四。
