# M-07 R2 深层验收回执（DeepAudit）

- 审查人：R2（V3 Fleet 深层验收，DeepAudit 路线）
- 审查时间：2026-09-19 15:20 – 15:45
- 审查对象：wt8 @ 10fde918 基线上的 M-07 改动（自报 9 文件 2 新增 7 修改，1399+/124-）
- **总 Verdict：CHANGES（返修后重审，架构保留）**
- 一句话：管线骨架、事务原子性、单入口幂等、词表重冻、合入预演全部独立复核通过；但**派生复活主通道在「偏好曾修改过一次」这一最常见产品流下仍然是开着的（P1，运行时实证）**，且钉住 epoch 门的测试实际未钉住（变异存活）。critical 卡不可 ACCEPT。

---

## 0. 审查中发生的事故（必须先读）

**wt8 在审查中途被外部清空。** 15:34:03 有另一会话（推断为 R1 评审员，stash 名 `m07-r1-review-baseline-check`）在 wt8 内执行 `git stash push -u`；随后 wt8 被 `reset --hard 10fde918` + clean（reflog `HEAD@{0}: reset: moving to 10fde918...`），M-07 全部工作区改动与 `v3-output/M-07/` 交付物被清空，且**主仓（Sparkle-project @ d21d1579）从未合入 M-07**——交付物一度只存在于两个 dangling git 对象里。

R2 已完成恢复并验证（全部只读操作，未写主仓工作区）：

- stash 合并提交 `fa34c0814d03a45239e8c53d0f3f6cf196e58213`（7 个 tracked 文件）
- untracked 提交 `2928b999b86988b362832dba7d564ff38187b837`（pipeline 模块、17 项测试、REPORT.md、changes.patch）
- 恢复流程：`git archive 10fde918` 导出到 /tmp → 从上述对象逐文件提取 → 补回 gitignore 的 `backend/app/gen`（从 wt8 现树拷贝）→ **恢复树 17/17 测试全绿**
- patch 完整性：恢复的 changes.patch 在基线导出树上 `git apply` 后与预清空状态 **9 文件逐一 byte-identical**（含 stash 里被 R2 变异污染的 profile_context_service.py 一行——R2 已还原并经 17 项测试回归确认）
- 交付物已回填 `wt8/v3-output/M-07/`（REPORT.md、changes.patch、两份探针测试）；**wt8 工作树保持基线干净**（不替 Worker 复原工作区改动，避免与可能存活的 R1 会话冲突）

Leader 需知：dangling 对象在 gc 前有效，建议尽快 `git branch recover/m07 fa34c081` 固化（或直接以 changes.patch 为准合入）。**在确认无仍在运行的 R1 会话前，不要再动 wt8。**

**续报（15:44-15:47）**：写回执期间，另一会话把 stash 重新 apply 回了 wt8 工作区——R2 检出其中 `profile_context_service.py` 携带 R2 变异实验 M1 的残留（epoch 门条件行缺失，1398+/124-），已由 R2 还原该行并复跑 17/17 全绿，wt8 现为 Worker 真实原状（1399+/124-）。教训入库：**评审员的变异实验与 stash/apply 恢复交错会污染交付树，跨会话共享 worktree 必须先协调**。R2 的探针 #1 临时文件已从 tests/unit 移除（证据版在 v3-output/M-07/）。

---

## 1. 逐风险面 Verdict

### 1.1 事务原子性真实性 — **PASS（有一处文档失实，见 P2-1）**

- `apply_in_txn`（memory_invalidation_pipeline.py:130-169）内 epoch bump（`_bump_memory_epoch_in_txn`，:313-377，`UPDATE..RETURNING`+flush）与事件 INSERT（:222-236，原生 SQL 同一 session）确实与状态变更同事务、无嵌套 commit。`bump_memory_epoch`（带独立 commit 的旧路径）已不再被四入口调用，`_bump_epoch_best_effort` 已删除。
- 四入口调用点均在 caller commit 之前：memory_service.py:1164（retract）、:1220（bulk）、:1297（correction reject）、:1407（revoke_episodic）、:199（supersede upsert），之后统一 `await self.db.commit()`。correction 与 supersede 同一入口收敛，属实。
- **P2-1**：模块 docstring :19-20 与 REPORT 均声称「commit 之后 DEL 派生缓存」；实际 `invalidate_derived_caches` 在 `apply_in_txn` 内部、**caller commit 之前**执行（pipeline:164），仅 WM 路径（commit=True）顺序正确。回滚时 DEL 已发生（多余重编译，无害方向）；更重要的是它在 P2-2 的 ABA 竞态里加宽了窗口。

### 1.2 幂等与并发 — **单入口 PASS / bulk REPEAT FAIL（P2-3）**

- retract/revoke_episodic/apply_correction 三个单记录入口：`with_for_update()` + 同事务内 `derive_status != active` 复查（memory_service.py:1136-1151、:1265-1267、:1364-1369），串行收敛成立；变异实验 M3（删复查）被击杀，测试真钉住。bump 无内部重试，commit 失败整事务回滚，无「事件写成功 UPDATE 重试」双 bump 路径。
- **P2-3（confirmed，代码即证）**：`revoke_inferred_memories` 的 select（memory_service.py:1195-1208）**没有 `with_for_update()` 也没有逐行终态复查**。两个并发批量撤销批次重叠同一用户时（admin kill-switch 重试/双触发/不同 subject_types 过滤相交），双方都读到同一批 active 行 → 各自 `_apply_retraction` + 每用户各一次 `apply_in_txn` → **同一用户两次 epoch bump、两条聚合事件、两套审计**。「每用户恰一次 bump」只在串行调用/重试下成立。串行重试幂等成立（第二次 select 过滤 revoked_at IS NULL → 0 行 → return 0）。
- PostgreSQL 真双连接并发未实测（dev DB 只读纪律，Worker 也如实登记）；sqlite 单连接下验证的是重试收敛，这部分与 Worker 自报一致。

### 1.3 词表重冻 — **PASS**

- 独立重算：`sha256("|".join(sorted(EVENT_REGISTRY)))` = `c281556037c9dcdca6931e44fe483d8351070e0a7f986e1b19fcaa93bd70fd9c`，与冻结常量一致；34 名。
- `memory_id` 进 CORRELATION_KEYS/CorrelationIds（纯增量，diff 干净）；CorrelationIds 构造器对非 UUID 会抛 EventContractError（实测），管线传入的是规范化 UUID 串，一致。
- 豁免类（CORRELATION_EXEMPT）未被触碰（diff 无涉）。
- 合约测试 31 passed + 1 failed；失败项 `test_truth_path_modules_never_read_client_telemetry[app/state_aggregator/service.py]` 检查的是**本卡未修改的文件**，按文件独立性判定为基线预存（与 Worker 自报一致）。

### 1.4 派生复活修复真实性 — **FAIL（P1 主通道未关死）+ 门正确但未被测试钉住（P2-4）+ ABA 窗（P2-2）**

**P1（Confirmed defect，运行时实证）**：`_remove_live_preference_key_in_txn` 的链头检查（memory_service.py:1737-1749）只过滤 `deleted_at IS NULL AND retracted_at IS NULL AND id != record.id`，**漏了 `replaced_by_id IS NULL`**。`derive_status`（memory_epistemic_contract.py:116-117）把 `replaced_by_id != None` 判为 SUPERSEDED 终态，但该 SQL 不看它。后果（探针 #1 于 15:31 在原树运行复现，`AssertionError: P1 CONFIRMED: live key survived...`）：

```
设置偏好(0.6) → 修改偏好(0.8)   [正常产品流，v1.replaced_by_id=v2]
→ 面板删除链头 v2
→ head-check 命中 v1（superseded 但 retracted_at 为 NULL）→ return False
→ live user_preferences.explicit["depth_preference"]=0.8 原样保留
→ ProfileContext 每次编译永久复活已删值
```

任何**曾被修改过一次**的偏好（即本功能最典型用户）删除后复活通道全开。交付测试 `test_memory_panel_preference_delete_removes_live_value` 只覆盖单版本链，未覆盖 supersede 链。修复：链头检查补 `MemoryPreference.replaced_by_id.is_(None)`（或直接用 derive_status 语义过滤），并加探针 #1 为回归测试（已存 `r2_probe1_supersede_chain_test.py`）。

**P2-4（Confirmed，变异实验）**：epoch 门代码本身正确（探针 #2 双向验证：门在 → 拒绝 stale；门删 → 放行 stale），但交付的 `test_profile_context_cache_rejected_after_epoch_bump` **没有钉住它**——该测试 fake 了 `_get_preferences`（构造用 version=7）而门上的 `get_preference_version` 读真实 DB（无行 → 默认值），版本失配先拒绝，epoch 条件从未参与判定。变异 M1（删除 `and context.memory_epoch == current_epoch`）后该测试**仍绿**。「DEL 失败也不复活」这条硬保证目前处于零有效测试状态。修复：按探针 #2（已存 `r2_probe2_epoch_gate_test.py`）让 version 匹配、仅 epoch 失配。

**P2-2（Highly probable，源码推理）**：inline snapshot 的 epoch 在**缓存写入时**读取（profile_context_service.py:432 `_write_inline_snapshot_cache`），而内容来自写入前的一系列 DB 读；构建期间（prefs→knowledge→cognitive→error→compile 可达数百 ms）若删除事务 commit，则「旧内容 + 新 epoch」入缓存 → 门通过 → 已删内容以 120s TTL（:45-46）复活。主 profile_context 缓存的同类撕裂窗小得多（epoch 在构造器处读，位于各内容读之后、compile 之前——顺序仍不安全但窗为 ms 级）。正确做法：epoch 在内容读**之前**读一次并复用于两处嵌入；或 setex 前复查 epoch、变化即跳过写入。此为「删除后 0 使用」验收的概率性破洞，窗口小、影响有界（≤120s），privacy-critical 卡建议一并修。

**其余核实**：aurora self_model 主动 DEL 属实（`_ALWAYS_INVALIDATED_TEMPLATES`，pipeline:89-93），TTL 90 天场景闭环；`_get_memory_epoch` 读失败 fail-closed 0（:437-448）方向正确（边缘：epoch 读持续失败期间写入的 epoch=0 条目会在持续失败期互相匹配放行——影响极窄，P3）；WM forget 端点接 `apply_working_memory_forget`（commit=True 后 DEL，顺序正确）；`memory_jobs` 衰减过滤补 `revoked_at/retracted_at IS NULL` 属实（但漏 `superseded_by_id IS NULL`，superseded 终态行仍被后台触碰——P3）。

### 1.5 M-03 接口漂移（合入风险）— **文本零冲突 / 语义清单见 §3**

- M-07 触碰的 7 个修改文件在 wt8 基线（10fde918）与主仓 HEAD（d21d1579）**逐字节一致**（diff -q 全 SAME）；M-03 返修只动了 business_metrics/context_manager/context_pack/context_builder/memory_retrieval_prefilter，与 M-07 文件集零交集。
- `memory_epoch_version_string()`（pipeline:104-115）在主仓全树**零引用**——是「提供待用」而非「已对接」，Worker §7 表述属实。
- 主仓 M-03 的 `context_manager.get_user_context`（main:226-246）缓存命中时仅刷 `past_session_memory` 且包在 `contextlib.suppress(Exception)` 里：DB 抖动时**静默供旧 episodic 内容**（fail-open）。这是主仓侧（M-03 域）问题，但与「删除后 context 0 使用」验收直接相关，列入合入 checklist。
- F4（today-only UTC 切日）/F5（settings 读失败 fail-open 不对称）：wt8 基线确无 `memory_retrieval_prefilter.py`（grep 无符号），不可修未合入代码的判断成立；主仓 M-03 合入信息自身就把「UTC+8 day-boundary, midnight rollover」「fail-open asymmetry」登记为延期项。交接要求见 §3。

### 1.6 长程/批任务 — **PASS（P3 两笔）**

- 衰减批任务过滤不误伤 active 行（只加终态过滤）；supersede 推进后旧行状态=replaced_by_id 置位（superseded），`derive_status` 判终态，但衰减过滤漏它（P3，见上）。
- nightly_review 输入仅 ErrorRecord+UserStateSnapshot（import 核对属实）；understanding_depth 纯计数豁免成立（epoch_bump 审计行自 M-01 起本就入 memory_corrections，非本卡新增失真）。

### 1.7 测试语义 — **M1 存活 / M2 M3 M4 击杀 / 预存失败抽检通过**

| 变异 | 操作 | 预期测试 | 结果 |
|---|---|---|---|
| M1 | 删 profile_context 缓存门 epoch 条件 | test_profile_context_cache_rejected_after_epoch_bump | **存活（仍绿）→ P2-4** |
| M2 | `await redis.delete` 改为不 await 协程 | aurora/profile_context 两个 DEL 测试 | 击杀（双红） |
| M3 | 删 retract_memory 终态复查 | test_retract_memory_repeat_keeps_single_epoch | 击杀 |
| M4 | 删 `_remove_live_preference_key_in_txn` 调用 | test_memory_panel_preference_delete_removes_live_value | 击杀（但见 P1：仅单版本链） |

预存失败抽检：contract 1 失败为检查未修改文件的遥测守卫（文件独立性即证基线预存）；ltm e2e 的 dev Postgres 认证与 inferred-lane embedding RetryError 未复跑（环境性，与 M-07 无文件交集，采信 Worker stash 对照 + 文件独立性）。

### 1.8 合入预演 — **PASS**

- 主仓 d21d1579 导出树上 `git apply --3way --check changes.patch` → **exit 0**，7 文件全部 cleanly（2 个经 3way 回退后仍自动解析），2 新增文件平凡落地。
- 合入语义风险不在文本，在 §3 checklist。

---

## 2. 发现分级

### P1（必修，阻断合入）

1. **supersede 链后删链头 → live 键不摘除，复活主通道仍开**（§1.4，memory_service.py:1737-1749，探针 #1 运行时实证）。修复：head 查询补 `replaced_by_id.is_(None)`（含 superseded_by_id 语义），加探针 #1 回归。

### P2（应当修，随返修一并）

2. **DEL 在 commit 之前执行**，与 docstring/REPORT 声明相反（pipeline:161-164 + memory_service.py 四调用点）。回滚方向无害，但加宽 P2-2 竞态窗。修复：`apply_in_txn` 移除内部 DEL，改为返回 keys 由 caller 在 commit 后调用（或 commit 回调）。
3. **bulk_revoke 无行锁无终态复查**，并发重叠批次双 bump/双事件（memory_service.py:1195-1227）。修复：select 加 `with_for_update()` 或按 user 分组加 advisory lock + 行级复查。
4. **epoch 门测试未钉住**（变异 M1 存活）：换成探针 #2 的构造（version 匹配、仅 epoch 失配）。门代码本身无需改。
5. **inline snapshot 写时钉 epoch 的 ABA 窗**（profile_context_service.py:432）：构建跨删除 commit 时旧内容配新 epoch，120s TTL 内复活。修复：epoch 前置读取并复用 / 写前复查。

### P3（观察/登记）

6. 衰减批任务漏滤 `superseded_by_id` 终态行（memory_jobs.py）。
7. `lower_confidence` 纠错不走管线（分数类非删除，语义边界可接受，登记即可）。
8. epoch 读持续失败期写入的 epoch=0 条目互配放行（极窄）。
9. （主仓侧）context_manager 缓存命中刷 `past_session_memory` 的 `suppress(Exception)` fail-open + CognitiveContext 缓存无 epoch 门——归 M-03/M-04 域，见 checklist。

---

## 3. 合入 Checklist（Leader 执行单）

前提：**P1 修复并通过探针 #1/#2 后方可合入**；P2-2/3 建议同批，P2-4/P2-5 必须同批（证据质量）。

文本合入（已验证无冲突）：
- [ ] 主仓 HEAD 应用 changes.patch（`git apply --3way --check` 已过）；词表 34 名 + 新冻结哈希随之落地，合约测试同步。
- [ ] 合入前确认 wt8 事故现场已处置：`git branch recover/m07 fa34c081` 固化 dangling stash（或确认以 changes.patch 为唯一真源后允许 gc）；排查 R1 会话是否仍在操作 wt8，避免二次覆盖。

M-03 适配项（合入后立即）：
- [ ] M-03R2/M-04 消费 `memory_epoch_version_string()`（当前主仓零引用）：若 memory_retrieval_prefilter 的 L0 过滤结果或 context_pack 产出有任何缓存，组键必须拼 epoch 组件，否则 M-07 的 epoch 门保护不到 M-03 侧缓存。
- [ ] 主仓 context_manager `get_user_context` 缓存命中路径：`suppress(Exception)` 包裹的 past_session_memory 刷新失败时静默供旧 episodic 内容（fail-open），建议 fail-closed 或加 epoch 门；同文件 CognitiveContext 缓存（300s，仅 preference_version 门）评估是否补 memory_epoch 门。
- [ ] `context_builder` stage34 / `context_pack` 在 M-03 加的 prefilter 出口确认对 SUPERSEDED（replaced_by_id/superseded_by_id 置位）行同样拒绝（M-01 derive_status 已含，M-03 status 维度沿用即可，抽查一次）。

F4/F5 交接项（M-03R2 落地时，Worker §7 已登记，此处落成可执行条目）：
- [ ] F4：`memory_retrieval_prefilter` today-only 窗口改用用户时区（timezone 默认 Asia/Shanghai 的 UTC+8 切日），或至少在 prefilter_metadata 记录 day-boundary 假设；M-03 合入信息已把「UTC+8 day-boundary, midnight rollover」列为延期项，归属明确。
- [ ] F5：settings 读路径异常时的 fail-open 不对称修正（读异常应与写路径一致 fail-closed；本卡侧旁证：写路径 MemoryPolicyEvaluator 对缺失行 allowed=True 是默认值语义、读异常上抛，不对称点确在 M-03 读侧）。
- [ ] 上述两项若 M-03R2 未覆盖，转 M-04 前置卡（Worker 建议成立）。

## 4. 核实通过、无需返修的项（给 Worker 的正面清单）

事务内原子性（bump/事件/审计/状态同事务、无嵌套 autocommit）；三单入口 FOR UPDATE+终态复查；`_bump_epoch_best_effort` 删除；await 修复真实（M2 击杀）；词表 34 名哈希独立重算一致；payload 内容无关（无 summary/pref_value/reason 原文）；WM forget 顺序正确；outbox 序列 upsert PG 路径成立；17/17 在两棵树独立复现；回归与预存失败判定全部复核成立；F4/F5 不可修不存在代码的处置诚实。

## 5. 收尾状态

- wt8 工作树：保持基线（未替 Worker 复原代码改动）；`v3-output/M-07/` 已回填 REPORT.md、changes.patch、r2_probe1/r2_probe2 两份探针、本回执。
- /tmp：m07r2、m07r2_pristine、m07r2_main、m07r2_verify、wt8_base_* 已全部清除。
- 主仓：全程只读（git archive/diff/grep/fsck 均 O(·) 读操作）；未起服务、未跑模拟器/浏览器、未 commit/push。

— R2 深层验收员，2026-09-19
