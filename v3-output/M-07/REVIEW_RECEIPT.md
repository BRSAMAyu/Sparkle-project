# M-07 R1 标准验收回执（general 路线）

- 审查人：R1（V3 Fleet 标准验收员）
- 审查时间：2026-09-19 15:20 – 15:55
- 审查对象：wt8 @ 10fde918 基线上的 M-07 改动（自报 9 文件 = 2 新增 + 7 修改，1399+/124-）；交付物 `v3-output/M-07/{REPORT.md, changes.patch}`
- 主仓只读参照：Sparkle-project @ d21d1579（含 M-01/M-02/M-03/D-01/E-05 已合入版）
- **总 Verdict：CHANGES（返修后复审，架构保留；C1 修复并补回归前不得合入）**

---

## 0. 事故责任声明（按 Leader 指令先行报告）

wt8 审查期间的树清空事故，触发源是**我的 `git stash -u`**：两个验收会话共享同一 worktree 而未协调，我的 stash 窗口（工作区瞬间回到基线干净态）被 R2 观察为「树被清空」。我在此确认：

- 我在 wt8 内执行过的全部写性操作（完整清单）：①`git stash push -u -m m07-r1-review-baseline-check`（≈15:34）→ ②`git stash pop`（15:35:24 成功，Dropped fa34c081）→ ③为红态实验 `git stash push -m m07-r1-red-state-check`（仅 7 个修改文件）→ ④`git stash pop`（≈15:38 成功，Dropped bbada142）→ ⑤两次 `git restore --staged`（仅 intent-to-add 索引标记，为使 ① 可执行）→ ⑥`git add -N`（恢复 Worker 原有 intent-to-add 状态）。
- **我未执行过 `git reset`、`git clean`、分支切换**。reflog 实证（`git reflog -12`）：审查窗口 15:20–15:47 内无任何 HEAD 移动记录，最新条目 `10fde918 HEAD@{14:50:57}: reset: moving to 10fde918...` 早于本次审查开始（属交付前会话的基点准备）。R2 回执 §0 引用的「reset+clean reflog」即此 14:50:57 旧条目，时间上不属于本次事故窗口。
- **stash 名单：当前 `git stash list` 为空**。我的两笔 stash 均已成功 pop 并 drop（对象 fa34c081、bbada142）；coordinator 确认 `recover/m07` 分支已固化 fa34c081，无数据风险。
- 15:41–15:44 工作树还有第二组并行写入（R2 的变异实验 M1：删 `profile_context_service.py` 的 epoch 门条件行后还原）。我在 15:42:50 于「无门版本」工作区实测 17/17 仍全绿——该意外观察恰好构成 C2-1 的关键证据（见下）。
- 已遵守新规：收尾 `git status --short` = 9 文件 + `v3-output/`，无多余残留（见 §7）。

## 1. 改动面核对 — PASS

- `git -C wt8 log --oneline -3`：基点 `10fde918`（M-02 ACCEPT merge），与 Worker 自报一致；`main` 的 merge-base(10fde918, d21d1579) = 10fde918，即 wt8 基线是 main 祖先、落后 4 个提交（E-05 / V3-FIX-13 / M-03 / gitignore）。
- `git status --short` + `git diff --stat`：9 文件、1399+/124-，与自报逐一相符；`v3-output/M-07/` 为 untracked 交付目录。
- **changes.patch 与工作区 diff 逐字节一致**（审查开始时与收尾时两次比对，md5 `0f3f319cccaf11a091af5402c9aa1407` 两侧相同——R2 的事故恢复未污染交付内容）。
- 无密钥、无 `/Users/` 绝对路径、无夹带无关改动（grep 复核；命中项均为测试夹具假数据如 `hashed_password="test"`、用于断言「事件不携带明文」的假银行卡字符串）。memory_jobs/profile_context_service 内的黑体格式化 churn 限于本卡已触碰文件，符合 black(120) 项目风格。

## 2. 任务目标达成核对 — 机制真实，主通道修复有 C1 级漏洞

### 2.1 单入口收敛与事务边界 — PASS

`memory_invalidation_pipeline.py` 全文 446 行读毕。四动作（correction: reject/no_longer_applicable；revoke: revoke_episodic + retract_memory；supersede: upsert_preference 版本推进；bulk_revoke）全部收敛到 `MemoryInvalidationPipeline.apply_in_txn`（:130-169）：`_bump_memory_epoch_in_txn`（:313-377，原子 `UPDATE..RETURNING` + 懒建 + flush 无独立 commit）与 `event_outbox` 原生 SQL INSERT（:222-236）同 session 同事务；四个调用点（memory_service.py 的 retract/bulk/correction-reject/revoke_episodic 及 supersede）均在各自 `await self.db.commit()` 之前调用。`_bump_epoch_best_effort` 已删除。M-01 契约文件 `memory_epistemic_contract.py` 与主仓 d21d1579 版**逐字节一致**（diff 为空）；管线状态转移全部经由契约 `derive_status`（revoked > superseded > retracted > archived > expired > resolved > active）判定，合法性成立。epoch bump 语义与主仓 M-01 `bump_memory_epoch`（memory_service.py:1559-1625）一致，唯一差异是并发首撞 IntegrityError 上抛使整个事务中止（设计意图，docstring 注明，客户端重试经幂等守卫收敛）——与 M-01 的 rollback+重试策略不同但方向正确。

### 2.2 事件词表与 D-01 契约 — PASS

独立重算 `sha256("|".join(sorted(EVENT_REGISTRY)))` = `c281556037c9dcdca6931e44fe483d8351070e0a7f986e1b19fcaa93bd70fd9c`，与重冻常量精确一致；词表 33→34 名（`memory.invalidated`，STATE_UPDATE，aggregate=user_memory，producer=管线文件，status=live）。`CorrelationIds`/`CORRELATION_KEYS` 增 `memory_id`（纯增量）。payload 内容无关（schema_version/memory_type/action/memory_ids/memory_epoch/reason_code≤40；测试断言 summary 明文不出现在 payload）。

### 2.3 派生消费面 — 门与 DEL 落地属实；**live 摘键存在 C1**；门测试未钉住（C2-1）

- ProfileContext 缓存门 = `preference_version ∧ memory_epoch`（profile_context_service.py:140-144，交付 patch 版）；inline snapshot 写入钉 epoch、读取 fail-closed（缺 epoch 或失配 → None，:402-421）；`_get_memory_epoch` 读失败 fail-closed 0（:430-446）；aurora self_model 90 天 TTL 主动 DEL（管线 `_ALWAYS_INVALIDATED_TEMPLATES`）；衰减批任务补 `revoked_at/retracted_at IS NULL` 过滤——均属实。
- **C1（必修）**：`_remove_live_preference_key_in_txn`（memory_service.py:1737-1749）的「更新链头存在即跳过摘键」守卫只过滤 `deleted_at IS NULL AND retracted_at IS NULL AND id != record.id`，**未按 derive_status 排除 superseded 行**（`replaced_by_id/superseded_by_id` 非空、`retracted_at` 为 NULL 的旧版本会命中）。实证（我的独立复现测试，非依赖 R2 探针；15:38 在交付树上运行）：`set_explicit_preference 0.6 → 0.8`（v1 superseded、v2 活跃链头）→ `retract_memory(v2)` 返回 True → **live `user_preferences.explicit["depth_preference"]=0.8 存活**。「先编辑后删除」是最常见产品流，Worker 的 headline 修复（红→绿实证）只覆盖了单版本链场景（`test_memory_panel_preference_delete_removes_live_value` 无链）。epoch 门挡不住它：摘键缺失时重编译读到的真源仍含已删值。与 R2 的 P1（探针 #1 运行时实证）完全同因同象。修复：head 查询补 `replaced_by_id.is_(None)`（并按契约对齐 `superseded_by_id` 语义），将 supersede→delete 链场景固化为回归测试（可直接采用 `v3-output/M-07/r2_probe1_supersede_chain_test.py`）。
- **C2-1（证据质量，必修）**：`test_profile_context_cache_rejected_after_epoch_bump` **没有钉住 epoch 门**。测试 fake `_get_preferences` 返回 version=7，而门内 `get_preference_version` 读真实 DB（该用户无行 → 0），版本恒失配使 preference_version 门先行拒绝缓存，epoch 条件从未参与判定。铁证：15:42:50 我在 epoch 门条件行被（并行会话）移除的工作区实测 17/17 全绿、该单测亦绿（工作文件 blob e4817be7，与交付 blob 757366d8 唯一差异即该行）；R2 的变异实验 M1 独立得出相同结论。修法：mock `get_preference_version` 与缓存一致（或造真实偏好行），构造「仅 epoch 失配」场景（可直接采用 `r2_probe2_epoch_gate_test.py`）。

### 2.4 幂等与并发 — 单入口 PASS；bulk 表述失实 + 并发缺口（C2-2）

- retract / revoke_episodic / apply_correction(reject) 三单记录入口：`with_for_update()` + **同事务内** `derive_status != active` 复查（memory_service.py:1136-1151、:1265-1267、:1364-1369），复查读的是锁内行，成立。测试断言为真「恰一次」：`len(audit)==1`、`len(events)==1`、epoch 不再变化、`revoked_at` 不被覆盖、`correction_count` 不重复累加（== 断言，非 >=0）。
- **C2-2**：`revoke_inferred_memories`（:1195-1227）**无 `with_for_update()`、无逐行 derive_status 复查**，仅有 `revoked_at IS NULL` SQL 预过滤。顺序重试幂等成立（inferred 行 `_apply_retraction` 置 `revoked_at`，二次调用选 0 行 return 0）；但 PG 上两个并发 bulk 批次重叠同一用户时可双 bump/双事件。Worker 报告「四个入口统一 SELECT...FOR UPDATE + derive_status 复查」对此入口**表述失实**（测试亦只覆盖单次调用）。修复：select 加行锁或按用户 advisory lock + 复查；至少修正报告表述。

### 2.5 DEL 时序 — 方向安全，表述失实（C2-3）

`apply_in_txn` 在 `commit=False`（服务层四路径）时，`invalidate_derived_caches`（:164）执行于 **caller commit 之前**；「提交后 DEL」仅对 commit=True 的 WM 路径（memory.py forget 端点）严格成立，与模块 docstring :19-20 及 REPORT 表述相反。回滚时产生多余 DEL（无害方向）；窗口内再水合的缓存携带旧 epoch，提交后必被读侧门拒绝，正确性由门保证。建议（随 C1 返修顺带）：DEL 移出 `apply_in_txn`，由 caller 在 commit 后执行。

### 2.6 inline snapshot ABA 窗（C2-4，R2 首发现，R1 依代码复核成立）

`_write_inline_snapshot_cache`（profile_context_service.py:427-437）在**写入时**才读 epoch，而快照内容来自此前数百 ms 的 DB 读序列；构建期间删除事务 commit 会产生「旧内容 + 新 epoch」入缓存，门通过，已删内容以 120s TTL 存活。主 profile_context 缓存的同类窗为 ms 级（epoch 在构造器读）。修法：epoch 前置读取一次并复用于两处嵌入，或 setex 前复查 epoch。

## 3. 测试实跑 — 全部独立复现（三重验证）

环境：wt8/backend + sparkle-cosmos venv（Python 3.11.15，pytest 9.0.3），sqlite in-memory + FakeRedis，内联 `SECRET_KEY`（未落盘 .env），未触 dev DB/Redis 写路径，真实 LLM 0 次。

| 项 | 我的实测 | Worker 自报 | 一致 |
|---|---|---|---|
| `test_memory_invalidation_pipeline.py` | **17 passed**（8.2s-11.9s 多轮） | 17 passed | ✓ |
| 红态（stash 法回退 7 个源文件、保留新增 2 文件实跑） | **13 failed, 4 passed** | 13 RED / 4 passed | ✓（精确到个数） |
| `test_event_registry_contract.py` | 31 passed, 1 failed | 同 | ✓ |
| `test_memory_inference_write_guard.py` | 8 passed | 8 | ✓ |
| `test_memory_epistemic_contract.py` | 11 passed | 11 | ✓ |
| `test_conflict_resolver_epistemic_guard.py` | 3 passed | 3 | ✓ |
| `test_working_memory_rejection_guard.py` | 3 passed | 3 | ✓ |
| `test_memory_inferred_write_lane.py` | 6 passed, 1 failed（60s embedding RetryError） | 同 | ✓ |
| `test_ltm_e2e.py` | 2 failed（asyncpg InvalidPasswordError，1s） | 同 | ✓ |
| `test_chat_signal_collector_profile_loop.py` / `test_aurora_control_surface_service.py` | 2+2 passed | 2+2 | ✓ |
| 治理守卫 `--rule AC` | **PASS**（working_memory transient-only） | PASS | ✓ |
| black / ruff | 未复跑（采信自报；diff 格式与 black(120) 一致性目检通过） | 通过 | — |

**基线预存失败三重验证**（事故后按新规以 clone 法重做，与 stash 法、Worker 自报三方一致）：
1. `test_truth_path_modules_never_read_client_telemetry[state_aggregator]`：clone 基线 1 failed/31 passed——该测试检查本卡未修改的文件，预存成立。
2. `test_ltm_e2e` 2 failed：clone 基线同样 2 failed（Postgres 认证，环境性）。
3. `test_memory_inferred_write_lane` 1 failed/6 passed：clone 基线同样（embedding RetryError，环境性）。
clone 法：`git clone wt8 /tmp/m07-baseline-check`（天然 HEAD 基线，untracked 不混入）+ 补拷 gitignore 的 `app/gen`，在 /tmp 内实跑。

## 4. 豁免与接线核对 — PASS（接线确认为合入后项）

- semantic_cache 豁免成立：`_generate_cache_key` 拼 `kv={knowledge_version}` + 读取时 knowledge_version 相等校验（semantic_cache_service.py:91-110, 183-204）；wt8 与主仓（d21d1579）版本该机制一致，合并树上豁免论据仍成立。
- nightly_review 豁免成立：仅 import ErrorRecord/NightlyReview/UserStateSnapshot，无 episodic/preference 内容。
- understanding_depth 豁免成立：纯计数指标（context_pack_runs.memory_counts / memory_corrections 行数），无内容载荷。
- **`memory_epoch_version_string()`：wt8 与主仓全树零引用**（仅管线内定义）——是「提供待用」而非「已接线」。主仓 `memory_retrieval_prefilter.py`（M-03 已合入版）无任何 memory_epoch 引用。**定性：合入后接线项，随 M-03R2 落地**，与 REPORT §7 表述相符。F4/F5 位于 M-03 预筛代码、wt8 基线确无该文件，Worker「不可修补未合入代码」的处置诚实成立。

## 5. 合入冲突预测 — PASS（文本零冲突）

- `git diff --name-only 10fde918 d21d1579` 与 M-07 的 9 文件**零交集**（main 侧改动集中在 M-03/E-05 域：context_manager、memory_retrieval_prefilter、semantic_cache_service 等，均非本卡触碰文件）。
- 主仓只读预演：`git -C Sparkle-project apply --3way --check < changes.patch` → **exit 0，7 个修改文件全部 cleanly 应用（2 新增平凡落地），主仓工作树事后确认未被改动**（status 空、HEAD 仍 d21d1579）。
- 合并的实质风险不在文本，在 §6 checklist 的 M-03 适配项。

## 6. 必修项分级与合入 Checklist（Leader 执行单）

### 发现分级（与 R2 回执 P1/P2/P3 对照）

| R1 编号 | R2 对照 | 内容 | 级别 |
|---|---|---|---|
| C1 | P1 | supersede 链后删链头 live 键不摘除，复活主通道仍开（运行时实证×2） | **必修，阻断合入** |
| C2-1 | P2-4 | epoch 门测试未钉住（变异存活；我在无门树上实测 17/17 绿） | 必修（随 C1 同批） |
| C2-2 | P2-3 | bulk 入口无行锁无复查 + 报告「四入口统一 FOR UPDATE」表述失实 | 应修（至少修表述） |
| C2-3 | P2-1 | DEL 在 caller commit 前执行，与 docstring/REPORT 相反 | 应修（顺带） |
| C2-4 | P2-2 | inline snapshot 写时钉 epoch 的 ABA 窗（R2 首发现） | 应修 |
| C3 | P3 | ①测试 :497 未 await 协程断言恒真；②memory_jobs 漏滤 superseded 终态行；③epoch 读持续失败期 epoch=0 条目互配；④lower_confidence 不走管线（语义边界，登记即可） | 观察/登记 |

### 合入 Checklist

1. [ ] **C1 修复**：`_remove_live_preference_key_in_txn` 链头查询补 `replaced_by_id.is_(None)`（对齐 superseded_by_id 语义）；采纳 `r2_probe1_supersede_chain_test.py` 为回归。
2. [ ] **C2-1 修复**：采纳 `r2_probe2_epoch_gate_test.py` 构造（version 匹配、仅 epoch 失配）替换/加固交付测试；修后重跑 17 项 + M1 变异确认被击杀。
3. [ ] C2-2/3/4 同批复核：bulk 行锁（或改报告表述+登记并发边界）、DEL 后置、epoch 前置读取。
4. [ ] 文本合入：`git apply --3way --check` 已过（R1/R2 双验）；词表 34 名 + 冻结哈希 `c2815560...` 随 patch 落地；若 M-03R2 再扩词表需再冻。
5. [ ] M-03R2 接线：`memory_epoch_version_string()` 进 retrieval prefilter / 任何记忆敏感缓存组键（当前主仓零引用）；F4（UTC+8 切日）/F5（settings 读 fail-open 不对称）随 M-03R2 或转 M-04 前置卡。
6. [ ] M-03/M-04 域登记（R2 发现，R1 认可）：主仓 context_manager `get_user_context` 缓存命中刷 `past_session_memory` 的 `suppress(Exception)` fail-open；CognitiveContext 缓存（300s）仅 preference_version 门，评估补 epoch 门。
7. [ ] 事故处置确认：`recover/m07` 分支已固化（coordinator 确认）；以 changes.patch（md5 0f3f319c...）为唯一合入真源；两个验收会话不再并行操作同一 worktree。
8. [ ] Worker 披露的 dev Redis ~4 个 `aurora:self_model:{uuid}` 测试残留键（90d TTL）：红线禁模式删除，Leader 知悉、择机处理。

### R1 未复核项（如实）

black/ruff 实跑、K/Z 守卫失败的环境归因（AC 已验 PASS；K/Z 未跑）、PG 真双连接并发（Worker/R2/R1 三方均受 dev DB 只读纪律限制，sqlite 串行收敛已验）。

## 7. 收尾状态

- `git -C wt8 status --short` = 9 文件（7 M + 2 A intent-to-add）+ `?? v3-output/M-07/`，无多余残留；stash list 空；HEAD 10fde918 未动。
- /tmp 已清：`m07_worktree.diff`、`m07_final.diff`、`m07_check3.diff`、`pcs_{patch,worktree}_version.py`、`m07-baseline-check/`。未 commit/push；主仓全程只读（唯一写性命令为 `apply --3way --check`，验证未落盘）；未起服务/模拟器/浏览器。

## 8. 实跑命令清单（可复现）

```bash
# 基点/改动面
git -C wt8 log --oneline -3; git -C wt8 status --porcelain; git -C wt8 diff --stat
git diff > /tmp/m07_worktree.diff && diff /tmp/m07_worktree.diff v3-output/M-07/changes.patch   # md5 双验
# 词表重冻
python -c "from app.core.event_registry import EVENT_REGISTRY; import hashlib; \
  print(hashlib.sha256('|'.join(sorted(EVENT_REGISTRY)).encode()).hexdigest())"   # c2815560... == 冻结常量
# 测试（SECRET_KEY 内联）
SECRET_KEY=... python -m pytest tests/unit/test_memory_invalidation_pipeline.py -q            # 17 passed
SECRET_KEY=... python -m pytest tests/contract/test_event_registry_contract.py -q             # 31p/1f
SECRET_KEY=... python -m pytest tests/unit/test_memory_inference_write_guard.py tests/unit/test_memory_epistemic_contract.py \
  tests/unit/test_conflict_resolver_epistemic_guard.py tests/unit/test_working_memory_rejection_guard.py -q
SECRET_KEY=... python -m pytest tests/unit/test_memory_inferred_write_lane.py -q              # 6p/1f
SECRET_KEY=... python -m pytest tests/integration/test_ltm_e2e.py -q                          # 2f（PG 认证）
SECRET_KEY=... python -m pytest tests/unit/test_chat_signal_collector_profile_loop.py tests/unit/test_aurora_control_surface_service.py -q
SECRET_KEY=... python -m pytest tests/unit/test_m07_r1_independent_repro.py -q                # C1 独立复现（已删，代码存回执 §2.3）
bash scripts/run_all_rule_guards.sh --rule AC                                                  # PASS
# 红态实验（事故前 stash 法）与基线复核（事故后 clone 法）
git clone wt8 /tmp/m07-baseline-check && cp -R wt8/backend/app/gen /tmp/m07-baseline-check/backend/app/gen
cd /tmp/m07-baseline-check/backend && pytest <三项预存失败测试> -q                              # 三项全部复现
# 合入预演（主仓只读）
git -C /Users/brsama/code/GitHub/Sparkle-project apply --3way --check < wt8/v3-output/M-07/changes.patch   # exit 0
git -C /Users/brsama/code/GitHub/Sparkle-project log --oneline -1 && git -C /Users/brsama/code/GitHub/Sparkle-project status --porcelain  # 确认未落盘
```

— R1 标准验收员，2026-09-19。总 Verdict：**CHANGES**（C1/C2-1 修复并复审通过后可达 ACCEPT；架构、事务模型、词表、幂等骨架、豁免论证均予保留）。
