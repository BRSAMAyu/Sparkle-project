# A-05 · Bounded Policy Patches / Adaptive Preferences — Worker 报告

**STATUS: READY_FOR_REVIEW (REVISION 2)**

- 卡片：`v3/07_tasks/cards/A-05.md`（Stream AURORA，Gate V3-3，risk **high**，Reviewers 2，locks aurora-policy + experience-memory，Depends on A-02✓/M-06✓/D-05✓）
- Base SHA：`e56be400`（wt15 HEAD，M-06/D-05/A-04/X-05B 已合入）
- Final SHA：同上（未 commit；交付物 = 本目录 + `changes.patch`）
- 返修：R2 DeepAudit **CHANGES_REQUESTED**（`REVIEW_RECEIPT_2.md`）→ 本版
  修复 P2-1/P2-2/P2-3/P3-4/P3-6/P3-8，登记 P3-5/P3-7/P3-9（见 §7 返修记录）
- 真实 LLM 调用：**0 次**（本卡纯确定性机制；无语义层通道）
- 词表 39：**零新名**（零事件、零 outbox、零 registry 变更——`git diff HEAD` 仅 1 行既有文件改动 + 7 个新文件；`test_event_registry_contract.py` 回归绿）

---

## 1. 实际解决的问题

AURORA_V3 §4 Bounded Plasticity 此前只是文档语义：「Aurora 可以保存
PolicyPatchCandidate，只有白名单 surface 可生效」没有机制化身。本卡把它落成
**代码边界**（提示词边界不是边界——A-02/X-02 已论证，本卡把「可塑性面」
做成同款结构性边界）：

1. **六面白名单 fail-closed**（卡面 Work 1）：`POLICY_PATCH_SURFACES` 封闭
   枚举恰好六面（granularity / clarification / explanation /
   intervention_preference / proactive_cadence / allocation_preference），
   精确集 + sha256 双钉。「改 prompt / 改代码 / 改模型参数」没有合法的
   surface 名，走不到任何写路径——`propose_patch` violations 非空即零写路径。
2. **生命周期状态机**（Work 2）：candidate→evidenced→active→expire/revoke
   （+rejected 终态）封闭迁移表；证据门**只认真实证据源**（M-06 投影记录 /
   D-05 outcome_observed 行），档位真源是 D-05 `association_evidence_tier`
   （≥repeated 自动激活；single_observation 需用户确认——confirm(若需)）；
   revoke 即时生效 + append-only 审计 + 终态不可复活（M-01 supersede 哲学）。
3. **policy version 进 Context/cache key**（Work 3）：active 集内容寻址版本
   `polpatch_<sha256[:16]>`；服务层决策输入缓存以 (输入摘要, 版本) 为键——
   active 集任何变化 → 版本必变 → **缓存不命中**；消费方自建缓存用
   `patch_cache_key(base, version)` 并入版本；决策载荷归因
   `annotations["policy_patch_version"]`（A-01 annotations extend-only）。

## 2. 关键设计决策

1. **patch 是决策输入，不是代码**（红线机制化）：六个面的消费契约全部是
   确定性投影——3 面进 A-02 提名重排（intervention_preference/granularity/
   clarification）、1 面进 X-02 因子（allocation_preference →
   `AllocationFactors.user_preference` 既有入参）、1 面进 proactive 门因子
   （minimal cadence → `proactive_budget_available=False`，A-02 X1 显式请求
   豁免不变）、1 面进解释参数化（explanation style）。不存在「patch 生效 =
   改 prompt/代码/模型参数」路径。
2. **重排只调序，永不越守卫**：`reorder_nominations` 只重排 `nominated`
   顺序；A-02 feasible set / R0-R9 守卫 / inert 地板语义不变（patch 把
   practice 提名到首位，无任务锚点时仍被 R3 剔除 → no_action——测试钉死）。
   patch 也不凭空注入提名（提名权在 spine/L2/决策环）。
3. **证据方向语义**（消费 M-06 红线）：prefer 需 ≥1 条正向共同出现证据、
   demote 需 ≥1 条负向（失败等价保留）；无 outcome 的 M-06 记录不构成证据
   （`evidence_count>0` 才解析）；截断投影按 `completeness_adjusted_strength`
   保守取档（FIX-31 P2-1 消费侧同律）。
4. **evidence ref 落在 A-01 既有 scheme**：`memory://experience/<expmem_id>`
   与 `decision://aurora_<32hex>`——两者均在 `AURORA_DECISION_REF_SCHEMES`
   内（零新名），可直接进 `AuroraDecisionContract.evidence_refs`（测试过
   `build_decision_contract` + `validate()==()`）。
5. **allocation_preference 不绕过 A-04 联合约束层**：走 X-02 既有
   `user_preference` 入参（服务层 import 期断言与 X-02 `USER_PREFERENCES`
   精确相等——漂移 fail-fast）；测试钉死「prefer_agent + practice 提名 →
   J1.delivery_mode_incompatible 确定性剔除」——偏好不高于结构边界。
6. **审计自包含**：行内 append-only `transition_history`
   （{at, action, from, to, reason, actor}）——revoke 的审计依据是永不消失
   的行，不是 7 天清理的 outbox（D-05 同款分工）。幂等：
   `uq_policy_patch_once(patch_id)` 内容寻址（同内容重提议返回既有行）。
7. **版本缓存契约**（M-06 (cache_key, watermark) 同构）：
   `patched_decision_inputs` 进程缓存命中 = 存储版本与缓存版本一致 + TTL 内；
   版本比对是机制化守卫（变异：`if cached_version != version and False` → 3 测红）。

## 3. 交付物

| 文件 | 内容 |
|---|---|
| `backend/app/core/policy_patch.py` | 冻结契约（纯函数）：六面白名单 + payload schema + 状态机/迁移表 + 16 reason 码 + 证据门常量 + 版本/缓存键 + 提名重排 + 因子/参数化投影 |
| `backend/app/services/policy_patch_service.py` | 服务层：fail-closed propose / 真源证据门（M-06 projector + D-05 行）/ confirm / revoke（即时+审计）/ expire sweep / effective 集 / 版本 / `patched_decision_inputs`（缓存+归因） |
| `backend/app/models/policy_patch.py` | `aurora_policy_patches` 表（revoke≠删除；审计行内保留） |
| `backend/alembic/versions/a05_20260919_add_aurora_policy_patches.py` | 迁移（down_revision=d05_20260919，单头延续） |
| `backend/tests/contract/test_policy_patch_contract.py` | 契约冻结 39 条：六面精确集+sha256 / fail-closed 全维 / 状态机 T6 / 版本语义 / 重排确定性×5 |
| `backend/tests/services/test_policy_patch_service.py` | 服务测试 35 条（R1 25 + R2 返修 10）：sqlite 真证据链全流程 / 四验收复现 / 用户隔离 / 幂等 / R2 返修钉死面 |
| `backend/tests/unit/test_policy_patch_migration_sqlite.py` | 迁移隔离重放 3 条（表结构/唯一约束/回滚 + 链挂接 d05） |
| `backend/app/models/__init__.py` | +1 行注册（唯一既有文件改动） |

## 4. 证据

### 4.1 目标测试（全绿）

```
cd backend && SECRET_KEY=test /opt/homebrew/bin/python3.11 -m pytest \
  tests/contract/test_policy_patch_contract.py \
  tests/services/test_policy_patch_service.py \
  tests/unit/test_policy_patch_migration_sqlite.py -q
→ 77 passed（R1 67 + R2 返修新增 10）
```

### 4.2 四项验收的独立复现路径

- **非法 patch field 被拒收**（①）：
  `TestFailClosedPropose::test_illegal_surface_writes_nothing`（system_prompt/
  temperature/prompt_override/code → V1 + 行数 0）+
  `test_illegal_payload_writes_nothing`（未知键/词表外值/错面键）+
  契约 `test_non_whitelisted_surface_rejected_fail_closed` ×10 参数化。
- **用户纠正可撤销**（②）：
  `TestRevokeImmediate::test_revoke_excludes_from_same_scope_decisions_immediately`：
  同 scope（exam+cognitive_overload）同提名输入，revoke 前 `practice` 重排
  首位且 `applied_patch_ids` 含该 patch；revoke 后**同一调用**返回基线序
  `("explain","practice")`、归因排除、版本 bump、T4 审计条目保留。
- **同 scope 历史有效 intervention 改变 ranking + evidence refs**（③）：
  `TestRankingWithRealEvidence`：真实 D-05 `record_exposure`+
  `record_outcome_association`×2（positive）→ 真实 M-06
  `ExperienceMemoryProjector` 投影 → patch 引用投影 record_id → 证据门
  repeated 自动激活 → `patched_decision_inputs` 重排 + `memory://experience/…`
  refs → A-02 `evaluate_intervention_policy` 按重排序选中 practice →
  `build_decision_contract` 过 `validate()==()`。全程生产服务路径，零 mock/
  零 seed 行/零 monkeypatch（证据源无 stub）。
- **policy version 缓存失效**（④）：
  `TestVersionCacheInvalidation`：版本 bump（revoke）→ `_inputs_cache` 不
  命中（重算输出无 patch）；`_cache_get` 版本不一致单测返回 None；
  `test_expiry_read_time_gate_and_sweep`（过期读时门 + sweep 幂等）。

### 4.3 变异必红（终态文件上执行；cp 备份逐字节还原，cmp 确认）

R1 原生变异（3/3）：

| 变异 | 注入 | 结果 |
|---|---|---|
| M1 白名单放开 | core surfaces 集加 `"system_prompt"` | 4 red（精确集 + sha256 + 参数化 V1 + 服务零写） |
| M2 revoke 泄漏 | effective 查询 `state in (active, revoked)` | 1 red（同 scope 决策仍引用被撤 patch） |
| M3 缓存忽略版本 | `_cache_get` 版本比对 `and False` | 3 red（stale 缓存 + 版本单测 ×2） |

R2 返修复演（4/4，含 R2 存活的 M7/M8——现已 killed）：

| 变异 | 注入 | 结果 |
|---|---|---|
| M8 审计重写非追加（R2 存活 → 本版 killed） | `_apply` history=`[entry]` | **4 red**（T1/T2、T1/T3、T1/T2/T4 序列断言 + append-only 单调性/前缀保持） |
| M7 终态复活 on re-propose（R2 存活 → 本版 killed） | 幂等分支 `existing.state="candidate"` | **1 red**（revoke→同内容 re-propose→仍 revoked 断言） |
| P2-1 缺陷复演（scope 泄漏，R2 PROBE_A） | 三因子投影喂未过 scope 的 `patches` | **3 red**（scoped allocation/proactive/explanation 三面绑定测试） |
| P3-4 缺陷复演（scope 装饰性，R2 PROBE_C） | 两证据通道删 scope 一致性检查 | **2 red**（memory + decision 跨 scope 证据拒收测试） |

### 4.4 回归（R1 基线 264 → R2 验收 485 → 本版 495，零回退）

```
tests/{contract,unit,services}: test_a02_intervention_policy_engine,
test_a04_joint_decision(+joint_factor_projection), test_joint_decision_contract,
test_experience_memory_{contract,projector}, test_intervention_lifecycle_
{contract,service}, test_event_registry_contract, test_aurora_decision_contract
→ 418 passed（R2 验收基线同数，零回退）+ 本卡 77 = 495
```

迁移单头：`tests/test_migrations_single_head.py` 绿（a05 挂 d05_20260919）。
ruff/black：新文件全部通过。

## 5. 边界与在途冲突面

- **避开**：X-06（tools）/X-03（command 路径）/M-08（memory API）片——本卡
  零 API router、零 tools/command 改动、不触 memory API 面。
- **不重建真源**：outcome=D-02/D-05；聚合=M-06/D-05；选择=A-02；分配=X-02；
  联合约束=A-04；契约形状=A-01（annotations extend-only 消费）。
- **词表 39 不动**：零事件名新增（审计自包含于 transition_history）。

## 6. 已知限制与后续（接线日工作，非本卡缺陷）

1. **运行时接线**：`patched_decision_inputs` 是决策环装配面的就绪接口，
   spine/L2/决策环的实际调用点接线属后续消费卡（A-02 的 spine 投影同理——
   引擎先落地、接线随后）。本卡以全链路集成测试（重排→A-02→A-01 契约）
   钉死接口正确性。
2. **patch 提议的产生**（AURORA_V3 L4 `policy_patch_candidate`）不在本卡：
   本卡提供 fail-closed 的 propose 入口与证据门；L4 分析器产候选归决策环
   后续卡（provenance 词表已预留 `l4_async_analysis`）。
3. **多 patch 同面冲突**：非重排面按 (created_at, patch_id) 最新者生效
   （确定性）；重排面互不冲突时叠加、同目标冲突时后处理者胜——均为确定
   性行为，测试钉死。
4. expire sweep 由读路径顺手收敛 + 显式幂等 sweep 双保险；无后台定时器
   （部署面选择，非语义缺失）。
5. **inputs 缓存对证据增长仅 TTL 兜底（P3-5，R2 确认轻级）**：版本键只覆盖
   active patch 集，不覆盖 M-06 证据水位——新 outcome 落库后同版本命中旧
   缓存，evidence_refs/族内序最长 120s（`INPUTS_CACHE_TTL_SECONDS`）陈旧。
   有界、可接受；**接线卡注意**：`patch_cache_key` 只并入 polpatch 版本，
   对证据新鲜度敏感的消费方需自行并入 M-06 watermark。

## 7. REVISION 2 返修记录（R2 DeepAudit CHANGES_REQUESTED → 本版）

对象：`REVIEW_RECEIPT_2.md` 全部 9 项发现（P1 无）。逐项处置：

| 发现 | 处置 | 落点 |
|---|---|---|
| **P2-1** scope 对三非重排面失效（PROBE_A 实测泄漏） | **修复**：`patched_decision_inputs` 因子投影前按 `scope_matches`（与重排同一谓词）过滤 `situation_patches`；双向钉死（exam patch 在 project 情境 → None/{} + exam 情境生效） | service L541-560；`TestScopedNonRankingSurfaces` ×3 |
| **P2-2** append-only 审计无测试（M8 存活） | **修复（测试）**：全部审计断言从 any() 升级为有序全史（长度+序列）；新增每步快照钉「长度单调 + 早期条目逐字节不可变 + from/to 链自洽」；M8 复演 4 red killed | 3 处既有断言强化 + `TestTransitionHistoryAppendOnly` ×2 |
| **P2-3** `_apply` 读改写无锁（丢失更新窗口） | **修复**：写前 `SELECT…FOR UPDATE` + `populate_existing` 重读，以库内当前状态做迁移判定（不一致 → T6 零写，后到者让位）——M-01/M-07 同构；sqlite 单写者天然串行（FOR UPDATE no-op），另附构造性交错测试（直接 SQL 提交并发 revoke 终局 → 迟到 confirm T6 让位、终态不被覆盖、审计零丢失） | service `_apply`；`TestApplyConcurrencyGuard` ×1 |
| **P3-4** admit 门不校验 patch scope × 证据 scope（PROBE_C） | **修复**：`_verify_evidence` 两通道（memory:// 签名切片 + decision:// D-05 行固化列）同律——已约束维度与证据切片精确相等才解析，否则 G1 rejected；跨 scope memory/decision 双钉 + 同 scope decision 正控制 | service `_verify_evidence`；`TestAdmitScopeConsistency` ×3 |
| **P3-6** 终态不可复活无测试（M7 存活） | **修复（测试）**：revoke → 同内容 re-propose → 幂等返回终态行原样（state/revoked_at/审计长度/行数全不动）+ 新内容后继行走新 patch_id；M7 复演 1 red killed | `TestTerminalStateNotResurrected` ×1 |
| **P3-8** 测试 goal 值不在词表（错配失真） | **修复（卫生）**：`test_scope_mismatch_does_not_rank` 改词表真值 exam vs project；另两处 incidental `goal="coursework"`（归一 unknown）一并换真值 | 测试文件 3 处 |
| **P3-5** 缓存对证据增长仅 TTL 兜底 | **登记**（§6.5）：120s 有界陈旧，接线卡需并入 M-06 watermark | §6 已知限制 |
| **P3-7** mode 过滤依赖 A-01 mode-mandatory 上游不变式 | **钉住**：`_verify_evidence` 逃生口处加注释钉死上游不变式与放松时的收紧义务 | service P3-7 注释 |
| **P3-9** 迁移索引名与 ORM 缺省名不同 | **登记**：D-05 同款房规（migration 显式命名），schema.sql 走迁移导出，cosmetic 不动 | 本表 |

验证面（全部在本 worktree 终态文件上执行）：

- 目标测试 **77 passed**（R1 67 + 新增 10）；迁移单头 2 条绿；
- R2 返修复演 **4/4 killed**（M8: 4 red / M7: 1 red / P2-1 复演: 3 red /
  P3-4 复演: 2 red——R2 时 M7/M8 均 0 red 存活）；全部 cp 备份 + cmp
  逐字节还原确认；
- 回归 **418 passed**（与 R2 验收基线同数，零回退；418+77=495）；
- ruff / black（120）：改动文件全绿；真实 LLM 0 次；主仓/dev DB 零接触。

## 8. Leader 合入前处置（DELTA-1/DELTA-3，双 PASS 后追加）

- **DELTA-1**（档位计数）：`association_evidence_tier(resolved)` 替代 `len(rows)`——只计过滤后有效观察。注：返修轮 P3-4 双通道修复已使 rows 上游 scope 过滤（该路径下 len==resolved），本修复为防御加固；变异验证在当前代码下不可达（诚实记录），正向钉 `test_tier_counts_only_in_scope_rows` 保留。
- **DELTA-3**（旁列盲写）：双重根治——①结构化：confirm_patch/admit_evidence 的旁列（user_confirmed/confirmed_at/activated_at）移至 `_apply` 迁移成功后赋值，拒绝路径控制流上不存在旁列写；②SAVEPOINT：`_locked_transition` 查询+守卫包进 begin_nested，T6 拒绝回滚丢弃 autoflush 盲写（生产 AsyncSession autoflush=True 场景兜底）。测试 `test_t6_rejection_leaves_no_side_column_traces` 验证锁下让位+行零痕迹；注：测试 fixture autoflush=False 且 populate_existing 覆盖内存脏值，autoflush 盲写机制在 fixture 下结构性不可红绿复现（诚实记录），修复正确性由控制流结构保证。
- 复验：79 目标绿（77+2 新钉）；合并口径 499+2。
