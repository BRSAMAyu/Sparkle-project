# X 线（Action，10 卡）深挖章 —— V3-COMPLETE-STATUS-FOR-V4 §4 素材

> 作者：wt770（文档深挖）｜基线：main@ce9846a3（2026-09-28）｜方法：卡面 + `git log --grep` 逐卡定位 → 读现势代码核实 → 目标测试在 worktree 实跑 → REPORT/RECEIPT/FIX 台账抽读。
> **本章事实判据**：所有 SHA 均已在 main 可达（`git show` 亲验）；运行级证据 = 本 worktree 实跑（§2.0）；「真模型 vs demo」逐处标注。
> 本轮新登记：**V3-FIX-502**（M/X 线卡级 receipt 断链——X-03..X-09 在列）与 **V3-FIX-503**（M-09 真模型复验，涉 X 侧引证）见 §5；另有多项已在册残差汇总于 §4。

## 0. 逐卡验证口径（本章通用）

- **实跑验证（2026-09-28，worktree wt770-docmx = main HEAD）**：X 线核心测试 403 用例全绿——
  `test_action_plan_contract + test_action_allocation_policy + test_action_allocation_guard + test_action_allocation_eval` = 141 passed；
  `test_action_command_service + test_agent_run_service + test_run_state_machine + test_hybrid_run_steps + test_failure_semantics + test_x09_failure_recovery + tests/v3_action_eval/test_x10_action_eval_gate` = 262 passed（156s，sqlite in-memory，零 LLM）。
- **评审证据形态**：X-01/X-02/X-10 有入库 REPORT/RECEIPT；X07-P21 有 REPORT；**X-03/X-04/X-05/X-05B/X-06/X-07/X-08/X-09 的 receipt 原件未入库**——评审结论在 ACCEPT merge commit message 内（「dual-reviewed」「R2 PASS」等），经 wt759 三源核验；断链本体已登记 **V3-FIX-502**。
- 真源注记（FIX-330 裁决引文）：生产的 agent 执行账本=X-05 AgentRun/AgentRunTransition + X-06 AgentToolCall + outcome_ledger 三套；模板件 agent_execution_stats 零写侧、已如实标 unavailable。

## 1. 意图（卡面提炼）

X 线 10 卡（ACTION stream，V3-2~V3-5 门）把「AI 陪伴学习」落成**可执行的行动引擎**，核心主张是 V3 的第 2 条：**Human/Agent/Hybrid 执行模型——AI 降摩擦但不偷走目标**。设计骨架（ACTION_AND_INTERVENTION_ENGINE / HUMAN_AGENT_HYBRID / AGENT_RUNTIME）：

1. **契约**：在既有 Task/Plan/Proposal 上加 V3 语义（desired_outcome/smallest_useful_step/completion_evidence/execution_mode/cognitive_ownership/source_refs/risk），不重建 task system；关键字段不得仅以自然语言携带（X-01）。
2. **分配**：delegation rubric 而非模型随口「我来帮你做」——八维因子输出 mode；high-risk auto=0；学习目标不默认 Agent 写完整答案（X-02）。
3. **授权**：proposal→approve→validate version/permission→commit→receipt 统一权威路径，所有入口同路；重复确认不重复写、冲突不覆盖、未授权不执行（X-03，critical）。
4. **人执行面**：start/complete/abandon/rescope + 按类型取完成证据；实际时长永不从 estimated 回填（X-04）。
5. **Run 真源**：统一 run_id/state 持久化，App 内存与 OpenClaw 不成第二真源；WebSocket 仅通知（X-05，critical）。
6. **工具边界**：工具元数据（read/write/risk/reversible/permission/cost）+ side effect 强制幂等键 + run budget（X-06，critical）。
7. **混合交接**：Agent 做一部分→轮到用户→继续；owner 纪律；用户操作两次不 resume 两次（X-07）。
8. **结果回写**：无论谁执行，完成统一产 Outcome 进 Outcome Ledger；失败不点亮成果（X-08）。
9. **失败语义**：false success=0、duplicate side effect=0、20+ chaos case 终态正确（X-09，critical）。
10. **端到端评测**：≥60 场景 allocation ≥90%、high-risk auto=0、false success=0、Simulator 无需开发者介入（X-10）。

**Forbidden（全卡共性）**：不重建既有真源；不用 mock 冒充真实行为；不以静态阅读宣称 UX 通过；不弱化既有安全/幂等/隔离/审计守卫。

## 2. 实际交付逐卡表

### 2.1 总表

| 卡 | 主干 SHA（评审签收） | 关键交付 | 用户可见行为一句话 | 验证证据 | 残差 |
|---|---|---|---|---|---|
| X-01 | `43942d23`（dual-review+rework） | x01 迁移（tasks 8 nullable V3 列）+ `core/action_plan.py`（448L 冻结契约） | 任务可携带「期望结果/最小有效步/完成证据/谁执行」结构化字段 | 640L 测试含迁移 sqlite 重放；F1 探针（脏枚举行曾致全端点 500）红→绿 | card_protocol 映射停留在文档级（B-06 ENTITY_MAP 后续补齐真源审计） |
| X-02 | `c0e02bf8`（dual-review+rework） | `action_allocation_policy.py`（995L）：纯函数 decide_allocation 四层 | 学习类请求永不自动代写；高风险永不自动执行；每次分配带 why+confidence | 85 场景盲评规则层 100%（目标≥90%）；1392L 测试；E-04 真模型 5 面收敛轮 15/15 | 语义层默认关（生产=规则层）；实机 5-Persona 观感转 HUMAN_INBOX |
| X-03 | `7fc507fd`（dual-reviewed, rev2） | x03/x03b 迁移 + proposals API + `action_command_service.py`（897L）统一命令路径 | 重复确认不重复写、版本冲突不覆盖、过期/取消明确、UI 拿权威 receipt | 1577L 测试；X-10 proposal 族 12 场景全 PASS | chat 卡片命令分发缺口由 wt687（FIX-378）收口；P-04 在其上加低风险 auto-execute 授权层（`322988ce`） |
| X-04 | `6a6363f8` | `task_completion_evidence.py`（275L）+ task_service +387L + mobile 完成流 | 完成要交证据；实际时长如实测量、绝不拿预估冒充 | 458L 后端测试 + mobile 真跑；「actual≠estimated」为函数级红线（违者 raise） | Focus/Calendar 仅 optional capability 挂点（卡面即如此定位） |
| X-05 | `fbe679bb`（dual-reviewed rev2）+ X-05B `238abe22`（双 PASS） | x05 迁移 agent_runs + `run_state_machine.py`（322L）+ agent_run_service（1087L）+ runs API + 投影消费者 | App 杀掉重开仍能查到任务进行到哪一步；worker 重启恢复或明确终态 | 状态机非法迁移测试；X-05B 后 190 绿；X-10 run_steps 族 13 场景 PASS | FIX-32 OPEN（once-set 键无 attempt 维度等可见性缝隙，备忘） |
| X-06 | `5abd1c4b`（dual-reviewed）+ 当日热修 `f2e9f22e` | x06 迁移 agent_tool_calls + `tools/metadata.py`（304L）+ `executor.py`（369L ToolExecutor） | AI 每次动工具都有权限判定、账本行、幂等键；花钱/超时进明确状态 | 1134L 测试（budget 449 + safety 685）；**事故**：合入当日 chat 管道 100% 断（models __init__ 漏注册）当日修 | FIX-40 P2-3 已收口@`42ade28c`；残余：reversible 38/38 全真零信息量、_resume_or_replay 信任创建时授权 mode |
| X-07 | `8c769eaf` + P2-1 `76677063` + P2-2 `20f9b200` | x07 迁移 run_steps + `core/run_steps.py`（340L owner/ownership 词表）+ AwaitingStepResumeCard | 「AI 备料→你来判断→AI 校对」的交接卡真实存在且不能被 AI 代答 | 1062L 后端 + 216L mobile 测试；owner 纪律服务层拦截（agent_run_service:1249 亲验） | **GJ07 三端实机未做**（headless+widget 口径） |
| X-08 | `5c62e2d8` | `outcome_capture_service.py`（219L）+ outcome_ledger_service +154L | 完成/失败都留可查结果记录；失败不点亮星图成果 | 528L 测试；J-06 实测 G-02 吸收器恰一次点亮+重放幂等 | partial→NEUTRAL 极性映射为保守口径（设计内） |
| X-09 | `0c0e08ef`（dual-reviewed） | `core/failure_semantics.py`（389L）+ tool_call_ledger（285L）+ executor 两阶段收敛 | 崩溃后不假装成功：同一操作重放被明确拒绝而非悄悄重执行 | 1141L 单测 + 217L 崩溃恢复 e2e；X-10 outcome 族含 failure_preserved | FIX-42 OPEN（分类器 transient+confirmed 陷阱等备忘）；幂等洗白链 FIX-417/447 已修（`df51a731`/`2d82a628`） |
| X-10 | `3b5a99bc` | `tests/v3_action_eval/` 判定套件 + 77 场景 fixture + results.json（18k 行）入库 | （对内）行动引擎全链 77/77 可重复判定 | **77/77 PASS、allocation 28/28=100%、high-risk auto=0、false success=0**；判定器从 DB 独立复算、`real_llm_calls=0` 强制断言 | 零真实 LLM 为显式设计（见 §3.6）；LLM 依赖面由 J-04/J-06/JOURNEY 真驱动补证 |

### 2.2 逐卡要点与证据细节

**X-01（43942d23）**——落点=tasks 表 8 个 nullable 新列（`action_schema_version` 判别位 NULL=legacy；desired_outcome；smallest_useful_step 带 `useful_because` 封闭枚举、空判据=伪步骤拒绝；completion_evidence 类型化证据规格；cognitive_ownership（D13 首版定义全仓第一落点）；source_refs 封闭 scheme；risk_class；reversible），**execution_mode 复用既有列不建第二真源**（dev 库 1231 行全 NULL 复核后定案）。契约真源 `core/action_plan.py`：C-01 同款冻结 dataclass+封闭词表+统一投影门——**读侧容错取舍（R2 返修）**：初版 REST 路径原样投影列值，单行脏枚举会使该用户全部任务端点 500（F1 探针实证）；修后版本门/词表不过→整块降级 None+WARN（区分「没有 V3 计划」与「计划损坏」）。契约载体=REST/JSON 非 gRPC，proto 不动（有意识决定）。

**X-02（c0e02bf8）**——「AI 能做 ≠ AI 应做」机制化为四层纯函数：①Guard 硬规则（R1 风险/不可逆、R4 具身、R5 隐私、R6 低置信、G1 学习守卫）从全集剔除不可行 mode；②选择层（显式意图>持久偏好>ownership×tool-advantage）；③修饰层（T1 紧急促进、T2 偏好 agent 但更慢更贵→降 hybrid）；④**语义层（默认关，`SPARKLE_ALLOCATION_SEMANTIC_ENABLED=False` 本 worktree settings.py:1029 亲验）**——LLM 只能在 feasible set 内选（越界 S2 拒收保规则默认），带熔断（3 败/300s）/限频/超时。学习守卫硬规则：学习任务 feasible set 永不含 agent、hybrid 必须带 user-authored 证据要求、`vet_agent_offer` 拒「直接写完整答案」；X-01 F5 矛盾集（agent×user_core 等）成硬规则测试冻结。封闭词表 sha256 双冻结。
**真模型证据**：85 场景盲评=规则层独跑 100%（fixture 标注只看 HUMAN_AGENT_HYBRID 文档、rubric 盲跑不见 target）；E-04（`58d08c6f`）真模型五面探针（act-B1 学习守卫/B2 机械委托/B3 风险/B4 灰区/B5 **注入推 agent**）基线轮 8/15 失败→prompt 收敛轮 **15/15**（qwen3.8-flash 真实 API，baseline/converged 两份 JSON 入库）。**生产authority实战**：J-04（`02b82cd2`）首行动推导中 LLM 建议 agent 的学习步被 decide_allocation 学习守卫拦回 human/hybrid（真 LLM 产出+规则权威，测试断言在案）；JOURNEY day1-6 真驱动 6/7 过门（day6 门曾因 FIX-314 时钟语义停、当日修复重跑 PASS，证据链完整）。

**X-03（7fc507fd）**——统一命令路径：`action_command.py`（命令注册/schema）+ `action_command_service.py`（proposal→approve→validate→commit→receipt 全生命周期）+ `task_commands.py`（首批命令集）；里程碑路径迁上命令路径（milestone_command_path 测试）；网关 `/action-proposals` 纯代理。幂等四态（同键重放/同键异 payload 重放既有/终态拒绝/TTL sweep）与乐观并发（版本冲突不覆盖）由 1577L 测试+X-10 proposal 族 12 场景双承载。后续增强：P-04（`322988ce`）低风险 auto-execute（总开关∧类别授予∧low∧reversible∧无人工标记五条件，grant_basis 固化进 receipt，revoke 即时生效含 resume 复核）；U-04 chat 卡片命令分发收口（wt687，FIX-378）——「所有入口走同一权威路径」在 09-27 才完全成立。

**X-04（6a6363f8）**——`resolve_actual_minutes` 函数级红线：只认实测两真源，非实测值直接 raise（代码注释「宁少扣不少算」）；`compute_actual_minutes_from_timestamps` 从时间戳推导；完成证据按 action 类型（artifact/self-report/test）取；mobile 任务卡/详情/执行屏接线。GJ05 的 backend 全链+widget 部分已证；三端实机同属 HUMAN_INBOX 族。

**X-05（fbe679bb + 238abe22）**——run 脊柱：QUEUED/RUNNING/AWAITING_USER/EXECUTING/terminal 状态机（非法迁移测试钉）+ agent_runs/agent_run_steps 表 + runs API + 事件投影消费者（`$` 起点消费组首部署回放突发被 FIX-28 定性为一次性部署成本并根治）；X-05B 补 EXECUTING producer 接线（执行步进可见性）+ runs API 硬化（intent 归属 404、cancel reason 服务端白名单）。R2 双 PASS 190 绿。**生产账本地位**由 FIX-330 裁决背书（agent-stats 真空事件反证：生产链路已有自己的三套账本）。J-06 旗舰旅程把 run 脊柱用进产品（prep[agent]→judgment[human]→execute_check[agent]→outcome[hybrid] 四步真实数据流）。

**X-06（5abd1c4b + f2e9f22e）**——工具能力边界：metadata（read/write/risk/reversible/required permission/cost）+ ToolExecutor（权限判定→账本行→幂等键→执行，账本与业务写同事务——后由 FIX-40@`42ade28c` 收编 8 处内部 commit 工具达成「失败一起回滚、无 key 中毒」，红绿链 3 红→6 绿）+ run budget（token/cost/time/tool calls，超限进明确状态）。**事故考古（V4 必读）**：合入当日 chat 管道 **100% 断**——AgentRun/AgentToolCall 漏注册进 models `__init__`，SQLAlchemy lazy relationship 解析失败；热修 `f2e9f22e`（「demo-critical」）当日收口。教训：ORM 模型注册是隐式全局契约，新表合入需 import 面 grep。
**真模型证据面**：J-06 prep 步走真实注册工具 retrieve_user_material 经 ToolExecutor 完整执行链（真实 document_chunks 检索，「零 mock 零预录」，prompt 断言在案）——工具执行链在真 LLM 会话中被端到端行使过。

**X-07（8c769eaf + 76677063 + 20f9b200）**——步骤契约：`run_steps.py` 纯函数（step_id/ordinal 全局唯一、owner∈{agent,human,hybrid}、completion_condition kind 封闭词表、越表 ValueError）；ownership 字段进 run 投影（解 U-04 P2：「你做」态此前从 authMode 不可达）；**owner 纪律**：agent 完成 human/hybrid 步被服务层拦截（本 worktree agent_run_service.py:1249 亲验）——J-06 判断面「空选择 422 judgment_required、agent 不可代决」即此纪律的产品化；resume 幂等（mobile `runStepActionIdempotencyKey` 统一推导式+服务端 `_confirmed_replay` 回 200）；P2-1 完成戳单一真源（计数器统一，274L 变异测试）；P2-2 BudgetExceeded→409。

**X-08（5c62e2d8）**——统一 Outcome：`capture_task_outcome`（任务完成路径挂钩）+ `build_run_receipt_outcome`（run 终态 receipt 映射，PARTIAL→NEUTRAL 极性保守）；经事件更新 Goal/Milestone/Galaxy 不双写多真源；G-02 吸收器实测恰一次点亮、同因 receipt duplicate 只补溯源、双面重放不重复点亮（J-06 测试断言）；失败/部分结果保留（failure_preserved/partial_not_promoted 场景在 X-10 outcome 族）。消费面：D-02 读模型账本 ledger_verified 查询、J-08 轨迹投影（derive_outcome_id 同一推导，`d105aa57` 四方一致锁）。

**X-09（0c0e08ef）**——失败语义三分类（retry vs reconcile vs unknown outcome）+ 两阶段收敛：executor 内部 commit 后崩溃→账本行 interrupted→**同幂等键重放永久拒绝**（「重试必须换新键——那是显式决策不是自动行为」注释在 executor 亲验）+ 客户端诚实状态。20+ chaos 场景（crash_recovery e2e 217L + 1141L 单测）。
**洗白链修复史（X 线最深的修复族，V4 教材）**：FIX-40 P3-6 发现自修正环可把幂等闸门拒绝「洗白」成新键真执行→X-09 先在 chat /stream+/task 面排除（error_type 过滤）；wt713 顺审发现三闸门类（IdempotencyConflict/ArgsMismatch/KeyRequired）仍可洗→FIX-417@`df51a731`；wt732 再发现 Interrupted 在 /confirm 两面仍可洗→FIX-447@`2d82a628`（wt740 运行级复现+6 用例钉+handler 排除集扩展）。链条说明：**失败语义的正确性不是一次设计出来的，是三轮对抗考古收出来的**。

**X-10（3b5a99bc）**——评测形态：77 场景（allocation 28/authorization 10/proposal 12/run_steps 13/outcome 10/journey 4）×六元组判定；**判定独立性=判定器对 DB 真相独立复算，不信执行器自述**；`real_llm_calls=0` 强制断言（可复现、CI 无 key 可跑）；results.json 18k 行逐场景六元组入库。总览：77/77 PASS、allocation 达标率 100%（mode target 22/22+offer guard 6/6）、high-risk auto=0、false success=0、总延迟 157s（纯服务层墙钟）。后续 P-04 卡把 dbfixture auto_grant 升级为完整授权仪式后 X-10 gate 12 绿复验（`322988ce` 引证）。

## 3. 设计决定与取舍（考古）

1. **加法契约而非重建**：8 个 nullable 列+版本判别位，旧行零影响（1231 行 NULL 复核）；execution_mode 复用、proto 不动（REST 是 tasks 契约载体的有意识判断）；card_protocol 不切流（文档级映射，B-06 审计补真源图谱）。
2. **分配权威=代码不=模型**：LLM 只在 feasible set 内精化灰区，越界代码强制拒收（S2）——「不信任 prompt」是结构性的；学习守卫/高风险非 auto 是硬规则不是提示词约束。J-04 实战（LLM 建议 agent 被拦回）证明该设计在真模型下行使。
3. **Run 表是唯一真源，WebSocket 仅通知**：X-05 验收原文「不让 App 内存或 OpenClaw 成第二真源」落到 agent_runs/agent_run_steps/agent_tool_calls 三表+状态机+投影消费者；FIX-330（agent-stats 真空→如实 unavailable）反向确认了「三套真账本」的边界。
4. **幂等键哲学**：side effect 强制幂等键；键永不自动重执行，重试换键=显式决策。洗白链三轮修复（417→447+FIX-40 P3-6 先行排除）把这个哲学贯彻到了自修正环/LLM 重试等所有旁路。
5. **账本原子性**：「工具写入与账本行同事务」最初对内部 commit 工具不成立（FIX-40 P2-3）——修法取「executor 打点+服务层收编 commit 为 flush」而非广泛 savepoint（调用面审计否决后者：独立脏会话调用方会静默丢写）。取舍记录完整在台账。
6. **评测独立性**：X-10 判定器从 DB 复算+零 LLM 断言=门禁可复现；LLM 依赖行为的验证被**显式路由**到别处（E-04 真模型探针、J-04/J-06 真组件链、JOURNEY 真驱动 6/7+day7 GO），不是遗漏而是分工。V4 读证据时要按这个分工找：**「X-10 100%」是规则层+服务层结论，不证明真模型灰区表现**——后者看 E-04/J-04/J-06/JOURNEY。
7. **已知代价的接受**：X-05 首部署消费组回放突发（一次性运维成本，不改为「运维知悉」）；reversible 元数据 38/38 全真（无信息量，登记待高影响域接入再分化）；budget 不切断 agent 循环（20 次硬顶兜底，FIX-40 行内留记）。

## 4. 残差与 V4 注意点

**活性残差（有台账号的）**：
- FIX-32（X-05B follow-ups，OPEN 备忘）：once-set 键无 attempt/epoch 维度（resume 后 30 分钟内重复里程碑被抑制——纯可见性）；cancel 白名单先于幂等早退（终态 run 非法 reason 得 422 非 200，测试注释相反）；sweep 措辞偏宽。
- FIX-42（X-09 follow-ups，OPEN 备忘）：分类器公共 API transient+confirmed→retryable 潜在陷阱（当前接线不可达）；WAIT_EXPIRED/QUEUE_STALE 的 error_category=permanent_failure 终态观感偏粗；REPORT 两处勘误。
- FIX-40 残余留记：P3-7 M7 冲突语义断言区分；reversible 38/38 全真零信息量；`_resume_or_replay` 信任创建时授权 mode（高影响域接入时复推）。
- V3-FIX-502（X-03..X-09 receipt 断链，本轮登记）。

**结构性事实（V4 设计输入）**：
1. **生产分配=规则层**。语义精化层默认关；灰区默认 hybrid。若 V4 要更聪明的灰区分配，先决问题是「给语义层真实流量+护栏」还是「继续加规则维度」——E-04 已证明 prompt 收敛后真模型五面可 15/15，但那是探针不是产品流量。
2. **所有权产品化已完成大半**：cognitive_ownership 三值贯穿 tasks→allocation→run steps→UI ownership 投影→U-04 组件；J-06 证明「AI 备料→用户判断→AI 校对」可端到端走通且 AI 代答被结构性拦截。V4 扩展执行模式时沿这条词表链，勿新造第二套 ownership 词汇。
3. **失败语义已成体系但仍在进化**：两阶段收敛+幂等键纪律+洗白排除集是现势边界；V4 新增任何「自动重试/修正环」必须先过「会不会把闸门拒绝洗白成新执行」这一问（三连登记的教训）。
4. **ORM 注册隐式契约**：X-06 合入当日 chat 全断事故——新表必须注册进 models `__init__`；V4 若引入模型注册守卫（如 import 面 lint）可根除该族。
5. **实机证据缺口**：GJ07（X-07）及全 X 线三端实机走查均 headless+widget 口径，转 HUMAN_INBOX；X-10 的 journey 族 4 场景是服务层重放，非真机。V4 验收计划应把「真机 hybrid 交接」列为设备解锁后的第一批。
6. **agent-stats 类「模板真空」教训**：FIX-330 证明「结构性零冒充测量值」与 mock 污染同罪——V4 新增任何统计面必须同时交付写侧或默认 unavailable。

## 5. 本轮发现问题登记（号段复核后占用）

| 号 | 定性 | 一句话 | 证据硬点 |
|---|---|---|---|
| **V3-FIX-502** | 实现漂移（证据面） | X-03/X-04/X-05/X-05B/X-06/X-07/X-08/X-09（及 M-06/M-08/M-09）卡级 REPORT/REVIEW_RECEIPT 从未入库，台账 FIX-28/29/32/40/42 引用死路径 | `git log --all --diff-filter=A` 0 命中；v3-output/ 现存 X 线仅 X-01/X-02/X-10/X07-P21；wt759 以 commit message 签收核验故结论不受影响 |
| **V3-FIX-503** | 承诺未兑现 | FIX-36「真模型复验由 E-05 下窗口补」未兑现（M-09 探针面；其结论直接影响「记忆个性化在答案层生效」这一 X/J 线共同前提的库内证据形态） | HEAD 库内 stability report 仍是修前 P01-D1 0/5 快照；E-05 产物与 fleet notes 无复验记录；代码修复有 8 单测钉 |

（号段复核：500/501 在册 0 占用。X 线本身未发现新的活性缺陷——洗白链/账本原子性等深坑均已被在册 FIX 收口，本章以引用方式归档。）
