# V4-I05 · 独立审查 R2 receipt（wtI05R2）

- 审查会话：wtI05R2（独立，未参与 I05 实现与一审）；高风险卡二审（与 R1 互补，聚焦对抗面与合并面）
- 审查对象：`agent/v4/i05` 实现头 `4cac07ecaba214f1441b4de009c585487d078e5e`（branch tip `48dc5453` = R1 receipt；base `ff02ec03`，merge-base 复核为直接父子）；独立下判，不以 R1 结论为前提
- 审查日期：2026-09-29；环境：`SECRET_KEY=ci-test-key DATABASE_URL=sqlite://`，python 3.11.15（Sparkle-project 共享 venv）、pytest 9.0.3、mypy 1.20.2（darwin arm64）
- 全部对抗探针为审查者自写、用后即删；审查结束 `git status` 零残留（探针文件已删，receipt 为唯一产物）

## 总裁决：PASS_WITH_CHALLENGES

派单八靶全部独立复核：对抗面（平票 tie-break / 72h 窗边界竞态 / 折叠×撤回复合）16 探针全绿且未发现行为正确性缺陷；A-05 权威面逐块核通过（单一权威未复制未绕过）；**合并面以真实合并演练定案**（main 已前移至 e50107fe，一审「零交集」已过时——现交集 3 文件，实测零冲突）；C1/C2/C3 复判成立、**C5 复判为原判词事实性不成立**（实测行为比 R1 描述更干净）；新登记 1 项非阻塞缺口（D-1 candidate 态不进撤回 sweep）。全部挑战为披露面/接线面级别，默认 shadow 下无行为风险，不阻塞二审通过。

## A｜对抗面（派单靶 1）——**PASS（16 探针亲跑全绿）**

1. **收益门平票 tie-break（「负向等权」声明下平票走哪边）**：纯层亲测——prefer 要求 `n_positive > n_negative` 严格大于，1正1负平票 → `no_benefit`；demote 对称（1正1负 → `no_benefit`）；censored-only → `censored_insufficient_evidence`（显式不结论）。**平票走「不利方向」**（对 prefer/demote 都是保守侧）。服务面亲测：live + 1正1负平票 + repeated 档 → 停 evidenced（不静默激活）；显式 `confirm_patch` 后 active（扣下不封死确认路径）。声明与实现一致。
2. **72h 窗边界与竞态**：a) 边界时刻 `now == expires_at` → 读时门**排除**（`>=` 语义，无宽限抖动）；b) **窗内 revoke → 窗过期**：+10h 用户撤销、+73h `expire_sweep` 结算数=0（sweep 只看 active）、读门持续排除、行保持 revoked——**无复活**；c) 窗过期（expired 终态）后再 revoke → `T6.illegal_transition` 拒绝；d) 过期行不在撤回 sweep 候选集（active/evidenced 过滤）——失效入口对它既不 affect 也不误伤（双向均不出现）。
3. **折叠×撤回复合**：refs `[a,a,a]` 落库即折叠为 `[a]`（库内亲验）；撤 a → **整卡终态 revoke**（策略失效是补丁粒度，无「部分引用保留」的中间态——剩余引用的档位保持体现在**未命中补丁不受波及**，非同卡部分保留）；纯层亲测折叠后 `source_refs` 决定撤回命中身份——重复条目不产生重复 verdict（单卡单命中）。跨域同值不同域不构成同源（`decision://aurora_aaa…` vs `expmem_record` 目标 → UNAFFECTED，纯层反例亲测）。

## B｜撤回传播对抗（派单靶 2）——**PASS（含 1 项新缺口登记 D-1）**

- **撤回→重放→再提议身份链（expshadow_/内容寻址）**：撤回失效后同内容重提议（含重复 refs 折叠后等价形态）→ 命中**同一 revoked 行**（`idempotent=True`），`admit_evidence` → `T6` 拒绝——终态不可复活结构性成立（内容寻址 id 不含 state，revoked 行就是身份终点）。撤回后 `shadow_report` 重放：effective 集变化 → cards 空 → `strategy_ids` 变 → **comparison_id 必然变化**（新旧 `expshadow_` 报告由派生输入区分，同输入恒同、异输入异 id，无身份混淆）。
- **人工失效入口对抗（retraction.registered 未接线声明下）**：合法但无命中源（decision 域）→ `affected=[]`、`unaffected=[patch]`、`policy_version_before==after`、行零触碰；未知 kind → ValueError（D03 词表）；畸形 ref（scheme 对 id 形态错）→ ValueError（closed-scheme）。fail-loud 口径成立。
- **D-1（二审新发现，非阻塞）：candidate 态绕行缺口**——`invalidate_on_source_withdrawal` 候选集仅 active/evidenced（docstring 已声明），**candidate 态引用已撤源的 patch 不进 sweep**，之后 `admit_evidence` 照常可 active（off 档亲证 tier=repeated→active；live 档亲证正收益源同样放行——收益门只拦无收益，不感知撤回）。缓解面：该入口是**通知性记账**（不删真源数据，B 组畸形拒绝除外）；D03 真实删除落地后 memory 通道 admit 因记录消失走 G1 fail-closed；live 72h 窗有界。**登记义务**：事件接线卡必须二选一——sweep 纳入 candidate，或 admit 前查撤回台账；当前人工入口不验证源真已撤回（入口契约=信任调用方），与 limitations #3 口径一致但应在该卡显式收口。

## C｜A-05 权威面最小改动（派单靶 3）——**PASS（diff 逐块核）**

- `core/policy_patch.py` **零改动**（diff 空）；`POLICY_PATCH_REASONS`/T4 码 `T4.revoked_by_user_correction`/迁移词表原样；`GATE_REASONS` 是 I05 自有封闭词表，未混入 A-05 核心词表。
- **reorder_nominations 单一权威未复制未绕过**：treatment 臂（`project_treatment_arm`）import 调用；decision 面唯一调用点沿用。一审未覆盖的关键点亲核：base 传 `patches`（未过滤）、I05 改传 `application_patches`（=situation_patches 预过滤）——**行为等价有结构性依据**：`reorder_nominations` 内部同谓词过滤（`state=="active" and is_effective(now) and scope_matches(...)`，core :698-704 亲读），预过滤幂等，off/shadow 相对 base 零行为差；live 档唯一差量=allowed_ids 过滤（声明的行为面）。
- 因子投影/归因/applied ids 全部从 `application_patches` 取（off/shadow 下 ==situation_patches，与 base 逐项一致）；`_memory_record_matches` 抽取重构与 base 内联块逐条件等价（P3-7 unattributed 逃逸口、P3-4 scope 精确相等原样随迁）；`validate_patch_request` 策略卡构造期复用非重实现；`STRATEGY_ALLOWED_SURFACES is POLICY_PATCH_SURFACES` 同对象+恰好 6 双钉。
- `revoke_patch` +`actor` 参数：默认 `user` 零行为变化；`actor` 截断 80 字符经既有 `_apply` 词表外自由字段（actor 本就非词表面）；缓存键 +strategy_mode（键为进程私有格式，无外部消费者）。

## D｜C1-C5 复判（派单靶 4；独立下判）

| 项 | 复判 | 依据（亲验） |
|---|---|---|
| **C1** transition_history reason 措辞 | **成立** | 撤回路径实测末条 `{"action":"revoke","from":"active","to":"revoked","reason":"T4.revoked_by_user_correction","actor":"evidence_withdrawal"}`；`evidence_source_withdrawal` 在 `revoke_reason` **旁列**。docstring/diff 文档「reason=…入 transition_history」措辞失实（审计仍可区分：actor+旁列）；常规用户 revoke 对照 actor=user/旁列=user_correction。文档改口建议维持，A-05 词表不 bump 的取舍维持 |
| **C2** limitations#5 前提合并即过时 | **成立（合并演练实证）** | 分支侧 tasks.json D04=PENDING（声明在其时点属实）；main e50107fe D04=done/DONE_REVIEWED。合并后该条前提失实、实质声明（零 galaxy 写路径）不变；合并演练零冲突，改写时点=合并时 |
| **C3** 旧行不回溯边界 | **成立＋加sharp** | 亲测 pre-I05 形态行（3×重复 refs、unfolded id）：新提议折叠 id≠旧行 id 并存、旧行字节零触碰；**且旧行自身 admit 档位不回溯=可照 V3 爬档**（3×重复 refs → tier=repeated → auto-activate）——「不回溯」同时意味着**折叠对存量行无追溯保护**，live 档补偿控制=观察面 record_id 去重+收益门（观察面 1 record 不因重复膨胀）。建议 limitations 补一句的 建议维持，并注明补偿控制 |
| **C4** live 用户披露面缺失 | **维持一审口径（不重开）** | 未重测；代码审读一致（扣下/门出= WARN 日志+Prometheus，终端用户面无披露）；live 启用前置建议归 HUMAN_INBOX/启用门槛 |
| **C5** 重放时 revoked 行入 unaffected | **原判词事实性不成立** | 亲测重放输出：`affected=[]`、`unaffected=[其余 active 补丁]`、`policy_version_before==after`——上一轮 revoked 行被 `state.in_(["active","evidenced"])` 候选过滤**排除，双向列表均不出现**（非 R1 所述「入 unaffected」）。实际语义比 R1 担忧更干净：重放幂等以版本不变证明；残留的次要口径=重放报告对已失效行**完全静默**（无 already_revoked 分组，审计需查行级 history）——登记为后续事件接线卡的可选改进，非缺陷 |

## E｜复跑（派单靶 5；全部审查者亲跑）

| 组 | 结果 |
|---|---|
| 本卡 73（unit 56 + service 17） | **73 passed** |
| A-05 39（test_policy_patch_service.py） | **39 passed** |
| D03 34（tests/core/test_retraction_recompute.py + tests/services/test_retraction_recompute_service.py） | **34 passed** |
| 对抗探针（A/B 两组，用后即删） | **16 passed**（含 candidate 绕行 2 例） |
| mypy 棘轮（rm -rf .mypy_cache ×3 次确定性复核） | **60 / 77, exit 0**；**base ff02ec03 同环境 fresh=60 且错误清单与分支逐字节相同**（`diff` 零输出）→ 分支零新增；R1 记录的 59 为同代码更早共享环境口径（venv 并行会话变迁），非本卡回归；合并树 fresh 亦 60 |

模型调用：0（全部纯函数/sqlite 隔离生产路径）。

## F｜合并落差（派单靶 6）——**真实合并演练定案（一审预判已过时，现实测）**

- main 已从一审时的 3b96039f 前移至 **e50107fe**（U10 销账 29/58；`ff02ec03..main` = 39 commits、201 文件）。文件交集从一审「2 文件（retraction_recompute_service.py+tasks.json）」变为 **3 文件：settings.py / metrics.py / tasks.json**（main 新增 D06 的 GRAPH_INDEX 设置与指标）。
- **真实合并演练**（临时 worktree @4cac07ec merge main）：**零冲突**；settings.py（I05 @972 区 vs D06 @1097 区）与 metrics.py（I05 @799 区 vs D06 @229 区）hunk 不相交，合并后两侧设置/指标共存亲验；I05 五个代码/测试文件合并后与实现头逐字节一致（diff 空）；tasks.json 交集 hunks（main 653-3204 区 vs I05 1049/1101/3666 区）不重叠。
- **合并树复跑**：73+39+34=**146 passed**；fresh mypy 60≤77。
- 语义落差：合并后撤回事件面为「D04 已接线（galaxy 图缓存）+ I05 策略失效未接线」并存，limitations #3 口径在合并后仍成立；D04 接线文件 main 侧改动与 I05 零交集（retraction_recompute_service.py 仅 main 改，I05 只消费 core 层——core 文件 main 未动）。
- 环境注记：主检出 `sparkle-cosmos` 属另一宇宙（agent/node-b/T36/1，main ref=dc991183 任务包收官线），非本卡合并目标；本卡权威远端主线 = Sparkle-project main（e50107fe）。

## G｜limitations 10 条复核（派单靶 7）——**10/10 与代码事实一致（分支时点）**

重点亲验两处「未接线」：**#2** `friction_chat_wiring` :835 实证不传 `decision_context`（生产 chat 链 live 门出事实缺位，fail-closed 不命中口径如实）；**#3** 全仓无任何监听器调 `invalidate_on_source_withdrawal`（非测试零调用方），`retraction_recompute_service.py` 零 policy_patch/experience_strategy 耦合，`retraction.registered` 仅有 D03 生产方注册（event_registry :474）。#4（无 sweep/worker，TTL=120s 实证）、#7（现算审计面）、#8（precondition 词表 import 既有权威）、#9（record_id 去重+折叠边界）、#10（mypy 基线时点差——本审以 base=branch=merged 同清单实证分支零新增，补强该条）均与代码一致。#5 前提合并即过时见 C2。

## 挑战清单（R2 CHALLENGED，均非阻塞）

- **R2-C1（承接一审 C1，亲验成立）**：撤回 revoke 文档措辞「reason 入 transition_history」失实（规范码+actor+旁列三分）；建议合并前顺手改 `invalidate_on_source_withdrawal` docstring 与 diff_or_evidence_only.md 第 35 行区措辞。
- **R2-C3+（承接一审 C3，加 sharp）**：limitations/diff 文档补「旧行不回溯=存量重复引用行 admit 仍可照 V3 爬档（repeated），live 档补偿控制=观察面去重+收益门」一句。
- **R2-C5（一审 C5 复判不成立，改登记）**：重放审计对已失效行双向静默（非入 unaffected）；事件接线卡可选 already_revoked 分组。
- **R2-D1（新）**：candidate 态不进撤回 sweep 且 admit 不查撤回台账（人工入口不验证源真已撤回）——事件接线卡必须收口（sweep 纳 candidate 或 admit 前查台账），并显式声明入口信任契约。
- **R2-C4（维持一审）**：live 用户披露面/豁免决定列为 EXPERIENCE_STRATEGY_MODE=live 启用前置。

## 结论

实现、证据与二审对抗面全部独立复核通过：平票走保守侧、72h 窗边界无竞态复活、折叠×撤回复合语义干净、撤回身份链终态不可复活、A-05 单一权威未复制未绕过、合并落差以真实演练零冲突定案。裁决 **PASS_WITH_CHALLENGES**（R2-C1/C3+/C5/C4 承接改口 + R2-D1 新登记）；两位独立审查（R1 PASS_WITH_CHALLENGES + R2 PASS_WITH_CHALLENGES）齐，按验收模型可进入集成 SHA 复验与销账流程。R2-D1 为事件接线卡的硬性登记义务，不阻塞本卡。

reviewed_head: `4cac07ecaba214f1441b4de009c585487d078e5e`（实现头；branch tip 48dc5453 仅一审 receipt）
