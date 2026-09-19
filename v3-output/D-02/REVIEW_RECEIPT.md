# D-02 R1 验收回执 · Outcome Ledger（general 路线，标准验收）

- **Reviewer**: R1（V3 Fleet 标准验收员）｜ **日期**: 2026-09-19
- **对象**: wt5 @ `fedc6a8e`（与 REPORT 自报 Base 一致），交付 4 个新增代码/测试文件 + `v3-output/D-02/`（REPORT.md + changes.patch）
- **方法**: 全部独立重验，不采信 Worker 自报。测试实跑、主仓契约逐值核对、live PG 自构 SQL 复核、patch 字节级比对、apply --3way --check 预演。
- **并发备注**: 审查期间 wt5 出现 R2 会话的探针文件 `backend/tests/services/test_d02_review_tie_probe.py`（15:38 生成，自声明非交付物）——非 Worker 交付、非 R1 产物，原样保留未动。全程遵守并发禁令：未用 stash/reset/clean/切分支。

---

## 一、逐断言 Verdict

### A. 改动面 — **PASS**

| 断言 | 独立证据 | Verdict |
|---|---|---|
| 只有 4 个新增文件，零修改零删除 | `git -C wt5 status --porcelain`：仅 4 个 `??` 代码/测试文件 + `?? v3-output/D-02/`；`git diff`/`git diff --cached` 均空 | PASS |
| changes.patch 与实际一致 | 从 patch 逐文件重构（剥 `+` 行）与 worktree 文件 `diff` 退出码 0、长度一致（core 15346 字节）；patch 恰含 4 个 `diff --git` 头，无夹带 | PASS |
| 无密钥、无主仓绝对路径 | 对 4 文件 + REPORT grep 密钥模式与 `/Users/brsama`：零命中 | PASS |
| 收工清理属实 | 无新增 `__pycache__`；`app/gen` 借用已删（R1 以符号链接重新借入做回归，收工自删）；无进程残留 | PASS |

### B. 测试实跑 — **PASS**

| 断言 | 独立证据 | Verdict |
|---|---|---|
| 63 项全过 | `python3.11 -m pytest tests/unit/test_outcome_ledger_contract.py tests/services/test_outcome_ledger_service.py -q` → **63 passed in 9.40s**（36+27 与声称逐一吻合；secret 注入为一次性进程环境变量，未落盘） | PASS |
| 回归范围与报告一致 | 同命令跑 Worker 点名 5 个套件 → **97 passed, 1 failed**；报告自报 29+3+25+9+31=97 passed + 1 failed，逐项吻合 | PASS |
| 唯一失败为基线先在 | 移出全部 4 个交付文件后单跑 `test_truth_path_modules_never_read_client_telemetry[app/state_aggregator/service.py]` 仍 **FAILED**（6 passed 1 failed）——与本卡无关，与 C-02-R1 结论互证，复认成立 | PASS |
| lint | black(120) `4 files would be left unchanged`；ruff `All checks passed`；`import app.main` OK（借 gen 后） | PASS |
| 三个关键守卫断言为行为断言 | `test_no_evidence_complete_is_self_reported_not_actual`（contract:92-103，断言 `is SELF_REPORTED` 且 `is not ACTUAL`）；`test_user_tier_evidence_never_upgrades_to_actual`（contract:116-134，4 参数化组）；`test_cross_user_ref_cannot_upgrade`（service:349-388，真实构造**他人** StoredFile + 我的 V3 声明引用它——若 `_resolve_declared_refs` 去掉 `user_id` 过滤此测试必翻红）：三者均为可证伪行为断言，非同义反复 | PASS |
| 分页 bug 修复有回归钉住 | `test_single_stream_dominant_walk_reaches_the_end`（service:420-439，30 条 limit=25 必须翻满）+ `test_exactly_full_page_has_no_cursor_when_exhausted`（service:441-449）；实现侧 `fetch_n = limit + 1` 探针与页末游标（outcome_ledger_service.py:398, 431-437, 204-215）与声称一致 | PASS |

### C. 契约一致性 — **PASS（附 1 项声明纠错，见 C2-1）**

| 断言 | 独立证据 | Verdict |
|---|---|---|
| TruthClass 五值口径 | 主仓卡 `v3/07_tasks/cards/D-02.md` work② 明列 actual/self-reported/estimated/unknown；B-02 FINDINGS「真实性评级」补 demo 档。D-02 五值 = 卡面 4 值 ∪ B-02 demo，确定性分级永不产 estimated/demo（`test_classification_never_returns_estimated_or_demo_for_completions` 全组合扫描钉住）——超集对齐成立，不造第二套 | PASS |
| X-01 evidence_kind 七值 + import 期完整性 | 主仓 `backend/app/core/action_plan.py:76-86` 枚举恰 7 值；D-02 `outcome_ledger.py:140-143` 两处 `assert set(映射) == set(EVIDENCE_KINDS)`。主仓若加第 8 个 kind → **import 期 AssertionError 即刻炸**（好），非静默漏 | PASS |
| D-01 correlation.outcome_id「兼容」 | **不成立（如实纠错）**：主仓 `event_registry.py:477-487` `CorrelationIds.__post_init__` 对每个非空 correlation 值强制 `_canonical_uuid`，非 UUID 直接 `EventContractError`——`outc_<sha256[:32]>` 放进 `correlation.outcome_id` 会被**拒**。REPORT §8①「届时 correlation.outcome_id 直接用 outc_* id」按字面执行会炸。与 D-01 自家 `evt_` 前缀的已知限制同类（`derive_event_id` docstring 明载 gateway `IsProcessed` uuid.Parse 拒收、需 follow-up 卡解决）。**今日无任何代码路径实际填充该键**（读模型 + 接线显式延后），故非运行期缺陷，判 C2 文档级必修 | **FAIL→C2-1** |
| 「可选/必需」completion evidence | 主仓 `action_plan.py:268-269`：V3 契约层 `completion_evidence must contain at least one typed entry`（必需）；legacy 行 `action_plan_projection` 返回 None（`action_plan.py:328-330`）→ 无证据合法但分级 self_reported（可选）。验收①的两面均有机械保证 | PASS |
| 卡范围 = 只建读模型、不接线 | 卡面 Acceptance 仅①（不伪装 actual）②（跨模块查询不重复计数），无 HTTP 端点/接线要求；work③「提供 outcome query」由服务层三函数满足，消费点 docstring 双落点登记。**但卡 work① 点名「goal evidence」未映射且未声明**：主仓 `models/goal.py` 的 `goals` 表为粗粒度聚合面（status/progress/mastery 派生字段，live 仅 4 行，未找到独立完成生产者；将其入册反而会与 task/focus 流重复计数）——排除实质成立但零声明，判 C2 文档级 | PASS（附 C2-2） |

### D. live PG 只读复核 — **PASS（漂移如实记录并复算）**

全部只读 SELECT（`docker exec sparkle_db psql -U postgres -d sparkle`，零写）。

| 断言 | 独立证据（R1 自构 SQL，不沿用 Worker 口径） | Verdict |
|---|---|---|
| (a) 五流行数 = 全量翻页总数 | focus 大户 `fc7c84b9`（registration_source=guest）五流自构计数：task_completion **2** + study_record_standalone **0** + focus_session **99** + quiz **0** + behavioral **0** = **101**（Worker 时点为 79——**live 已漂移**：当日新增 COMPLETED focus 至 07:30，全库 tasks 完成行仍 378 未变）。以递归键集等价校验复算：101 行 (occurred,id) 全序无并列（distinct=101），5 个整页锚点逐一满足「锚点下方行数 = total − rn」→ 全量翻页 **101/101、0 重复、0 遗漏**（5 满页 + 1 尾行） | PASS（漂移已复算） |
| (b) GJ03 task e5f5a8b6 唯一性 | 该 id 前缀恰 **1** 行 alive COMPLETED task（actual_minutes=20，completed_at 2026-09-19 02:00:58.885315——契约测试 `_TS` 正取自此行，交叉印证）；echo study_record 恰 **1**；COMPLETED focus **0**、quiz **0**、declared evidence NULL → 按守卫必判 **self_reported**（回声永不升级）。账本身份 =(source, source_id)，源行唯一 ⇒ outcome 唯一 | PASS |

### E. 零写路径 — **PASS**

两模块全文 grep `INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/TRUNCATE/alembic/session.add/commit/flush`：零 DB 写命中（命中的 6 处 `.add/.update` 全为 Python 内存 set 操作，outcome_ledger_service.py:623-679）；DB 语句仅 `select(...)` 构造 ×19。core 模块纯 stdlib+dataclass，无 IO。

### F. 合入冲突预测 — **PASS**

`cd /Users/brsama/code/GitHub/Sparkle-project && git apply --3way --check /tmp/d02.patch` → **PASS（no conflict）**，4 个新文件路径在主仓 HEAD（`42180162`，已越过任务书 d21d1579）均不存在，纯新增；`--check` 只读不落盘，事后 `git status` 干净。注：主仓 HEAD 已前移至 `42180162`，基准以实际 HEAD 预演，无碍。

---

## 二、必修项分级

- **C1（阻断合入）**：无。
- **C2-1（合入前必修，文档/契约声明级）**：纠正「`outc_*` 与 D-01 `correlation.outcome_id` 兼容」的不实声明（`outcome_ledger.py` 模块 docstring :20-21、REPORT.md §2/§8①）。事实：`CorrelationIds` 强制 canonical UUID（event_registry.py:477-487），`outc_<hash>` 今日放入即抛 `EventContractError`。修法：改为「派生风格与 `derive_event_id` 同款；作为 correlation 值需随 D-01 `evt_` 同类 follow-up 卡解决值域门（UUID 化包装或放宽校验），接线卡不得按 REPORT §8① 字面直填」。代码行为零改动。
- **C2-2（合入前必修，文档级）**：补「goal 面不入册」的显式决策记录（REPORT §3/§8 或 core docstring）：goals 为派生聚合状态（progress/mastery 滚动自 task/focus 成果，入册即重复计数，违反验收②），现无独立完成生产者（live 4 行）；如未来出现一等 goal-completion 生产者，按第六源 bump 版本走双人评审。
- **观察项（不要求整改）**：① R2 探针文件 `test_d02_review_tie_probe.py` 在审查期间出现于 wt5，非本卡交付物，处置权在 R2/主会话；② live focus 流当日 +22 行漂移已复算，不影响任何守卫结论；③ 主仓 HEAD 已前移至 42180162，合入前建议对最新 HEAD 复跑一次 apply --check（本次已过）。

---

## 三、总 Verdict

## **ACCEPT**（附 C2-1 / C2-2 两项文档级必修，可与合入同批落地；零代码改动要求）

63/63 实跑全绿；回归 97 过 +1 基线先在失败独立复认；三大守卫为行为断言；契约对齐（B-02 词表、X-01 七值 import 期炸护、X-01 契约层必需证据门）独立证实；live PG 双断言以自构 SQL 复算成立（含漂移）；零写路径、零 schema 变更、patch 与交付字节一致、主仓 apply 预演无冲突。「完成 ≠ 点击」的机械保证（无证据/回声/未解析声明 → 永不 actual；跨用户 ref 防注入）经红测与 live 样本双重实证。

---

## 附：R1 实跑命令清单

```
git -C wt5 log --oneline -3 / status --porcelain / diff / diff --cached
grep 密钥模式与绝对路径（4 文件 + REPORT）
patch 逐文件重构 + diff 字节级比对（core/svc/两测试）
PYTHONDONTWRITEBYTECODE=1 SECRET_KEY=<一次性测试值> python3.11 -m pytest tests/unit/test_outcome_ledger_contract.py tests/services/test_outcome_ledger_service.py -q      # 63 passed
同环境 pytest tests/unit/test_action_plan_contract.py tests/unit/test_action_plan_migration_sqlite.py tests/test_action_plan_v3_integration.py tests/services/test_event_idempotency_isolation.py tests/contract/test_event_registry_contract.py -q   # 97 passed 1 failed
移出 4 文件后单跑失败守卫（基线复认）→ 文件逐一回位
python3.11 -c "import app.main"          # OK（app/gen 以符号链接只读借入，收工删除）
black --check --line-length 120 ×4 文件；ruff check ×4 文件
grep 零写路径模式 ×2 模块
docker exec sparkle_db psql -U postgres -d sparkle -At -c <自构只读 SELECT：五流计数/全序锚点校验/GJ03 断言/cohort 探针>
git -C 主仓 apply --3way --check /tmp/d02.patch（只读预演）
```

收工清理承诺：删除 R1 借入的 `backend/app/gen` 符号链接与 `/tmp/d02*` 产物；wt5 终态 = 4 交付文件 + v3-output/D-02/（含本回执）+ R2 探针（非 R1 处置）。
