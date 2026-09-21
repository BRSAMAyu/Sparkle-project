# X-10 · Action Engine E2E Evaluation — REPORT

> Stream=ACTION ｜ Gate=V3-5 ｜ risk=medium ｜ lock=action-eval ｜ 2026-09-21
> Base SHA：`8c769eaf`（含 X-07）｜ Final SHA：见 `changes.patch` 头（本卡全部为新增文件，未改既有代码）
> 状态：**READY_FOR_REVIEW**

---

## 0. 一句话结论

77 个 allocation/action 场景（≥60 达标）+ GJ04-07 四条 golden journey 全部在**真实服务层 + 真实 DB schema**上跑通，六元组（decision/execution/result/outcome/latency/cost）全量记录，判定器对 DB 真相独立复算：**allocation 达标率 100%（28/28）、high-risk auto=0、false success=0**；无人值守一键完成核心 case 集，开发者零介入。

---

## 1. 交付物

| 产物 | 路径 | 说明 |
|---|---|---|
| 场景集（单一事实来源） | `backend/tests/fixtures/x10_action_e2e_scenarios_v1.json` | 77 场景，封闭 schema + expected 封闭键集（gate 测试冻结） |
| 评测模块 | `backend/tests/v3_action_eval/` | `scenario_schema` / `dbfixture` / `executors` / `verdicts` / `runner` 五件套（Q-01 三路由同款模块纪律） |
| gate 测试（判定器单测） | `backend/tests/v3_action_eval/test_x10_action_eval_gate.py` | 12 测试：3 结构守卫 + 7 **变异红证** + 2 真实端到端抽检 |
| 无人值守脚本 | `scripts/devtools/x10_run_action_e2e_eval.py` | 一键全量 → `results.json` + `EVAL_RESULTS.md`，acceptance 不绿 exit≠0 |
| 机读结果 | `v3-output/X-10/results.json` | 全量六元组 + 逐场景判定 checks（891 条，全留痕） |
| 场景矩阵报告 | `v3-output/X-10/EVAL_RESULTS.md` | 逐场景表 + 覆盖矩阵 + 失败清单（本轮空） |
| 本报告 | `v3-output/X-10/REPORT.md` | |
| 补丁 | `changes.patch`（worktree 根） | |

复现：

```bash
cd backend && SECRET_KEY=test .venv/bin/python -m pytest tests/v3_action_eval/ -q   # gate + 判定器单测
backend/.venv/bin/python scripts/devtools/x10_run_action_e2e_eval.py               # 全量 77 场景无人值守
```

---

## 2. 评估口径（对齐 `v3/05_metrics_eval/EVAL_PROTOCOL.md`）

- **层位**：L1 deterministic tests 与 L3 simulator journeys 之间的**真实服务层闭环**——每场景走真实 `ActionCommandService` / `AgentRunService` / `TaskService` / allocation policy / outcome capture+ledger，DB 为真实 ORM schema（sqlite aiosqlite 内存引擎 + 真实迁移产物 `Base.metadata` + outbox 两表；与既有 run/proposal 测试同一 fixture 形态）。**无模拟器/无浏览器/零 gradle**（资源纪律：本机 16G 内存下唯一 HEAVY 亦为纯 CPU 轻载）。
- **禁止 mock 冒充的落实**：领域逻辑零 mock；mocks/确定性边界只存在于（a）LLM 边界——allocation 语义层默认关闭（`SPARKLE_ALLOCATION_SEMANTIC_ENABLED=False`，全轮 `real_llm_calls=0` 被判定器强制断言）、（b）事件总线——`EVENT_BUS_MAX_RETRIES=0` 只去退避 sleep，publish 失败语义不变（总线是 best-effort 广播，账本读模型才是真相面）、（c）时钟注入——过期场景回拨 `expires_at`（与真实 sweep 同一谓词）。
- **判定独立复算**（EVAL_PROTOCOL §2「不允许模型自评作为唯一证据」的确定性版）：判定器**不信执行器自述**——用独立 DB 会话重读真相行（task/proposal/run/transition/outbox/账本），用纯函数（`decide_allocation` / `decide_authorization_mode` / `run_steps_wire` / `awaiting_step_projection` / `RUN_RECEIPT_OUTCOME_POLARITY` / `build_task_outcome_capture`）重算预期再比对。执行器输出只是六元组的记录面，不是证据面。
- **判定器有效性证明（防「全绿失明」）**：gate 测试含 7 组变异红证——错 mode 谎报、高风险 auto 谎报（点亮 `high_risk_auto` 全局旗标）、COMMITTED 假成功（DB 真相 PENDING + 无 receipt）、双 resume 幂等破坏、run 极性谎报（FAILED→positive）、LLM 成本泄漏、意外异常——判定器全部判红。**77/77 全绿不是判定器失明。**
- **Repetition**：全场景确定性（纯服务+固定 fixture，无随机模型路径），按协议 §3 以「同场景复跑判定稳定 + decision_id 逐字节一致」替代多次采样（gate 测试钉住）。
- **Regression**：ACTION 链既有守卫全量复跑绿（§5），未发现本卡引入回归。

---

## 3. 场景矩阵与六元组统计

### 3.1 家族矩阵（77 场景）

| family | n | pass | fail | error | 覆盖面 |
|---|---|---|---|---|---|
| allocation | 28 | 28 | 0 | 0 | 八维分配因子 ×22 mode target + 6 供给 vetting（G3/G4/R1/R5/E2） |
| authorization | 10 | 10 | 0 | 0 | auto 授权服务路径 ×3、纯函数规则 ×4、commit 门 fail-closed ×3 |
| proposal | 12 | 12 | 0 | 0 | commit/receipt ×2、幂等 ×3、终态封闭 ×3、TTL 过期 ×2、乐观并发 ×1、输入校验 ×1 |
| run_steps | 13 | 13 | 0 | 0 | 计划契约 ×2、owner 纪律双向 ×2、显式交棒 ×1、幂等 resume ×3、冷启动恢复 ×1、取消/过期 ×2、resume 白名单 ×1 |
| outcome | 10 | 10 | 0 | 0 | 真相分级 ×3、focus 覆盖率 ×2、失败保留 ×1、PARTIAL 不升格 ×1、receipt 极性 ×1、幂等 id ×1、事件内容纪律 ×1 |
| journey | 4 | 4 | 0 | 0 | GJ04-07 全覆盖 |

### 3.2 六元组统计（每场景全量记录于 `results.json`）

- **decision**：allocation 场景记 `AllocationDecision` 全量（mode/why 封闭词表/confidence/feasible set/审批与证据旗标 + `decision_id`）；action 场景记服务端授权决策（`proposal.authorization`）；run 场景记步骤计划（owner/完成条件）；journey 记分配→授权→交棒决策链。
- **execution**：184 次真实服务操作，逐操作留痕（op/ok/error/elapsed_ms），含 4 条旅程的全部相位序列（如 GJ07 十二步：task_start→create_run→…→user_confirm_resume→user_confirm_replay→agent_check→succeed→approve→ledger_query）。
- **result**：终态真相（proposal status/receipt、run status/terminal_reason/result_ref、task status/actual_minutes、完成戳与幂等键）。
- **outcome**：capture 极性（POSITIVE/NEGATIVE/NEUTRAL）+ 账本 truth_class（actual/self_reported/unknown）+ 证据附着（pipeline_echo / agent_run:// 独立证据）。
- **latency**：总 25,159 ms（77 场景服务层墙钟），均值 326.7 ms，max 604.5 ms；家族分布 allocation 7,969 / authorization 3,225 / proposal 4,145 / run_steps 3,766 / outcome 4,086 / journey 1,966 ms。旅程单条 ≤505 ms（GJ04 505.4 / GJ05 466.3 / GJ06 494.4 / GJ07 500.2）。
- **cost**（O-07 cost 面的确定性下界）：**真实 LLM 调用 0 次、0 token**（强制断言）；服务操作 184 次；DB 事务与操作数逐场景在册（`cost.service_ops` / `db_transactions`）。评估本身零推理成本；生产成本面由 O-07 `sparkle_cost_per_wvpl` 等指标承接，本卡为其提供 run/outcome 关联点（`run_id`/`correlation` 已全量在案）。

### 3.3 判定强度

全轮共执行 **891 条独立判定 check**，其中 25 条为结构性不变式（按因子动态重判，与 fixture 标签无关），全部通过；每条 check 携带 expected/actual 留痕可审计。

---

## 4. Acceptance 映射

### ① allocation ≥90% target；high-risk auto=0；false success=0 — **全部达标**

| 断言 | 结果 | 证据 |
|---|---|---|
| allocation ≥90% target | **100.00%**（28/28；mode target 22/22，offer guard 6/6） | `results.json` `summary.allocation`；既有 X-02 盲评守卫 `test_action_allocation_eval.py`（112 测试）同轮复跑绿 |
| high-risk auto=0 | **0** | 高风险不变式覆盖 5 个 allocation 场景（high/critical/medium×不可逆）+ 授权面 `requires_human_approval` 永不 auto + GJ06 高风险 run 必经 `AWAITING_APPROVAL` 才可 resume（run 面无审批直通）；变异红证证明谎报必被抓 |
| false success=0 | **0** | 「声称成功 ⇔ 服务端真源确证」逐场景强制：COMMITTED ⇔ receipt 在 + 命令域副作用落库；SUCCEEDED ⇔ run 终态行 + result_ref receipt；outcome POSITIVE ⇔ 任务真 COMPLETED / NEGATIVE ⇔ 真 ABANDONED；PARTIAL→NEUTRAL 永不升 positive、永不升 actual（X-08 语义） |

### ② Simulator（场景运行器）无需开发者介入完成核心 case — **达标**

- `scripts/devtools/x10_run_action_e2e_eval.py` 一键无人值守：自动建 77 个独立真实 DB 上下文、真实服务层执行、独立判定、写 `results.json` + `EVAL_RESULTS.md`、acceptance 不绿 exit≠0；全程无手工步骤、无环境特调（`SECRET_KEY` 走 env 默认注入，worktree 无 .env 依赖）。
- 判定全自动：判定失败/异常降级为 fail/error 并留 full checks 痕迹，不需要开发者解读。

---

## 5. 既有测试基线复跑（回归面，全绿）

| 批次 | 测试 | 结果 |
|---|---|---|
| 本卡 gate | `tests/v3_action_eval/` | 12 passed |
| allocation（X-02） | `test_action_allocation_policy/eval/guard` | 112 passed |
| command path（X-03/X-04 契约） | `test_action_command_service / test_action_proposals_api / test_action_plan_contract` | 74 passed |
| run steps（X-07） | `test_hybrid_run_steps(_api) / test_run_step_projection / test_x07_run_steps_migration_sqlite` | 30 passed |
| outcome（X-08/D-02） | `test_x08_outcome_capture / test_x08_outcome_ledger_gj / test_outcome_ledger_contract` | 58 passed |
| action flow/execution/budget/tool（X-04/X-05b/X-06） | `test_x04_action_flow / test_x05b_e2e_execution_projection / test_x06_run_budget / test_x06_tool_call_safety` | 83 passed, 1 skipped（既有 skip） |

---

## 6. 失败/低分 case 清单与根因分类

**本轮全量轮：0 失败 / 0 error（77/77）。** 按卡面「保留失败 case」要求如实说明：

- 开发过程中曾被判定器抓住并修复的 4 类问题（作为判定有效性的过程证据，非最终失败）：
  1. **判定器口径错误**（非被测系统缺陷）：vet-only 场景误套 mode target、`OutcomePage.items` 属性名错、步骤 id 硬编码——修正判定器；
  2. **场景构造违反真实 FSM**：GJ04 从 STUCK 直接 complete（FSM 无此边）、GJ06/07 从 PENDING 提案 complete（`PENDING→COMPLETED` 非法）——按真实产品语义改为 rescope→resume→complete 与 task 先 start；
  3. **fixture 期望与真源语义相悖**：o06 期望 ABANDONED「不升 actual」，与 X-08 设计语义（放弃是服务器记录的负向事实：`ACTUAL + NEGATIVE`，结构性不可点亮）相悖——修正期望为真源语义；
  4. **词表大小写/枚举值**：`AgentRunKind` wire 值为小写 `execution`、授权 reason codes 为小写。
- 低分 case：无（无场景落在 0.6–0.9 灰区；allocation 二值命中，confidence 分布见 results.json `decision.confidence`）。
- 若后续轮次出现失败，`EVAL_RESULTS.md`「失败 case 清单」按 根因=被测缺陷/判定器缺陷/场景构造缺陷 三类登记（本轮判定器与场景构造缺陷均已收敛归零）。

## 7. 观察与发现（诚实申报，非本卡 acceptance 项）

1. **`await_user_step` 不校验被交棒步骤的 owner**：编排层误用 `await` 交棒 agent-owned 步骤时，服务层会进入 `AWAITING_USER`（完成侧 owner 纪律守卫仍在，用户无法替 agent 盖戳，故无越权后果，但 run 会卡在等待）。场景 `run_r05` 以对抗性误用实证了完成侧守卫。建议后续在 await 入口补 owner∈{human, hybrid} 校验（一句话改动，属 X-07 面增量，本卡不越锁改动）。
2. **GJ06/GJ07 的审批门/交棒为编排层显式语义**：run 状态机不自动进 `AWAITING_APPROVAL`/`AWAITING_USER`（X-07 验收备案 A 的「编排层显式 await 交棒」语义），本卡场景按该语义构造并通过；产品 UI 侧的发起责任由 U-04 交互族承接。
3. **事件总线在无 Redis 环境为可观测降级**（log 告警 + 返回 None）：与「账本读模型是真相面」的设计一致，本评测的判定全部落在 DB 真相，不依赖事件投递。

## 8. 诚实申报（边界与限制）

- **DB 为 sqlite 内存引擎**（真实 ORM schema + 真实服务层），非 PG：`FOR UPDATE` 行锁在 sqlite 下 no-op（与既有全部后端测试同一限定），并发恰一性由复查+唯一索引兜底——五路并发级压力不在本轮口径（X-07 验收已在真实 PG 实证过并发 resume，本卡未重复）。
- **零真实 LLM、零真实模型路径**：allocation 语义层关闭；语义灰区的真实 LLM 增益属 L2 离线评口径（X-02 REPORT 已申报 ≤5 次冒烟预算），本卡不覆盖。
- **「无需开发者介入」指场景运行器（脚本+服务层闭环）**，非移动端 GUI 自动化——卡面场景 simulator 定义即后端场景运行器，移动端交互面由 U-04 组件测试（26 个）与各端 journey 标记承接。
- **evaluation 的 latency 是服务层墙钟**（进程内调用，无网络/网关跳数），不代表端到端产品延迟。
- **未 commit/push**（资源纪律）：全部改动以 `changes.patch` 交付，收工后由主会话合入。

## 9. 资源纪律执行申报

- 主仓与 wt61 只读（仅读取过 wt61 `app/gen` 存在性用于核对 proto 一致性；后经哈希比对确认 proto 全同后，用本 worktree venv 的 grpc_tools 自行生成 `backend/app/gen`，未改动生成产物本身）；
- 未 commit / 未 push；构建产物仅 `backend/.venv`（worktree 内，随 worktree 回收）与 `/tmp` 评测探针（收工自清）；
- 全程零模拟器/零浏览器/零 gradle；pytest 串行分批（≤6 批），批间 swap 巡检（最低 1,025 MiB，未触 1G 停止线）。
