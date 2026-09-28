# V4-I05 · 独立审查 R1 receipt（wtI05R1）

- 审查会话：wtI05R1（独立，未参与 I05 实现）；高风险卡一审（需 2 位）
- 审查对象：`agent/v4/i05` @ `4cac07ecaba214f1441b4de009c585487d078e5e`（base `ff02ec03419c54cb40cc05128ff110277f8bbb9f`，merge-base 复核为直接父子）
- 审查日期：2026-09-28（UTC 16:39）；工作树复核零残留（全部探针/突变 `git status` 干净）
- 环境：`SECRET_KEY=ci-test-key DATABASE_URL=sqlite://`，python 3.11.15（main checkout 共享 venv）、pytest 9.0.2、mypy 1.20.2、ruff 0.15.8、black 26.3.1（darwin arm64）

## 总裁决：PASS_WITH_CHALLENGES

R1-R5 预登记审查点全部独立复核通过；shadow 零行为红线经**审查者亲做双突变**（admission 档 + off 档，实现方自证只覆盖 decision 档）反转变红实证成立。挑战 5 条均为**文档口径/披露面级别**（C1-C5，见文末），不涉行为正确性、不阻塞一审通过；C1/C2 建议二审前顺手修正证据文档。

## R1｜shadow 零行为红线（最重）——**PASS（亲做突变红证）**

实现方自证的突变仅覆盖 decision 门出档（`patched_decision_inputs`）。按预登记 R1 本审查亲做 **admission 档突变**：

- 突变 M1（admission 收益门在 shadow 生效）：`admit_evidence` 中 `strategy_mode == STRATEGY_MODE_LIVE and may_auto_activate(...) and verdict != BENEFIT_OBSERVED` → `strategy_mode != STRATEGY_MODE_OFF and ...`。复跑服务套件：**1 failed / 16 passed**，FAILED 恰为 `TestLiveBenefitGate::test_shadow_mode_observes_but_activation_unchanged`（shadow 下 no_benefit 仍 active 被打破）→ 红证成立。还原后 17/17 绿，`git status` 零残留。
- 突变 M2（off 档 V3 断言可失败性）：`admit_evidence` 自动激活处 `if strategy_mode == STRATEGY_MODE_LIVE: self._apply_live_window(...)` → 恒真。复跑：**1 failed / 16 passed**，FAILED 恰为 `TestLiveBenefitGate::test_off_mode_activation_has_no_bounded_window` → off=V3 逐项钉死断言可失败性成立。还原后绿。
- decision 档红线（加严形态，`test_shadow_payload_identical_to_off_byte_for_byte`：门出情境事实在场时 shadow 载荷与 off canonical JSON 逐字节恒等）本审查审读断言强度成立：比较面覆盖 nominated/applied ids/policy version/因子/归因全载荷；任一 shadow 偷跑 live 门出的实现必然翻红（与实现方反转变红记录口径一致）。
- 默认档核验：`settings.EXPERIENCE_STRATEGY_MODE: str = "shadow"`（settings.py +972 区），未知值 `resolve_strategy_mode` fail-closed 按 off（单测参数化×6，live 只认字面 `"live "` 容忍）。shadow 档 admission/decision 仅新增观察（指标 + 结构化日志）与一次只读投影，**零输出差量**。

## R2｜live 三边界——**PASS（一正一反亲跑）**

审查者自写独立探针 6 例（fresh 场景：explain/project 域，与卡测 practice/exam 域不同源；探针用后即删），全绿：

1. 收益门负向（1 正 3 负，live）：admit 后停 evidenced（扣下不静默激活）；显式 `confirm_patch` 后 active——确认路径合法保持。正/负双向参数化通过（3 正 1 负 → active + `expires_at == now+72h`）。
2. 有界窗收敛（live）：激活后 +71h 仍在 effective 集、+73h 排除；`effective_patches` 读时顺手将行收敛为 `expired`（无无限期 live——结构上被 72h 缺省窗排除）；`expire_sweep` 幂等（剩余 0）。
3. 窗口回滚面：`EXPERIENCE_STRATEGY_LIVE_WINDOW_HOURS=0` → 激活不带窗（有界化可关）。
4. live confirm 亦补窗：no_benefit 扣下后显式确认激活，`expires_at = now+72h`（用户确认的策略同样有界）。
5. decision 面负向：live + `human_required_step=True` → `applied_patch_ids == ()`、提名回 V3 基线序、`do_not_apply_human_required_step` 进指标；正向：无门出事实 → 正常应用且 practice/explain 升首。
6. shadow/off 对照、censored 显式不结论、负向等权（平手/反超 = no_benefit）由 73 测复跑覆盖（见复跑节）。

**I07 掌握门结构性不绕过核**：六面 payload 键集 `SURFACE_PAYLOAD_KEYS` = adjustment/mode/style/intervention/cadence/preference（+direction）——`human_required` 不是可 patch 键（V2 未知键拒绝）；I07 `hybrid_policy` 的 `BLOCK.agent_completed_human_required_mastery` 模块零改动；本卡零新增应用通道（唯一应用面仍经 A-02 `evaluate_intervention_policy` 既有守卫，friction_chat_wiring :835 调用链审读确认）。策略面门出（live 过滤 allowed 集）与结构性守卫双保险成立。

**R2 附带评估（用户披露面缺失）**：live 档的扣下/门出可见性 = WARN 日志 + Prometheus 指标，均为**运维面**；终端用户面无「策略因无收益被扣下/因 human_required 被门出」的显式披露（`policy_patch` 注解只含 applied ids）。默认 shadow 下无用户可见行为变化，故本卡可过；**任何 live 灰度启用前应补用户披露面或将其列入启用前置**（进 HUMAN_INBOX/启用门槛，见 C4）。

## R3｜签名/缓存键变更（实现方称零消费者）——**PASS（全仓复核属实）**

- `revoke_patch` +`actor` 参数（默认 `"user"`）：全仓 grep 生产代码，唯一调用方 = 新增 `invalidate_on_source_withdrawal`（policy_patch_service :696，actor=`evidence_withdrawal`）；零 API/gateway/proto/orchestrator 消费者（gateway 的 revoke 路由为 community/marketplace 无关域）。既有 A-05 测试 5 处调用均走默认 actor → 零行为变化（A-05 39 测复跑绿实证）。
- 策略档位进 `_inputs_cache_key`：键为进程内 LRU 私有格式，键加字段 = 模式切换立即失效旧键，无外部消费者读键形。`patched_decision_inputs` 生产调用方唯一 = `friction_chat_wiring._decide_intervention`（不传新可选参 `decision_context`，签名兼容）；`context_cache_key.py` 消费 `policy_version`（未改语义）。120s TTL 与「存储版本一致」命中条件未动。

## R4｜折叠兼容——**PASS（旧行向后兼容亲测）**

- 服务层同身份：propose 入口先 `fold_evidence_refs` 再 `derive_policy_patch_id` + 落库 → [a,a,b] 与 [a,b] 同 patch_id、同 evalver（服务级亲证；注意核 `derive_policy_patch_id` **本身不折叠**——身份等价在服务入口折叠点成立，纯层测试 `test_evaluation_version_content_addressed` 钉的是折叠后输入的恒等）。
- 旧行兼容（审查者自写探针，用后即删）：手工插入 pre-I05 形态行（存重复 refs [a,a,a]、unfolded 派生 id）→ 该行零触碰、字节不变；同内容新提议得折叠 id ≠ 旧行 id → 两行并存、零碰撞、零数据丢失；`_verify_evidence` 按存储 refs 逐条解析 → 旧行档位**不回溯**（重复引用的既有档位行为保持 V3）。
- 边界声明评估：「旧行档位不回溯」是 propose 时点折叠的结构性后果，证据文档以「propose 折叠」隐含表达但**未逐字声明**（见 C3）；limitations #9 的 record 级去重声明与实现一致（`observation_face_from_records` 按 record_id 去重）。

## R5｜撤回传播 + 事件「同批接线」声明——**PASS（声明如实）**

- D03 strategy 面消费：`strategy_withdrawal_plan` 复用 `plan_recompute`（face=`DerivedFace.STRATEGY`，精确 `SourcePointer` 二元组身份）；`CANDIDATE_FACES_BY_KIND` 三类撤回均含/收窄 strategy 面（material_deleted/result_retracted 全面、inference_retracted = insight+strategy），import 期断言钉住。命中 revoke（actor=`evidence_withdrawal`）、unaffected 显式保留、三档一致（off/shadow/live 参数化）。
- 审查者独立探针（用后即删）：decision 源 + `inference_retracted` → 命中失效、replay 幂等（二次 affected=[] 且 version_before==version_after）；跨用户隔离（同源 id 不同用户互不波及）通过。
- **事件监听未接线声明属实**：`retraction_recompute_service.py` 全文零 policy_patch 耦合；`retraction.registered` outbox 事件生产方存在（D03），无任何监听器调 `invalidate_on_source_withdrawal`——当前生效方式 = 显式服务调用，与 limitations #3 口径一致。main 侧 D04 已接线的是 galaxy 图面缓存失效（`invalidate_galaxy_graph_view_cache`），策略失效监听缺口**在合并后依然存在**（同批接线承诺的兑现对象后续卡）。
- SourcePointer 域命名冻结：`source_pointer_of_ref` 域名（`expmem_record`/`decision_evidence`）与 id 形态（`expmem_+16`/`aurora_+32`）和 A-05 `policy_patch` 证据 ref 封闭 scheme 逐一对应；单测 `test_source_pointer_round_trip_and_rejects_garbage` + 跨域不同域反例钉死具体域名字符串（改名即红）。

## 复跑（全部审查者亲跑，fresh 口径）

| 组 | 命令 | 结果 |
|---|---|---|
| 本卡 73 | `pytest tests/unit/test_experience_strategy.py tests/services/test_experience_strategy_service.py -q` | **73 passed** |
| I04 39 + I03 77 + A-05 39 + D03 34 | 同上 + `test_no_action_supplement.py` + `test_semantic_selector.py` + `test_policy_patch_service.py` + `test_retraction_recompute.py` + `test_retraction_recompute_service.py` | **262 passed**（73+39+77+39+34，与卡面抽组口径一致） |
| 其余受影响面 | `test_memory_utility_gate(25)+wiring(9)+friction_chat_wiring(76)+experience_memory_projector(22)+attribution(38)+hybrid_policy(31)+intervention_lifecycle(36)` | **237 passed**（合计 499 绿） |
| ruff（6 改动文件） | `ruff check <changed>` | All checks passed |
| black（4 改动文件，120） | `black --check <changed>` | 4 files unchanged |
| mypy 棘轮（**rm -rf .mypy_cache 后**） | `bash scripts/ci/mypy_ratchet.sh` | **59 / 77, exit 0**（与实现方 fresh-cache 口径一致） |
| mypy 改动文件直查 | `mypy app/core/experience_strategy.py app/services/policy_patch_service.py` | 两文件本体 **0 error**（直查连带报的 33 条全在传递 import 的既有模块，非本卡文件） |
| main@3b96039f fresh-cache mypy | `mypy app --cache-dir=/tmp/...`（main checkout） | **59**——合并后棘轮 59≤77 仍成立 |

模型调用：0（全部纯函数/sqlite 隔离生产路径；审查过程无任何真实模型调用）。

## limitations 10 条如实性核对

逐条对照实现与代码：#1（相关性计数可解释规则）#2（chat 侧 decision_context 未接线——`friction_chat_wiring` :835 实证不传）#3（撤回监听未挂——上文 R5 实证）#4（无在线 watch sweep——无 cron/worker 新增，回退=用户 revoke+72h 窗）#5（零 galaxy 写路径——grep 零命中）#6（I06 receipt 零消费）#7（shadow_report 现算不缓存；120s 决策缓存含档位——`INPUTS_CACHE_TTL_SECONDS=120` 实证）#8（precondition 词表 import 既有权威）#9（record_id 去重 + 折叠边界）#10（mypy 59 vs I04 55 基线时点差）——**10/10 与代码事实一致**。两处「未接线」（#2/#3）登记口径如实、未淡化。

## 合并落差预判（base ff02ec03 vs main 3b96039f，14 commits）

- 交集文件：main 侧改 `retraction_recompute_service.py`（D04 消费接线：galaxy 缓存失效 + epoch 栅栏 + 读门世代比对）与 `tasks.json`。I05 **零改动**前者（纯消费 `core/retraction_recompute`，该 core 文件 main 未动）→ 无语义/文本冲突。
- `tasks.json`：main hunks 在 653-717/1648-1718 区（D03/F05 条目），I05 hunk 在 1049 区 → 不重叠，可自动合并。
- 语义落差：**limitations #5 前提合并即过时**——main 上 D04 已 `DONE_REVIEWED`，「D04 未启动/tasks.json PENDING」的表述需在合并后改为「D04 已落地，本卡零 galaxy 写路径、VERIFIED 通道由其承接」（实质声明不变，见 C2）。`retraction.registered` 已入 event vocabulary（40→41），本卡零事件新名，无冲突。
- mypy：main@3b96039f fresh-cache = 59 → 合并后棘轮不回退。

## 挑战清单（CHALLENGED 项，均非阻塞）

- **C1（文档口径，建议修正）**：diff_or_evidence_only.md 与 `invalidate_on_source_withdrawal` docstring 称撤回 revoke 的「reason=`evidence_source_withdrawal` 入 transition_history」；实测 transition_history 末条 reason 为词表内规范码 `T4.revoked_by_user_correction`（actor=`evidence_withdrawal`），具体理由串在 `revoke_reason` 旁列。审计可区分（actor+旁列），但「入 transition_history」措辞失实，且 T4 码字面含 "by_user_correction" 对系统主体撤回略有误导——A-05 核心词表零改动是既定取舍，建议文档改口（如需码面精确可在后续卡 bump 词表，非本卡义务）。
- **C2（合并即过时的前提）**：limitations #5「D04 未启动（PENDING）」在合并 main 后失实（D04 DONE_REVIEWED）；实质声明（本卡零 galaxy 写路径）不受影响，合并时需顺带改写该条前提。
- **C3（边界未逐字声明）**：「旧行（存重复 refs）档位不回溯」「legacy 行 patch_id 保持 unfolded 派生、同内容重提议将并存新行（幂等去重不再命中旧行）」为实测属实的结构性边界，建议补进 limitations 或 diff 文档一句，避免未来读者误以为折叠对存量数据有回溯语义。
- **C4（live 用户披露面缺失评估，R2 预登记项）**：live 档扣下/门出仅运维可见（日志+指标），无终端用户披露面。默认 shadow 下可接受；建议将「用户披露面或其豁免决定」列为 EXPERIENCE_STRATEGY_MODE=live 启用前置（HUMAN_INBOX/启用门槛），不阻塞本卡。
- **C5（审计标签语义，记录即可）**：`invalidate_on_source_withdrawal` 幂等重放时，上一轮已 revoke 的行会出现在本轮 `unaffected_patch_ids`（「本轮未受影响」事实正确，但标签易被审计消费者误读）；version_before==version_after 可证幂等。后续事件接线卡可改为显式 `already_revoked` 分组。

## 结论

V4-I05 实现、证据与预登记审查点（R1-R5）全部独立复核通过；shadow 零行为红线的可失败性经审查者亲做双突变（admission 档为实现方未覆盖的新突变面）实证；live 三边界、撤回传播、折叠兼容、签名/缓存键零消费者声明均成立。裁决 **PASS_WITH_CHALLENGES**（C1-C5）；待 R2 独立审查后按验收模型收口。

reviewed_head: `4cac07ecaba214f1441b4de009c585487d078e5e`
