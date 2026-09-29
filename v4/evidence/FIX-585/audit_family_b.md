# FIX-585 B 型深审：7 文件冻结时间戳消费链定性

- 审计人：V4 舰队修复工程师（FIX-585c）
- 日期：2026-09-29（本轮机器本地日期；工作区 darwin/arm64）
- 主仓：`/Users/brsama/code/GitHub/Sparkle-project`
- 上游：FIX-585b 扩扫（[audit_family.md](audit_family.md) §三）收敛 B 型 7 文件——冻结时间戳按「数据」注入、服务端真实时钟消费面未证。本轮逐文件走「注入点 → 服务端消费链 → 判定」实查（不信任注释、不猜），判定方法与六文件深审同款：「冻结双端/纯渲染/路由键 → 安全」vs「真实时钟差值/窗口 → 炸弹（爆点=冻结值+窗口）」。

## 结论先行

**7 文件：2 炸弹 + 5 安全。** 两枚炸弹均为首例 stuck_journey 同构（测试冻结数据基点 + 服务端真实 `utcnow()` 差值/窗口），已修复（测试基点动态化/补注时钟，与首例 e694242d 同款修法）；5 文件安全链各自留证。修前基线 7 文件合跑 **145 passed EXIT=0**（未爆≠安全：判定以消费链实查为准，跑绿只证当前未爆与改动无回归）；修后同口径 **145 passed EXIT=0**（用例数零漂移）。

## 一、判定表

| # | 测试文件 | 冻结注入点 | 服务端消费链实查 | 判定 | 爆点 |
|---|---|---|---|---|---|
| 1 | `backend/tests/api/test_insights_evidence_cards_api.py` | `_NOW = datetime(2026,9,25,10,0)`（原 L64）→ `_seed_lifecycle_event` 默认 `occurred_at=_NOW-2h`（:91）、窗外样本 `_NOW-45d`（:413） | **炸弹**。API 端点 `get_evidence_cards`（insights.py:46-67）调 `build_cards(user_id, window_days)` 不传 `now` → `evidence_insight_service.py:123-124` `now_naive=(now or datetime.utcnow())`、`since=now_naive-30d`，查询谓词 `occurred_at >= since`（:242/:335/:355/:542/:566/:613）。冻结种子 2026-09-25 08:00 随真实钟漂出 30 天窗 → friction/helped 卡消失，3 用例翻红（test_three_kinds / test_helped_suppressed / test_correction_updates）。`test_user_isolation_and_window` 的 -45d 样本恒出窗（越久越真）；`test_censored_split` 已用动态 `utcnow()`（:332） | **炸弹 #1 → 已修** | **2026-10-25 08:00 UTC**（= 种子时刻 + 30d 窗；审计日距今 25.8 天） |
| 2 | `backend/tests/api/test_insights_understanding_dimensions_api.py` | `FROZEN_NOW=2026-09-25 12:00`、`FROZEN_TODAY`（:25-26）→ `metric_date`/`ran_at` 播种（:77/:94） | 读面零钟：`get_latest_row` 纯 `ORDER BY metric_date DESC LIMIT 1`（understanding_dimensions_service.py:409-417）；`latest_run` 纯 `ORDER BY ran_at DESC LIMIT 1`（understanding_calibration_service.py:333-340）；端点（insights.py:109-201）无 utcnow。冻结值只作排序键，取最新行与宿主钟无关 | 安全（路由键/排序键） | 无 |
| 3 | `backend/tests/aurora/test_shadow_comparison.py` | `_NOW=datetime(2026,4,19,10,0)`（:26）→ `SignalSnapshot.collected_at`（:63） | 消费面仅透传：engine.py:154/:204 `created_at=snapshot.collected_at` 进 `TransitionDecisionRecord`（携带字段，无比较）；engine.py 全文无 utcnow/staleness/freshness 判定；`project_aurora_to_dual_core_mode`（migration.py:207-247+）只读 signal 文本与 decision 字段；corpus hook 路径快照与路由同钟现取（migration.py:120 `collected_at or _utcnow()`，参数注入）。legacy 输入 `DualCoreRoutingInput` 无时间戳 | 安全（纯透传） | 无 |
| 4 | `backend/tests/unit/test_card_protocol_phase4.py` | `FROZEN_NOW=2026-09-25 12:00`（:32）→ `due_date`（:101）、`scheduled_for`（:117/:124）、`completed_at`（:186）、`submitted_at`（:201）、feedback_log timestamps（:214/:220） | 消费面无日数学：`_get_plan_occurrences` 纯 `ORDER BY scheduled_for ASC … LIMIT 30`（main_chain_artifact_service.py:500-511），状态只做 Counter（:196）；`_resolve_current_phase` 按 metadata/边序（:430-452）；`submitted_at` 纯透传渲染（:337）；正负反馈判定按 content 关键词（:618-623）；真实 `utcnow()` 只写 `generated_at`/`timestamp` 渲染字段（:230/:351）。create_occurrence 纯插入（task_occurrence_service.py:38-62）。邻座服务 utcnow 均为写侧时戳（decision_log/risk_register/intervention_record/plan_state） | 安全（排序键+纯渲染） | 无 |
| 5 | `backend/tests/aurora/test_proactive_autoexec.py` | `_NOW=datetime(2026,9,21,12,0)`（:52）→ grant 文档 `_NOW.isoformat()`（:203/:228/:255 等）、`now=_now()` 全程显式注入（grant/revoke/decide/handle_operation 每个消费点） | **授权门无新鲜度窗**：`decide_auto_execution` 授权检查是 `op not in grants` 存在性判定（autoexec.py:538-549），grant 时间戳从不与任何时钟比较；`now` 形参全链注入（gate :786 `now=now or _utcnow()`、receipt 落账 :933 `record(receipt, now=now)`）；`receipt.occurred_at == _NOW.isoformat()` 断言（:604）当前绿即证消费端同钟。Redis TTL（grant 180d/receipt 7d）是写侧墙钟键过期，非日期窗比较，FakeRedis 且不实现 ex | 安全（冻结双端：now 全程显式注入） | 无 |
| 6 | `backend/tests/unit/test_memory_retrieval_prefilter.py` | `NOW=2026-09-19 12:00`（:45）→ `RetrievalContext(now=NOW)` 必填注入（:50）+ 记录 `occurred_at/created_at=NOW-1d`、`expires_at`、`due_at`、`valid_from` 等 | 阈值消费面全走注入钟：TTL 判定 `_reject_ttl` `now = ctx.now`（memory_retrieval_prefilter.py:450）、状态机 `derive_status(record, now=ctx.now)`（:434）；`ctx.now` 是必填字段（:244）无回退。唯一的真实钟回退 `utcnow()` 在 `build_retrieval_context`（:707，DB 读侧 context 装配 helper），测试不经过（直构 RetrievalContext）。数据与判定同锚 NOW，day 边界用例（:366-385）双端冻结 | 安全（冻结双端：ctx.now 必填注入） | 无 |
| 7 | `backend/tests/unit/test_memory_utility_gate.py` | `NOW=2026-09-28 12:00`（:32）→ `extract_utility_features(..., now=NOW)`（11 处显式）、`apply_history_utility_gate(..., now=NOW)`（:383/:406）、手构 `UtilityFeatures`（无时间戳，age_days 默认 0） | **一枚炸弹藏在漏网调用**：`evaluate_history_utility` 只吃预提取特征无钟（:340-351 docstring 自证）；但 `test_stale_penalty_grows_beyond_free_window`（:336-348）的 `fresh = extract_utility_features(occurred_at=NOW-5d)` **漏传 `now=`** → 服务端回退真实 `datetime.now()`（memory_utility_gate.py:188）。stale 侧 age 冻结 120d → 罚 `min(1,(120-30)/60)=1.0` 封顶（:329-331，FREE=30d/FULL=90d，:71-72）；fresh 侧 age 随墙钟增长，追平 90d 后 `fresh_score==stale_score`，`assert fresh_score > stale_score` 永久翻红（其余 evaluate/apply 调用点 11 处 `now=NOW` 全注入，安全） | **炸弹 #2 → 已修** | **2026-12-22 12:00 前后**（= fresh 种子 2026-09-23 12:00 + 90d 满罚阈；审计日距今 84 天） |

## 二、修复记录（红→绿）

### 炸弹 #1 — test_insights_evidence_cards_api.py

- 修法（首例 e694242d 同款）：`_NOW = datetime(2026, 9, 25, 10, 0, 0)` → `_NOW = datetime.utcnow()`（模块导入时取）+ 头注因果。修后 `occurred_at=_NOW-2h` 恒在 30 天窗内、`_NOW-45d` 恒出窗，断言语义不变、对宿主钟日期全脱钩。
- 红的证明（消费链，非猜测）：`build_cards` 默认 `now=None` → `utcnow()`；谓词 `occurred_at >= since`，`since = utcnow()-30d`；冻结种子 2026-09-25 08:00 在 `utcnow() > 2026-10-25 08:00 UTC` 后出窗 → `friction_pattern`/`interventions_that_helped` 卡消失 → test_three_kinds（`kinds <=` 断言）、test_helped_card_suppressed（`"friction_pattern" in kinds`）、test_correction_updates（friction 卡取键）三处翻红。
- 爆点算术验证（python 直算）：`seed(2026-09-25 08:00)+30d = 2026-10-25 08:00 UTC`，今日未爆（seed ≥ now-30d 为 True）；修后 `(utcnow()-2h) 在窗 = True`、`(utcnow()-45d) 出窗 = True` 恒成立。

### 炸弹 #2 — test_memory_utility_gate.py

- 修法：`test_stale_penalty_grows_beyond_free_window` 的 `fresh = extract_utility_features(...)` 补 `now=NOW`（对齐同测试 stale 侧与全文件 11 处注入纪律）+ 行注因果。
- 红的证明：漏传 `now` → `extract_utility_features` 服务端回退 `ensure_naive_utc(datetime.now())`（:188）→ fresh age = 真实墙钟 − 2026-09-23 12:00，随日期增长；stale 罚在 age≥90d 封顶 1.0（:329-331），fresh 罚追平后两分相等，`assert fresh_score > stale_score`（严格大于）永久失败。
- 爆点算术验证：fresh 满罚日 = 2026-09-23 12:00 + 90d = **2026-12-22 12:00** 前后（受本机 datetime.now() 本地时区与 naive-UTC 的 ±小时偏移影响，日期级精确）；今日 fresh age=6.02d，罚 0。

## 三、取证跑

```
# 修前基线（两炸弹均在潜伏期 → 全绿，未爆≠安全）
cd backend && DATABASE_URL=sqlite:// SECRET_KEY=x \
  /opt/homebrew/opt/python@3.11/bin/python3.11 -m pytest \
  tests/api/test_insights_evidence_cards_api.py tests/api/test_insights_understanding_dimensions_api.py \
  tests/aurora/test_shadow_comparison.py tests/unit/test_card_protocol_phase4.py \
  tests/aurora/test_proactive_autoexec.py tests/unit/test_memory_retrieval_prefilter.py \
  tests/unit/test_memory_utility_gate.py -q
→ 145 passed in 5.80s, EXIT=0

# 修后同口径
→ 同命令 145 passed in 5.52s, EXIT=0（用例数零漂移）
# 两修复文件单跑
→ 31 passed in 2.74s, EXIT=0
```

## 四、边界甄别与本轮局限

- 爆点日期均为 naive-UTC 语义（服务端 `replace(tzinfo=None)` / naive 比较）；F1 以 CI 触发时刻跨过 2026-10-25 08:00 UTC 起算红，F2 受宿主机本地时区偏移 ±小时级摆动，日期级结论不受影响。
- 同族边界：`backend/tests/unit/test_memory_utility_gate_wiring.py`（find 模式 `memory_utility_gate*` 的另一命中）实查无冻结日期常量——自有 `_utcnow()` 动态钟（:99/:126），不属 B 型，登记豁免。
- F5 的 grant 文档 Redis TTL（180d）与 receipt TTL（7d）是写侧墙钟键过期：同进程测试内 grant→消费间隔为秒级，非日期窗炸弹；FakeRedis 亦不实现 `ex`。
- 与并行会话零交集自查：本轮仅动两个炸弹测试文件 + 本证据文件 + 台账 DYNAMIC_ISSUES.md FIX-585 行（python 追加）；fleet-state JSON 只做 json.load 完整性校验、未写入。
