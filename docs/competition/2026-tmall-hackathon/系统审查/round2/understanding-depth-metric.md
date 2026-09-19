# 理解深度量化基线（数据飞轮之四：understanding_depth 从"有字段无基线"到每日 0-1 可回归指标）

- 实现员：数据科学家工程师（sysrev wt7，数据飞轮专项之四——最后一块拼图）
- 工作树：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt7`（基线 8b17ca15，未 commit）
- 日期：2026-09-19
- 补丁：[understanding-depth-metric.patch](understanding-depth-metric.patch)（`git diff --cached` 产物；`backend/.env` 与 `backend/gateway/gen` 为 gitignored 软链/产物，未入补丁）
- 纪律执行：主库只读 —— 迁移**未**对主仓 PostgreSQL apply，改用**本地 sqlite 基座隔离重放**（§4.3）；独立端口验证未启动新服务（无状态验证不占端口）；未触碰主仓 `.env`
- 红绿协议：18 项新测试（单调性 9 + sqlite 落表 3 + 迁移重放 2 + API 4），red 实证 7 failed → green 20/20（含 2 项既有单头守卫）

---

## 0. 总览

| 挂账项 | 实测定性 | 本波交付 |
|---|---|---|
| understanding_depth **谁在算** | `self_evolution_service.UnderstandingDepthService.evaluate()`（:233）每次请求**现算** L0-L5 等级（§1.1） | 不动运行时链路；新增**每日离线**聚合 `UnderstandingDepthMetricService`，与运行时等级互补 |
| understanding_depth **存哪** | 纯 Redis（`understanding-depth:current/notified:*`，TTL 365d）+ `chat_messages.metadata` 内嵌 JSON 串；**等级历史零落库** | 新表 `understanding_depth_daily`（user_id+date 唯一，score Float + components JSONB），alembic `ud01_20260919` 挂当前唯一 head |
| understanding_depth **有没有被用** | 有：context_builder 注入 → prompts 4 个模板渲染 natural_hint → 升级推送 SystemUpdate（§1.2）——但**无基线、无趋势、无出口端点**，"越用越好用"不可见证 | GET `/api/v1/insights/understanding-depth`（近 7/30 天趋势）+ 网关代理（X-User-ID 注入纪律沿用 `SetProxyUserContextHeaders`）|
| **无回归验收** | 验收脚本止步于 mr4（9 项） | `acceptance_memory_revival.py` 增 UD-10：端点接线 + 二轮分 > 首轮基线（§5）|

指标设计要点：4 个可当日计算的分量（记忆注入量 / 个性化 run 占比 / 用户主动纠正率↓ / 重复提问率↓）线性加权合成为 0-1 分，**每维对"更懂用户"单调**并由单测钉死（§2）。

---

## 1. 现状盘点：understanding_depth 的生产写入与消费

### 1.1 谁在算、存哪

`backend/app/services/self_evolution_service.py:233` `UnderstandingDepthService.evaluate(user_id)` 返回 `UnderstandingDepthSnapshot(level, score, dimensions)`，等级判定：

| 等级 | 条件 | 数据源 |
|---|---|---|
| L1 | active_preferences ≥ 3 | `memory_preferences`（未删/未归档/未撤回 count） |
| L2 | active_patterns ≥ 2 | `behavior_patterns`（confidence≥0.7） |
| L3 | 近 3 次 alignment ≥ 0.7 | Redis `strategy-calibration:*` |
| L4 | insight_adoption_rate ≥ 0.5 | Redis system updates + ChatMessage/Task 回查 |
| L5 | strategy_resonance_rate ≥ 0.6 | profile hit rate（Redis 代理） |

存储：`understanding-depth:current:{uid}`（TTL 365d）、`understanding-depth:notified:{uid}:{level}`；另有 `execution_engine.py:1748-1754` 把快照以 JSON 串写进 assistant 消息 `response_metadata["understanding_depth"]`（即 `chat_messages.metadata`）。**evaluation 结果本体从不落库**——每次请求现算，等级变化即 Redis 覆写，无任何日粒度留痕。"字段存在但无基线"定性属实。

### 1.2 谁在消费

1. `orchestration/context_builder.py:817-822`：`ENABLE_PERCEPTIBLE_INTELLIGENCE` 开启时 evaluate → `user_context_payload["understanding_depth"]`；
2. `orchestration/prompts.py:1140+`：`understanding_depth_section` 渲染 natural_hint 进 4 个提示词模板（占位预算 60 token / 5%）；
3. `orchestration/session_state_mixin.py:221`：解析 `evolution_kind == "understanding_depth"` 的 system update；
4. `maybe_enqueue_upgrade`：升级时 `build_system_update` 推送用户可见通知。

结论：**消费链健康，缺口在"度量留痕与出口"**——没有历史可比、没有趋势端点、没有验收断言，产品方无法见证"越用越懂"。

---

## 2. 指标设计：理解深度分 v0.1（0-1，每日）

设计原则：只从**既有生产表**聚合（零埋点新增）、当日可实现、逐维单调、可解释可重放。

| 分量 | 含义 | 数据源（已有表） | 归一化 | 方向 |
|---|---|---|---|---|
| memory_injection（权重 0.40） | 记忆命中/注入量：日均注入记忆条数（preferences+goals+episodic） | `context_pack_runs.memory_counts`（JSONB，`core/context_pack.py:1570` 每次上下文组装落一行） | `min(1, avg/3)`，HIT_SATURATION=3 | ↑ |
| personalization（0.25） | 个性化回复率：注入 ≥1 条记忆的 pack 占比 | 同上 | 占比即分量 | ↑ |
| non_correction（0.20） | 1 − 纠正强度：memory_corrections 次数 / max(当日 user 消息数,1) | `memory_corrections` + `chat_messages(role=user)` | `max(0, 1 − intensity/0.5)`，CORRECTION_TOLERANCE=0.5 次/轮 | 纠正越少↑ |
| non_repeat（0.15） | 1 − 重复提问率：当日 user 消息归一化（去空白/标点/小写）后重复占比；≤4 字符寒暄豁免 | `chat_messages(role=user)` | `1 − dup_ratio` | 重复越少↑ |

**合成分** `score = Σ w_i × c_i ∈ [0,1]`（权重和为 1）。单调性论证：各分量是对"更懂用户"的单调函数，正权线性组合保持每维单调——单测 `test_more_memory_injection_increases_score` 等 4 例钉死"更多记忆命中→更高分"。

**冷启动/边界**：当日既无 pack run 也无 user 消息 → 不落行（无活动日不计入均值与趋势）；历史补算由 celery 任务 `day` 参数重放（数据源表保留原值）。

**与运行时 L0-L5 的关系**：L0-L5 是"系统对用户理解程度"的即时等级（偏存量、通知驱动）；本指标是"理解行为强度"的日粒度流量度量（偏增量、可画趋势）。两者并存，components JSONB 保留全部原始样本量供对账。

---

## 3. MVP 实现

| 文件 | 内容 |
|---|---|
| `backend/app/models/understanding_depth.py`（新） | `UnderstandingDepthDaily`：user_id/metric_date/score/components(JSONB)/context_pack_runs/chat_turns，`uq_..._user_date` 唯一约束 |
| `backend/alembic/versions/ud01_20260919_understanding_depth_daily.py`（新） | 可逆迁移，down_revision=**gfix03_20260918**（ScriptDirectory 实证当前唯一 head）；含 Migration Contract 头 |
| `backend/app/services/understanding_depth_metric_service.py`（新） | `compute_components`/`compute_score` 纯函数 + `compute_daily_for_user`（幂等 upsert）/`compute_daily_all`（当日活跃用户全量，单用户失败不阻断）/`get_trend`（7/30 天） |
| `backend/app/core/celery_tasks.py`（+35 行） | 任务 `app.core.celery_tasks.compute_understanding_depth_daily`（max_retries=2，缺省算 UTC 昨天） |
| `backend/app/core/celery_app.py`（+6 行） | beat 条目 `understanding-depth-daily`：crontab 03:40，**queue=default**（按任务书要求路由 default 队列） |
| `backend/app/api/v1/insights.py`（+43 行） | `GET /api/v1/insights/understanding-depth?days=7|30`（route-tier: authed，返回 data[]+meta.latest+definition_version） |
| `backend/gateway/internal/handler/proxy_routes.go`（+2 行） | `insights.GET("/understanding-depth", h.proxyWithHeaders)`；user-id 注入由既有 `SetProxyUserContextHeaders`（AuthMiddleware 上下文 → X-User-ID）承担，网关零业务逻辑 |
| `backend/app/models/__init__.py`、`backend/alembic/env.py` | 模型登记（`__all__` + autogenerate 导入） |

注册实证：`celery_app.tasks` 含任务名、`beat_schedule["understanding-depth-daily"] = {task, crontab 3:40, queue: default}`（进程内断言通过）。

---

## 4. 红绿

### 4.1 单测（tests/unit/test_understanding_depth_metric_service.py，13 项）

| 测试 | red 实证 | green |
|---|---|---|
| `test_more_memory_injection_increases_score` | 首版实现分量未夹紧 → `assert 1.0 < 1.0` 红 | ✅ 更多记忆命中→更高分 |
| `test_memory_injection_saturates_at_hit_saturation` | — | ✅ 饱和点=3 钉死 |
| `test_more_personalized_runs_increase_score` / `test_fewer_corrections_increase_score` / `test_fewer_repeats_increase_score` | 首轮红（同上） | ✅ 逐维单调 |
| `test_score_stays_in_unit_interval` | — | ✅ [0,1] 界 |
| `test_short_messages_exempt_from_repeat_detection` | — | ✅ 寒暄豁免 |
| `test_normalize_memory_counts_ignores_malformed_payload` | — | ✅ 脏 JSONB 容错 |
| `test_compute_daily_for_user_persists_row_and_is_idempotent` | 迁移前 schema 缺失红 | ✅ 落行+重算不重不漏 |
| `test_compute_daily_for_user_skips_inactive_day` / `test_compute_daily_all_covers_active_users_only` | — | ✅ 冷启动/活跃圈定 |

### 4.2 API 测试（tests/api/test_insights_understanding_depth_api.py，4 项）

趋势结构（data+meta.latest 升序）、7/30 窗口映射与缺省、days=3/60 → 422、新用户空趋势。red 实证：端点未挂 prefix 时全量 404 → 挂 `/insights` 后绿。httpx ASGITransport 与 db_session 同事件循环（sqlite 内存基座）。

### 4.3 迁移验证（主库只读纪律的落法）

- **不连主库**：`tests/unit/test_understanding_depth_migration_sqlite.py` 用 alembic `Operations.context(MigrationContext.configure(sqlite_conn))` 把 ud01 的 upgrade/downgrade **单迁移隔离重放**在临时 sqlite 文件库：表结构 10 列全对、唯一约束/索引齐、downgrade 后表消失；ORM 语义验证——同用户同日第二行被唯一约束拒绝。
- **单头守卫**：`tests/test_migrations_single_head.py` 通过，新 head = `ud01_20260919`（规则守卫同步输出"✅ alembic 单头: ud01_20260919"）。
- **为何不整链 upgrade**：140+ 迁移含 pgvector/AGE 等 PG 专属 DDL，sqlite 无法整链重放；worktree 软链主仓 `.env` 仅用于让 Settings 可实例化，`DATABASE_URL` 从未被用于写主库（测试全走 conftest sqlite 内存基座 + 临时文件库）。
- **未做** autogenerate 空 diff 校验：空库 diff 会把全量 140 迁移产物误报为"未应用"，噪音无价值；改为上述列集显式断言（同等信息、零噪音）。

### 4.4 治理守卫与环境性红

`bash scripts/run_all_rule_guards.sh`：仅 **AQ/BG** 红——worktree 缺 gitignored 的 `app.gen`（python proto 产物），pristine 8b17ca15 上同红，属环境产物缺失非本改动回归（网关侧已软链主仓 `gen/` 并以 `CGO_ENABLED=0 go build ./...` + handler 测试 28s 全绿验证）。

最终：**18/18 新测试 green + 单头守卫 2/2 + ruff 全绿 + black(120) 已格式化 + go vet/build 过**。

---

## 5. 验收脚本第 10 项（scripts/devtools/acceptance_memory_revival.py，+59 行）

- `ud10.endpoint(理解深度趋势端点接线)`：经网关 GET `/api/v1/insights/understanding-depth`，断言 200 + `meta.definition_version=="v0.1"`（证明网关代理→鉴权→引擎全链）；
- `ud10.baseline-monotonic(二轮分>首轮基线)`：best-effort `celery call compute_understanding_depth_daily` 触发离线计算（worker 未跑则显式 SKIP 并给出提示，不写主库——脚本仅 SELECT，落表由产品自身 celery 任务完成）；有基线行时断言 `scores_asc[-1] > scores_asc[0]`（末行=记忆注入后的二轮，首行=首轮基线）。

---

## 6. 已知边界与后续

1. **memory_counts 依赖 `ENABLE_CONTEXT_PACK_TELEMETRY`**（settings 开关）：关闭时 memory_injection/personalization 两分量按 0 计，score 退化为 non_correction+non_repeat 的 0.35 封顶组合；上线清单需确认该开关（`context_pack.py:1556` 消费点）。
2. **beat 只算 T-1**：03:40 跑昨日；"今天"的基线要等次日（`day` 参数支持手动重算）。API 趋势为已落行日期，前端需按日期补零。
3. **AQ/BG 守卫**在 worktree 因 `app.gen` 缺失同红（基线同红），主仓跑不受影响。
4. **后续（非本波）**： components 纳入重复提问的 embedding 相似度口径（当前纯文本归一化）；`insights` 端点接 mobile 周报卡片；理解深度分与 L0-L5 等级做相关性对账。
