# 北极星 C 线证据链战报——「期末只剩一周，用 Sparkle 备考效果最好」的证据

- 纵队：C 纵队战报编纂线（C-REPORT，wt203 ｜ 纯编纂零代码，主仓只读）
- 日期：2026-09-23 ｜ 基线：`4a824864`
- 性质：A 线 SPEC-REVIEW 战报的姊妹篇。本篇只做一件事——把「期末一周备考效果最好」这条北极星主张的**每一条证据链**（问题→修法→实证数字→对用户的意义）编纂成可进参赛材料的形态。
- 诚实红线：每个数字可溯源（来源见 §9 索引）；进行中的如实标注为进行中；待判的不写成已过；尚未证明的不预支结论。

---

## 0. 总览：北极星主张 → 证据强度

| # | 主张（用户语言） | 证据链 | 关键实证数字 | 强度 | 主溯源 |
|---|---|---|---|---|---|
| 1 | **提问秒回，不等 30 秒** | TTFT 双簇根因→配置级收敛 | fast-track 30.6s→**1.26s**（24×）；通用链 29-43s→**1.05-2.06s**；事实投影 30-90s→**0.6s** | 活栈实锤 | TTFT-PROBE / TTFT-CFG 报告 + 舰队日志 |
| 2 | **判得准、回得快、还省 79% 钱** | GRADE-AB 100 题双臂真实 LLM 评测→PRO 档切流 | verdict B 0.94 vs A 0.93；gate 双过；时延 **5×**；成本 **-79%** | 真实 LLM 全量实证，已切流（可一键回滚） | GRADE-AB 报告 + 运行证据 JSON + commit `838494ad` |
| 3 | **计划真的每天跟着你走** | JOURNEY 仪器链（intake 自愈 + 多天驱动器） | 7 条 day:N 脊柱实栈落库；CP-00/01/03 稳定 pass、**fail=0**；J4-J6 **待判** | 部分实证（Day2 判定等真实跨日） | JOURNEY-DRIVER / INTAKE 系列 + 舰队日志 |
| 4 | **该在跑的安全与上下文，真的在跑** | 三个「从未运行/死码」级修复 | SecurityMonitor **史上首次真启动**（双行日志）；sidecar/fast-track 多轮死码 **2 行修复**+真实 LLM 三轮冒烟 PASS；user_state_v1 从未产出→红转绿 | 活栈实证 | PROD-LOG / PROD-FIX-1 / ORCH-NEIGHBORS / SIDECAR-JOURNEY |
| 5 | **星图不再大面积未知** | 星区重放（回填队列根治+幂等重放） | **183/183** 节点真实 LLM 判定；VOID 46→**6**（残余=真不可判） | 活栈实证 | SECTOR-AUDIT 报告 + 舰队日志 |
| 6 | **每一分光子都诚实入账** | combo 光子黑洞修复 + 首胜唯一索引 | 18 次发放蒸发→0；8 并发恰一发；旅程对账基数=余额=5050 | 红→绿并发实证 | TOUR / PHOTON-IDEM 报告 |
| 7 | **AI 记忆/星图确实带来增益** | GAIN-EVAL 消融评测 | ——（尚无数字） | **进行中：增益尚未证明** | 舰队日志派卡记录（wt198） |

一句话读法：链 1/2/5/6 是**已闭合的工程实证**；链 3 是**仪器已就位、判定面等真实时间**；链 4 是**把「以为在跑其实从没跑过」的三处修到有生产实证**；链 7 刚开工。七链合起来覆盖北极星旅程的「秒回交互→便宜判卷→诚实经济→每日适应（待判）→增益证明（进行中）」。

---

## 1. TTFT 链：从 30 秒沉默到秒级开答

**问题**。北极星基线（LOOP3）5 条实测 TTFT：12.2 / 28.8 / 30.1 / **30.6s**，3/4 聚在 29-31s 簇。TTFT-PROBE（wt126）用 7 条逐帧时间线把 30 秒钉死在两处：

- **簇 B（主害，5/7 条）**：qwen3 混合模型流式下默认**先思考后作答**，`reasoning_content` 流持续 13-43s 期间思考块被整段丢弃——前端 0.3s 收到一次「思考中」后陷入长静默（实测 M2=42.9s、M6=33.4s）。延迟本身在模型侧，暴露面是配置缺陷：DashScope 车道发的思考参数是 GLM 风格 `thinking:{type}`（兼容模式不认），部分路径干脆什么都不发（=默认思考开）。
- **簇 A（规划轮）**：`check_sufficiency`（LLM 3.2-19.2s）→ `check_goal_quality`（15.7-35.7s）→ LangGraph planner **恒定打满 10s 超时**走兜底，三项串行全部发生在首个事件之前（V1A=30.6s、M7=39.8s）。
- **附带发现一级死码**：`asyncio.timeout(30)(manager.process_planning_turn)(...)` 把上下文管理器当可调用对象→必然 TypeError→被 except 吞掉——**每次考试冲刺开场 100% 命中**，fast-track 快车道整体死亡，活栈日志实证 `'Timeout' object is not callable`。这就是 LOOP3 V1A 跌入 29s 通用链的直接原因。

**修法**。三步收敛，全部配置级/预算级，语义零改：

1. TTFT-PROBE（合入 `d19551a0`）：两处 `asyncio.timeout` 误用改为 `async with` 形态，救活 fast-track；reasoning 块按 **3s 节流**下发进度帧（等待期不再静默假卡，承接 DL-R1-AUDIT S18）。
2. TTFT-CFG（wt131，合入 `b0a3b05f`，14 条新增单测）：DashScope **思考分档**——FAST/STANDARD/PLUS 显式注入 `enable_thinking=false`，PRO/MAX/TOP 不注入（保留思考），统一在 `get_openai_client_kwargs` 一孔覆盖流式/非流式/langchain 全部组包路径；planner 超时 10s→3s；前置质量门移 FAST 车道 + 5s 预算封顶（超时落既有启发式兜底）。
3. 主会话热修（`63ca1517`）：fast-track 补 done 帧。

**实证数字**（全部活栈）：

| 面 | 修前 | 修后 | 溯源 |
|---|---|---|---|
| fast-track 冲刺开场 | 30.6s（LOOP3 同类） | **1.26s（含 done 帧）**，24 倍 | 舰队日志 @`63ca1517` |
| 通用链 TTFT | 29-43s | **2.06 / 1.05s**（enable_thinking wire 生效） | 舰队日志 @`b0a3b05f` |
| 事实投影（明示事实入档） | 30-90s（根因：确定性抽取被串行排死在 LLM 往返后，带内 51.2s） | **0.6s**（declared 快车道前置，`inferred_extraction`、due_at 正确） | wt128 NBP-6 @`7454f484` |

**对用户的意义**：冲刺第一句话从「提交后半分钟无反馈」变成秒级开答；改用轻档的学生不再为回答深度支付 30 秒思考税；等待期有节奏的进度帧替代三点动画假卡。

---

## 2. GRADE-AB 链：100 题双臂裁决——判卷档切换从假设变成事实

**问题**。B-QWEN 选型备忘录（wt183，`d2265244`）提出假设 A：聊天内错题诊断（四段结构：①错误类型②根因③正确解法④变式题）现役 PRO 档 qwen3.7-plus 思考（$0.0012/1k）可能被 qwen3.8-flash 思考同价档（$0.00025/1k）替代——「思考同价 flash 能否追平 plus 思考一致率」当时**没有任何实测数据**。采纳门槛事先冻结：≥100 题、错误类型分类一致率差 ≤3pp、JSON 解析成功率差 ≤2pp，双过才切。

**修法**。GRADE-AB（wt189，`ed31944f`+真跑修复 `418f3493`）把门槛变成三个资产：100 题离散数学静态金标题包（verdict correct 50 / wrong 44 / partial 6；边界三类 partial 6 / 笔误 slip 6 / 空白 blank 4；七大域，图论 22 题与真实旅程用户弱点同科）+ 双档 A/B 运行器（与生产同一入口 `llm_router.select_model(force_tier=…)`，两臂 system 提示词逐字节相同、温度 0.3、单变量=模型档位；纯净性=绕过降级链防 B 臂污染）+ 8 项 pytest 守卫（-79% 成本锚点钉死在测试里）。

**实证数字**（全量 100 题 × 2 臂真实 LLM，run_id `GRADE-AB-20260923-005550`；5 题冒烟先行全通 verdict 1.0/1.0）：

| 指标 | A 臂（现役 PRO，qwen3.7-plus 思考） | B 臂（候选，qwen3.8-flash） | 判定 |
|---|---|---|---|
| verdict 准确率（vs 金标） | 0.93 | **0.94** | B 不降反升 |
| 错误类型分类一致率 | 0.80 | 0.77（差 3.0pp） | gate① 恰在门槛内，**pass** |
| JSON 解析成功率 | 1.0 | 1.0（差 0pp） | gate② **pass** |
| score MAE | 0.0375 | 0.0375（相同） | — |
| 时延 p50 / p95 | 5147ms / 14595ms | **1031ms / 2212ms**（≈5×） | — |
| 100 题总成本（估算） | $0.0355 | **$0.0074**（比 0.2085，-79.2%，预测 0.2083） | — |
| 两臂互判一致率 | — | verdict 0.99 | 13 处分歧对称（相邻类别双向混淆，非系统性） |

`adoption_signal=pass` → **裁决采纳假设 A**：`.env` 加 `LLM_TIER_PRO=dashscope_standard_thinking,glm_4_7_pro` + 引擎重启，双进程日志实证 override applied——B 线 PRO 档正式切 qwen3.8-flash（commit `838494ad`）。**回滚 = 删一行 env**。

**对用户的意义**：聊天内错题诊断从 5 秒级思考档降到 1 秒级、单次成本 -79%，而判定质量不降（verdict 反而 +0.01）——错题诊断从「贵而慢的深度功能」变成「每个学生每次错题都用得起的高频功能」。

**诚实注记**：成本/时延为估算面（token 数为 CJK 启发式、单价取 router 注册锚点）；gate① 的 3.0pp 恰在阈值边缘，分歧清单里 partial 边界题占比已登记供复核。

---

## 3. JOURNEY 仪器链：7 天旅程的「脊柱」与诚实的时间门

**问题**。北极星七条检查点此前只有「单日 API 压缩轮」；而「期末一周」的本质是多天旅程。两个结构性障碍：

1. **「天」绑死真实时钟**：`date.today()` 内联散布约 20 个文件、无中心时钟 seam——Day N→N+1 唯一诚实路径是真实跨日（时间注入/进程假钟两条路都被证据否决：跨进程时钟撕裂 + 证据时间戳造假，双违诚实红线）。
2. **最常见路径缺 7 天脊柱**：用户经 goal 建计划后走 exam-sprint intake 会命中计划复用（NBP-3b），返回的是只有里程碑梯任务的 goal 计划——**Day1-Day7 的 day:N 标签任务缺位**，`_plan_current_day` 无从推进，CP-04 的结构判定面退化（JOURNEY-DRIVER 实测 S2 不可观测）。

**修法**（四卡接力，全部域级回归零新增失败）：

- INTAKE（wt102）：plan_id UUID 断裂 + 同目标重跑 intake 撞配额 403（或静默双计划）→ **同目标幂等复用**语义（重放返回既有计划，红→绿 2 例）。
- INTAKE-IDX（wt111）：部分唯一索引 `uq_plans_user_sprint_goal_active` 根治并发双计划窗口——存量 224 条活跃冲刺中实测恰 1 组违反（LOOP1 时代遗留），保留最新、非破坏收敛。
- INTAKE-TEMPLATE（wt166，`5b912dcf`）：复用命中后**补挂 7 天模板**（收紧复用条件的方案 B 被证据否决：要么复发静默双计划、要么制造 403 故障面），形状闸/goal 闸/PG 行锁三层并发防护；存量用户**首触自愈**（下次 intake 即补齐，保真度等同首次生成）。
- JOURNEY-DRIVER（wt161）：`--phase day2/day2settle/day3/day3settle` 相位 + **次日门**（同日运行诚实 blocked——「昨天」尚不存在，跑它就是伪造时间线）+ 复习提交按 error id 守卫（重跑零双提交）+ Day4-7 完整设计（CP-02 轨迹→CP-06 覆盖度→CP-07 后测增益→CP-08 遗忘率）。

**实证数字**：

- **intake 自愈实栈落库**：外科式 intake 重入 API → 同 plan_id 200 复用 → DB 实证 11 任务中 **7 条 day:N 脊柱**（Day1-7 + phase:1/2/3 分带，goal 里程碑原样保留）——wt166 设计精确落地。
- **压缩轮收敛 fail=0**：JOURNEY-DRIVER 活栈 run `NS001-JOURNEY2-20260922-211514`：`counts = {pass:3, fail:0, blocked:6, unsupported:2}`——**CP-00**（诊断基线+考纲图谱 mastery 落星图）/ **CP-01**（计划生成+幂等复用+人工确认端点，404 防枚举探针过 @`308400d1`）/ **CP-03**（错题落库+复习+星图 mastery 同步，`39045ad6`）稳定 pass。
- **复习机制面**：到期错题队列 due=1、提交=1、`next_review_at` 相对提交前可证实推进=1。
- **J4-J6（次日计划适应判定）= 诚实 blocked，等明晚真实日界**——仪器已闭合（基线含脊柱、差分逻辑就绪），判定面未到达。**待判不是已过**。
- 全程 LLM 消耗 3 条（预算 24），面板/星图/账本证据 JSON 逐步入盘（`v3-output/JOURNEY-DRIVER/live-20260922/`）。

**对用户的意义**：「明天该学什么」真的每天基于昨天结果自适应，而不是一次性生成的静态清单；这是北极星从「工程指标绿」走向「用户旅程真」的测量基础——没有这套仪器，效果主张永远停留在口头。

---

## 4. 三个「从未运行/死码」级修复：把以为在跑的真的跑起来

这一链的共性触目惊心：三处核心能力**在修复前从未真正运行过一次**，且全部无告警（错误被吞）。

### 4.1 SecurityMonitor 史上首启

- **问题**（PROD-LOG 只读巡检，wt175，`a2506361`，两 P1 之一）：SecurityMonitor 启动即死——`main.py:203` 传参调用 vs `:97` 无参签名，TypeError 被吞——**爆破/IP 风控监控从未运行过**。
- **修法**（PROD-FIX-1，wt179，`9ba67176`）：签名对齐双向兼容 + **启动即验、失败不静默** + shutdown 收进 lifespan + 4 个新指标。
- **实证**：引擎重启后生产日志双行实证——**SecurityMonitor 史上首次真启动：`initialized=True`、`background_tasks=2`、`redis_ready=True`**。
- 配套（SECTOR-AUDIT，wt147）：安全审计表 `security_audit_logs.id` 双侧无默认值→每条 INSERT 必带 NULL id→NotNullViolation（活栈 29 条实证），失败分支还 rollback 毒化整个请求事务（登录审计一并被吞，安全审计数据 100% 丢失）。修法：模型 `default=uuid.uuid4`（零迁移）+ SAVEPOINT 隔离（失败只回滚审计行自身）+ `[SecurityAuditFallback]` 全事件 JSON 留痕。

### 4.2 sidecar / fast-track 多轮死码（2 行修复）

- **问题**（ORCH-NEIGHBORS，wt190，`bef7ae07`，卡面猜测被证伪）：9/10 测试失败全部是**真产品缺陷**——`save_session` 恒以 `planning:session:{user_id}:{chat_session_id}` 落键（正确的多租户设计），而 orchestrator 的 Aurora 规划旁路（:427）与 fast-track（:731）两处读取不带 `user_id` → 真实 Redis 下键恒 miss → **多轮对话的旁路与续聊退化为每次重新开场**。
- **修法**：2 行补传 `user_id`（明确裁决拒绝双键兜底——跨租户安全优先）。
- **实证**：SIDECAR-JOURNEY（wt196，`8f97733d`）双层覆盖：5 个调用点级单测（键形制/多轮不重开/恰一次挂载/无遗留键回退/跨租户隔离；变异验证还原修复后恰 2 钉变红）+ 3 轮 API 级旅程全绿；orchestration 目录 199 passed / 0 failed。**真实 LLM 三轮冒烟 PASS**：T1 冲刺开场 → T2 离题提问（通用链先答任务状态）→ T3 回归规划命中确认门（系统提示需确认继续=会话延续铁证，无重复开场）；Redis 恰一把 `planning:session:{uid}::` 键=键形制生产实证。

### 4.3 user_state_v1 从未产出

- **问题**（同 PROD-LOG 巡检，两 P1 之二）：`predictive_service.py:496` 引用坏列 `importance`（真列 `importance_level`）炸整个 `get_user_state`——**user_state_v1（AI 上下文状态聚合）从未产出过**。
- **修法**（同 PROD-FIX-1）：`importance_level` 两处修正 + AttributeError 进护栏 + 字段级降级信封（单字段缺失不再拖垮整个状态面）。
- **实证**：单测红转绿 + 重启后旧错误零复发（完整活栈证明由 JOURNEY 驱动器运行给出）。

**对用户的意义**：登录风控与爆破监控从「纸面存在」变成真实在跑；多轮对话里「我刚才说的」不再被忘掉重问；AI 的用户状态聚合第一次真正有货——三条都是从 0 到 1 的复活，而不是从 60 分到 90 分的打磨。

---

## 5. 星区重放链：183/183 真实 LLM 判定，VOID 大面积→6

**问题**（SECTOR-AUDIT，wt147）：星图知识节点大面积 VOID（修复时点演示库 173 节点中 completed-VOID 27 + pending-VOID 19；COLDSTART 早期快照 29/129 形态一致），且根因是**回填队列恒满丢弃**：`[QueueBackpressure] drop dispatch queue=glm_batch depth=200 cap=200` 实证 19+ 条。三个生产面缺陷叠加：① completed-VOID 节点被永久重选（无 status 门槛）——LLM 判定确属 VOID 的已完成节点永远命中重选，形成永久重复入队源；② 无在途去重（0.7s/12s 内两次 enqueue 同用户 24 节点实证）；③ 消费端 worker 缺位。

**修法**：选择面排 completed（存量修正走重放不走热路径）+ Redis 在途去重（TTL 600s 可配）+ 丢弃显式降级（不再无声，也不死锁）+ 幂等重放脚本 `scripts/devtools/replay_void_sector_backfill.py`（进程内直调、不占背压额度、dry-run 只读）。

**实证**：重放实跑 **183/183 节点真实 LLM 星区判定**（qwen3.8-flash ~1.5s/节点），星图分布收敛为 **WISDOM 200 / TECH 87 / CIV 25 / COSMOS 10 / LIFE 9 / ART 8 / VOID 6**（残余 VOID=信息真不足的节点）——星图扇区多样性恢复，SECTOR-AUDIT 全闭环。

**对用户的意义**：知识星图从「大片未知灰区」变成可读、可导航的学习地图；考纲薄弱点在星图上第一次真正可辨（配合 GALAXY-KW 的关键词投影与 GRAPH-GRPC-SHAPE 的经网关全链可见契约）。

---

## 6. 光子经济诚实链：combo 光子黑洞 + 首胜唯一索引

这一链回答的是「奖励系统是否诚实」——学习激励产品的经济账本必须分毫不差。

### 6.1 combo 光子黑洞（TOUR 旅程中发现，黑洞级 P1）

- **症状（活栈实证）**：任务完成后成就解锁日志连篇 `Granted 30 photons ... old=20 new=50` 出现 **18 次**，但余额/流水**纹丝不动**——每次发放都在随后的事务回滚中蒸发，连击加成 100% 失败；截断的 INSERT 毒化 asyncpg 事务→同批全部发放回滚→事件重试死循环→归档端点连带 500。两轮旅程实证余额卡在 1500/2330/2560 台阶。
- **根因（双缺陷叠加）**：① combo 去重键 `achievement_combo:{uuid4()}` 长 53 字符，超出 `related_item_id` **VARCHAR(50)**——PG 上每次必炸 `StringDataRightTruncation`，而 **SQLite 单测不 enforce 列宽所以 6 用例全绿（假绿）**；② 异常被 except 吞掉后经 loguru 打 `%s` 占位——loguru 不认 `%s`，异常原文整个丢失（"光子丢失必须可见"的可观测性自身不可见）。
- **修法**：键截短为 `achievement_combo:{hex[:16]}`（34 字符，零迁移）+ 同文件 9 处 loguru `%s`→`{}`；修复后活栈复跑 combo 发放入账、10/10 归档 200。

### 6.2 每日首胜唯一索引（PHOTON-IDEM，wt170，`003f71f1`）

- **问题（红证）**：首胜发放是 check-then-insert，2 并发竞态实测**流水 ×2（0→30 两行）而余额只有 30**——审计虚增为 60，审计与余额自相矛盾，「可兑换基数」（审计重放口径）诚实性被击穿。
- **修法**：唯一**部分索引** `uq_photon_tx_daily_first_idem ON (user_id, related_item_id) WHERE related_item_id LIKE 'daily_first:%'`（键域与读侧去重门严格同域；combo 域裁决**否决并入**——生成器构造唯一、无幂等语义可供索引执行）+ 写侧 `INSERT … ON CONFLICT DO NOTHING RETURNING` 原子仲裁（败者返回与读侧门命中逐字段同构的 `deduplicated=True`）。幂等从「缓存+读侧门」双保险升级为三保险，**首胜 30 光子/日的金额语义零变化**。
- **绿证**：8 并发恰一发、流水恰一行、余额恰 +30；迁移存量收敛保留最早真实发放行（演示库 daily_first 域 2 行、域内重复 0）。

### 6.3 全旅程对账（TOUR，9 pass / 0 fail）

6 个新面（计划确认/冲刺小队/自习室/小队榜/自我锚/光子兑换）作为一条真实学生旅程 API 级串测全绿，其中经济面：攒光子余额 20→**5050**（确定性可重复）；**审计流水重放基数=5050 与余额对账相等**（四收入类型+首胜/combo、transfer_in 排除）；兑换 3000 成功 `entitlement=pro` 到期 +7 天、余额精确扣减、`redeem_pro` 流水恰 1 条、**二次兑换 409 月顶幂等**；DB 直读 `users.entitlement='pro'`。

**对用户的意义**：努力攒的每一分光子都在账上；「可兑换基数」重放口径与余额从此不可能自相矛盾——这是「学出会员」变现链可信的前提。
**附带诚实发现**：兑换价 3000 对真实学生≈**100 天**诚实积累（日均收入 ~30-80 光子），可达性待产品校准（已立卡建议：800-1200 或首月梯度）。

---

## 7. GAIN-EVAL（进行中）：增益证明，尚无数字

舰队日志（11:3x 派卡，wt198）：对用户第一性原理问题的直接回应——**memory/画像/向量/星图的增益从未被系统证明**。GAIN-EVAL 建消融评测资产：开关盘点 + 20 场景三类依赖 + 多臂运行器 + 确定性判分优先；判定规则事先钉死：**B 臂（关依赖）在依赖场景劣于 A 臂 = 正增益证明；B≥A = 负增益红旗**；零产品改动、不切流。

**现状如实标注：wt198 在途，尚无任何增益数字。本战报不为其预支任何结论——在它跑完之前，「Sparkle 的记忆/星图比裸用 GPT 好」是一个合理假设，不是已被证明的事实。**

---

## 8. 诚实边界汇总（评委会版）

1. **J4-J6（次日计划适应）是待判不是已过**：判定等真实跨日夜（次日门设计使然——伪造时间线即违诚实红线）；仪器已闭合。
2. **CP-05 复习命中率阈值面不可证**（API 级 performance 为人设自报、n 小、单日），只有机制面 pass；CP-06/07/08 待 Day4-7 相位。
3. **GAIN-EVAL 未跑完 = 增益尚未证明**（§7）。
4. **GRADE-AB 成本/时延为估算面**；gate① 恰在 3.0pp 阈值边缘（分歧清单已存档可复核）；价格快照 2026-09-22，落地前以 dashscope 现价复核。
5. **TTFT 探针样本量 7 条**，单实例串行，非压测；通用链 1.05-2.06s 为当时活栈两次实测，不代表 P99。
6. **兑换价 3000 光子的可达性未校准**（诚实日均 ~30-80 光子→约 100 天），「学出会员」对免费学生当前实际不可达，已登记待产品裁决。
7. CP-98（真人自报）/CP-99（真实考试成绩）在 API 级**永不判**（frozen unsupported）——不冒判是这套仪器的第一原则。

---

## 9. 溯源索引

**v3-output 报告**（均在主仓，只读）：
- `TTFT-PROBE/REPORT.md`（7 条逐帧时间线、30.6s 基线、两簇根因、asyncio.timeout 死码）
- `TTFT-CFG/REPORT.md`（enable_thinking 分档裁决、wire 级断言、planner 3s、前置门 FAST 化）
- `GRADE-AB/REPORT.md` + `B-QWEN/REPORT.md`（假设 A、100 题包、gate 冻结）
- `JOURNEY-DRIVER/REPORT.md` + `live-20260922/evidence/run-summary.json`（counts fail=0、CP 表、次日门）
- `INTAKE/REPORT.md`、`INTAKE-IDX/REPORT.md`、`INTAKE-TEMPLATE/REPORT.md`
- `SECTOR-AUDIT/REPORT.md`（队列恒满根因、审计 INSERT 修复、重放方案）
- `TOUR/REPORT.md`（+ `TOUR/evidence/`：9 pass 旅程、combo 黑洞实证、对账 5050）
- `PHOTON-IDEM/REPORT.md`（红证/绿证、索引裁决）
- `SIDECAR-JOURNEY/REPORT.md`（双层测试、变异验证）
- `PROD-LOG/`、`PROD-FIX-1/`（两 P1 巡检与修复）

**运行证据**：
- `/tmp/grade_ab_full/grade_ab_run_20260923-005550.json`（GRADE-AB 全量 100 题双臂原始判定，pack_sha256 `fc979182…`、prompt_sha256 `c344e7b8…`）

**舰队日志**（`v3/.sparkle_v3_fleet_state.json` notes，活栈实锤的记录源）：通用链 2.06/1.05s@`b0a3b05f`、fast-track 1.26s@`63ca1517`、fact 投影 0.6s@`7454f484`、GRADE-AB 全量判定与切流@`838494ad`、SecurityMonitor 首启@`9ba67176`、183/183 重放、intake 自愈 7 条脊柱@`5b912dcf` 轮、J4-J6 blocked、真实 LLM 三轮冒烟@`8f97733d` 轮、GAIN-EVAL 派卡。

**关键 commit**：`d19551a0`(TTFT-PROBE) `b0a3b05f`(TTFT-CFG) `63ca1517`(fast-track done帧) `7454f484`(NBP-6 投影) `308400d1`(CP-01) `39045ad6`(CP-03) `ed31944f`+`418f3493`(GRADE-AB 资产) `838494ad`(PRO 档切流) `a2506361`(PROD-LOG) `9ba67176`(PROD-FIX-1) `bef7ae07`(键作用域 2 行修复) `8f97733d`(SIDECAR-JOURNEY) `5b912dcf`(INTAKE-TEMPLATE) `003f71f1`(PHOTON-IDEM)

**口径**：`v3/FLEET-BRIEF.md`（口径词典：冲刺完成度/自我锚/在场/可兑换基数/星图可见；四线现状）。

---

*编纂：C 纵队 C-REPORT（wt203）。零代码、零测试、主仓只读；本文全部数字未做任何外推或美化，待判/未证明项已逐条标注。*
