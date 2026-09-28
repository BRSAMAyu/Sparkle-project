# V4-I03 二审 receipt（独立审查 R2）

- **审查会话**：wtI03R2（未参与 I03 实现与一审）
- **审查对象**：branch `agent/v4/i03`，HEAD `7a055e62`（实现 `ac6f9ae5` + pin `845751ce` + 一审 receipt `7a055e62`）；一审结论 PASS 已读，本审独立下判
- **审查日期**：2026-09-28
- **二审靶**（与一审互补，聚焦合并与生产落地面）：①合并落差预警 ②off/shadow/live 档位语义 ③对抗形态判定 ④对照落账幂等 ⑤零真模型红线 ⑥独立复跑 ⑦limitations/O 项定性复核
- **方法**：只读审查 + 独立复跑 + 独立探针脚本（`/tmp` 会话产物，未入库）；`git merge-tree --write-tree` 干跑合并面

## 0. 总裁决：**APPROVE（二审通过）**。CHALLENGED：**无**。

阻塞项 0；非阻塞观察 3 条（N-1/N-2/N-3，均移交下游消费卡 V4-I04/I07 与协调方），见 §8。双审齐（R1 PASS + R2 APPROVE），risk=high 的 2 份独立审查要求满足，待协调方按集成 SHA 复验流程销账。

## 1. 独立靶 1：合并落差预警 — ✅ 无阻塞（merge-tree 干净；串扰面零交叉）

分支基线 `f1e68517` 落后本地 main `001561c3` 24 个 commit（I01+I06 功能面、F01、FIX-558、I06 一审 C1 bypass 修复 `a9339621`、销账 state 提交）。逐面核查：

| 面 | 结论 | 证据 |
| --- | --- | --- |
| 文本冲突 | **零冲突** | `git merge-tree --write-tree main HEAD` → tree `5119111`、exit 0 |
| `settings.py` | 双方都加开关但 hunk 不相交（I06 `CONTEXT_SELECTION_RECEIPT_MODE` ~L931；I03 `SEMANTIC_SELECTOR_MODE` ~L959）；合并结果树中两开关并存且互不影响（亲读合并树） | ✅ |
| `standard_workflow.py` | **I06 完全未触碰**（`git diff f1e68517..main -- backend/app/agents/` 为空）；I03 的 router_node 影子钩子是唯一改动 → 无冲突 | ✅ |
| `tasks.json` | 双方改动落不同卡区（main @@749 F01/I01/I06 面 vs I03 @@879/@930）→ 自动合并 | ✅ |
| 迁移/生成文件 | I03 零迁移零生成物；I06 迁移 `i06_20260928_add_context_selection_receipts.py` 独立 → 无碰撞 | ✅ |
| **context 键串扰** | **零串扰**：I06 回执装配输入全部来自 `ContextPackBuilder.build` 内部观测（prefilter 结果、`metadata["memory_utility_gate"]`/`memory_selfcheck`/`preference_deny_quiet`），**不读 `context_data`**；I03 只写 `context_data["semantic_selector"]`/`["semantic_selector_mode"]` 两个名字空间隔离键。键面、存储面（I06=Postgres 表；I03=context_data+Prometheus）、metrics 面（互不重名）三重不相交 | ✅ grep+读码核实 |
| I06 C1 修复 `a9339621` | 只动 `context_selection_receipt.py` + 其 wiring 测试 → 与 I03 零重叠 | ✅ |
| D02 在航（wtD02，基 `56c3341c` 早于 I02） | 触 `settings.py`（删 I02 块 ~919-927）、`context_pack.py`、新 `attribution.py`——**不触 I03 任何面**；D02 与 I02 的 settings 块删改冲突是 D02 自己的合并债，与 I03 无关 | ✅ |

**合并建议**：①合并顺序无约束（I03 可先可后进 main，唯一债是 merge 后跑受影响面）；②集成 SHA 复验时在合并树上跑 77 + orchestration 208 + contract 304（覆盖 I06 冻结面）+ I09 面 300；③运维口径提醒：合并后 I03 默认 `off`（零行为），I06 默认 `shadow`（已在落库）——两卡默认态不对称，属各自卡面已如实声明的事实，非回归。

## 2. 独立靶 2：off→shadow→live 档位语义 — ✅ PASS（live 同义性有代码级保证；fail 面全封闭）

行为矩阵（独立探针逐项亲测）：

| 档位 | 行为 | 判定 |
| --- | --- | --- |
| `off`（默认） | 内层 `run_semantic_selector_shadow` 先判档返回 None；外层 router 门连 import 都不做——**零调用、零写入、零行为**（探针：off 后 ctx 两键全缺席） | ✅ |
| 未知值（`LIVE-TURBO`/None/空白） | `.strip().lower()` 归一后不在 {off,shadow,live} → 按 off + WARN（fail-closed 不猜），ctx 零写入 | ✅ 亲测 |
| `shadow` | 跑对照 → `context_data["semantic_selector"]`+`["semantic_selector_mode"]`+2 metrics；返回值被 router 钩子丢弃，钩子位于专家早退与 I09 快路早退**之后**、权威 `RouterNode` **之前**，try/except 包裹 → 物理上不可能改路由 | ✅ 亲测+读码 |
| `live` | **无独立代码路径**——与 shadow 走同一个 `run_arm_comparison`，mode 仅作为 `semantic_selector_mode` 元数据落账。探针：同一输入 shadow/live 产出 `to_dict()` **逐字段 byte-identical**，仅 mode 标记不同 | ✅ 亲测 |

**live 同义声明的代码层保证**：不是靠约定而是靠结构——本卡不存在 live 分支代码，live 的裁决语义只能由下游消费卡（I04/I07）新增读取路径才可能出现；当前全仓 `semantic_selector` 两键 grep **零消费者**（本次复审重核）。

**误配 fail 面（逐项亲测）**：
- live/shadow 下无 proposer（生产现状）→ 语义臂如实 `proposer_unavailable` 拒绝、`model_calls=0` 实测、agreement 恒 `not_comparable`——**不冒充有语义判定** ✅；
- 空干预白名单 → 一切选择首拍 `unknown_intervention` 拒绝（**fail-closed 非 fail-open**：缺配置的方向是全拒绝，不是全放行）✅；
- 白名单 ⊄ 契约词表 → `SelectionRequest.__post_init__` 构造期 ValueError（进不了运行时）✅；
- proposer 异常 → PROPOSER_UNAVAILABLE + tokens/usage_source=None 不冒充 ✅；
- 影子自身崩溃 → router 钩子 WARN 不阻塞路由（测试 `test_router_node_shadow_failure_never_breaks_routing` 钉死）✅。

## 3. 独立靶 3：对抗形态判定 — ✅ PASS（一审未测的 4 族 13 探针全走向「宁漏报回落慢路」）

| 对抗族 | 探针（一审未测） | 判定走向 |
| --- | --- | --- |
| **嵌套否定+目录外 tool 复合** | `并不是不喜欢…用 get_plan_state 查一下` + stub proposer 提 `rm_rf_slash` | 文本复杂性与 proposal 校验**独立路径**：multi_negation 照常命中，目录外 tool 照常首拍 `out_of_catalog_tool` 拒绝（repairs_used=0），拒绝话术零成功标记 ✅ |
| **超长消息（截断边界）** | 240KB 尾部嵌套否定 / `并不是不`×30000 / `还没`×20000 | **无截断丢判**（全文扫描，尾部命中）；病态重复串 4.5–6.3ms 无回溯爆炸；240KB 单轮 122.9ms（<0.03% 路由轮，仅 messages[-1] 一条）✅ |
| **中英混杂** | 英文否定+中文双否定同句 / 纯英文搁置 / `later 再说` | 中文结构单元照常命中（跨语言不干扰）；纯英文/英文时间词+中文「再说」不构成连续结构 → 不触发 → **漏报回落慢路** ✅ |
| **emoji/控制字符注入** | 零宽 U+200B、`\x00`、ANSI `\x1b`、RLO U+202E、emoji | 注入**在算子序列内部**（`不是\u200b不`/`并非\u200b没`）→ 结构断开 → 不触发（漏报安全向）；注入在**完整算子之后**（`并不是不🚫`）→ 算子已完整命中不受影响；尾部 RLO 不破坏 → 命中。全部走向与「拆任一算子即不触发」同机制 ✅ |
| **跨子句缓解（R2 新边界）** | `没有材料。不过不影响我继续` | 缓解词只在同子句作废——跨子句不撤销前子句命中 → material_insufficiency 仍命中 → 规则臂 CLARIFY（**过报方向=多问一次澄清，保守非危险**；本卡 shadow 只记录，零行为后果）。属 limitations §7 缓解词启发式同族，登记 N-1 |

本卡关键背景：探针/对照全部产物在当前卡内是**观测面**（零消费者），假阳假阴在本卡均无行为后果；「宁漏报」的硬约束真正生效点是未来 live 消费（I04/I07），届时须沿用「漏报=回落既有慢路」的方向。

## 4. 独立靶 4：对照落账完整性（存储面/幂等/重放） — ✅ PASS

- **落哪**：三落点——`context_data["semantic_selector"]`（随 Redis checkpoint 持久：记录为纯 JSON 值，checkpoint 序列化通过、不进 `KNOWN_NON_SERIALIZABLE_CONTEXT_KEYS` 告警面）+ 2 个 Prometheus 计数器 + 进程内记录对象。**无数据库表、无迁移**（与 I06 的 Postgres 落库形成对照，本卡落账面更轻）。
- **幂等性**：`comparison_id = sscmp_<sha256(version|text_sha|whitelist_digest)[:32]>` 内容寻址——同输入重放 id 恒定（亲测 `sscmp_8e7ee70c…` 两次一致），输入微变 id 随变（不碰撞）。与 D02 `derive_attribution_sample_id`（`attr_<sha256[:32]>`，重放恒同 id）**同一设计族**：下游若按 comparison_id 落库，天然重放幂等不虚增。
- **重放不虚增**：context_data 单键**覆写**不累积（亲测两次 shadow 后 ctx 键集仍恰为 2 个）；checkpoint 只存最新一份。Prometheus 计数器随重放递增——这是观测计数语义而非账目声明，不构成虚增。
- **隐私面**：记录只存 `input_text_sha256`，原文零泄漏（亲测全量 json dump 不含原文）；`matched_span` 只存算子级短片段。

## 5. 独立靶 5：零真模型声明 — ✅ PASS（费用红线核实）

- `semantic_selector.py` import 面：stdlib（hashlib/re/dataclasses/enum/typing）+ loguru + `aurora_decision` 词表 + metrics + `ExecutionMode`——**零 LLM 客户端、零网络、零 token_tracker 依赖**。
- 全仓 `SemanticProposer` 构造点 grep：**除协议定义与测试 `_StubProposer` 外零构造点**；生产影子钩子调用不挂 proposer → 语义臂恒 `proposer_unavailable`（`model_calls=0` measured，如实）。
- 本会话全部测试在无任何 API key 环境通过（LLMRouter 27 configs 无 key 注册）——若存在隐性真模型调用不可能全绿。

## 6. 独立靶 6：复跑 — ✅ 全绿（本会话独立执行）

| 面 | 结果 |
| --- | --- |
| `pytest tests/unit/test_semantic_selector.py -q` | **77 passed**（1.04s） |
| 冻结语料 23 条独立复核（直读 `probe_corpus_snapshot.json`，对活代码重算 expected/actual/rule_arm 三字段） | **23/23 零 mismatch** |
| `pytest tests/orchestration -q` | **208 passed**（46.75s） |
| mypy 棘轮（`scripts/ci/mypy_ratchet.sh`） | **71 / baseline 77**（≤ 基线零新增）；`semantic_selector.py` 自身全仓口径 **0 error**（limitations §8 亲证） |
| R2 独立探针 31 项（A/B/C/D/E 五族） | **31/31 PASS**（B4a 首测 FAIL 为探针自身构造偏靶——零宽字符插在完整算子之后而非内部；修正靶位后 3/3 PASS，正文 §3） |

环境：`SECRET_KEY=ci-test-key DATABASE_URL=sqlite://`，worktree `.venv`（python 3.11.15），与 run_manifest 声明一致。

## 7. 独立靶 7：limitations 9 条与一审观察 3 条定性复核 — ✅ 全部成立

- **9 条 limitations 逐条复核**：§1 零真模型（本审 §5 独立核实）、§2 保守结构面（本审 §3 对抗探针反向证实：未预见形态全落漏报安全向）、§3 agreement 无基线（生产影子恒 not_comparable，亲测）、§4 影子白名单保守最小集（读码证实且空/缺配置 fail-closed）、§5 live=shadow 同义（亲测 byte-identical）、§6 语料自造 23 条（结构核实）、§7 缓解词启发式（本审 §3 补充跨子句同族边界）、§8 mypy 平台差 71（本机复跑同值 71/77，改动文件零错误）、§9 审查待发生（本 receipt 即其闭环）。**无一条夸大或失实。**
- **O-1（语料双份维护静默漂移）**：成立——快照 json 仍零测试消费者（grep 重核）；本审独立复核当前两侧一致。移交建议（测试直读快照或重算 diff）维持，归 I04/I07。
- **O-2（`_RULE_DECISION_TO_INTERVENTIONS` 硬编码干预名）**：成立——L755-761 仍是字面量、无 import 期不变式；影响限于影子 agreement 指标偏斜（运行时白名单仍硬拒越权）。移交建议维持。
- **O-3（FakeRouter 断言边界）**：成立——结构保证（只写两个零消费键）本审重核仍真；「钩子键集 ⊆ {semantic_selector, semantic_selector_mode}」冻结断言建议维持，归 I04/I07 挂消费时落地。

## 8. 二审非阻塞观察（不阻塞合并，移交下游/协调方）

- **N-1 跨子句缓解边界**：缓解词只在同子句作废，`没有材料。不过不影响…` 类跨子句形态会命中 material_insufficiency（过报方向=规则臂多问一次澄清）。本卡零行为后果；I04/I07 接线消费规则臂判定时应知悉该边界（可在消费卡词表评审时决定是否扩缓解词辖域到邻接子句）。
- **N-2 live 档缺运行时「只记录」信号**：live 与 shadow 的同义性靠结构保证与文档声明（settings 注释/limitations §5/`semantic_selector_mode` 落账），但 live 下无独立的启动 WARN 或 metric 维度提示操作者「本卡 live 不裁决」。I04/I07 接管 live 裁决语义时应加消费侧显式标识，避免运维误读。
- **N-3 影子记录随 checkpoint 持久**：`semantic_selector` 两键为 JSON 安全值，随 Redis checkpoint 进会话档（单键覆写不累积）。无敏感性（仅 sha+判定+冻结文案），但 I04/I07 设计消费面时应知道记录会随会话恢复存活。

## 9. 结论

- **卡验收三条**：①不单关键词误判（机制=多 token 结构单元+去算子翻转+对抗探针证实）、②未知 ref/目录外 tool 拒绝零成功话术（复合对抗下仍首拍硬拒）、③双臂对照判定/成本/失败形态全留档（内容寻址幂等、重放不虚增）——**全部成立**。
- **合并落差**：merge-tree 干净、零文本冲突、与 I06/C1/D02 零语义串扰（§1 清单）。
- **档位语义**：off 零行为可失败（一审变异+本审行为矩阵）、shadow 永不改路由、live 本卡与 shadow 结构性同义、误配全 fail-closed。
- **费用红线**：零真模型路径全仓核实。
- **复跑**：77 + 23/23 + 208 + mypy 71/77 全绿（本会话独立执行）。
- **总裁决：APPROVE**；CHALLENGED 无；N-1/N-2/N-3 非阻塞移交。高风险卡双审齐备，待协调方在集成 SHA 复验后销账。
