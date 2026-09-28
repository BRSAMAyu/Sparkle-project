# V3 全量状态报告 —— V4 设计唯一入口文档

> **文档契约**：V4 设计者只看这一份文档做判断。因此本文档承载：V3 真实意图、全部实施细节、完成度证据、已知问题与诚实边界。持续更新（协调会话每轮维护），版本号+日期在文首。**本文档只写有三源证据（git 主干 SHA / 独立审查 receipt / 运行级实测）支撑的事实；推测与待验证项显式标注。**
>
> **终门结果：PASS（2026-09-28 08:19，JOURNEY 7/7）**
>
> **当前版本**：v0.8（2026-09-28 04:36——冷读可用性轮：名词表 24 条/O-Q 线长句拆解/§10 散点收敛/changelog 时序修复；v0.7 已修 5 项 P0）
> **维护者**：Sparkle v3 舰队协调会话（主会话）｜**权威数据源**：v3/.sparkle_v3_fleet_state.json notes 流、v3/07_tasks/tasks.json（102/107 已核正）、v3/06_agent_fleet/DYNAMIC_ISSUES.md（FIX 台账 364 行，口径=状态格行首枚举）

---

## 0. 阅读指南与诚实声明

- **完成度判据**：tasks.json status + fleet done 名单 + git 主干交付 SHA 三源核验（wt759 全量核验报告 v3-output/WT759-RECON/report.md，逐卡 SHA 证据链在案）。**零假账**：90 张 fleet 声称 done 全部有主干交付。
- **验收模型（ADR-0011，原文在 sparkle-cosmos 仓 docs/，本仓无副本）**：普通任务 DONE = 独立未参与会话审查 + 当前集成 SHA 可失败测试；高风险 = 2 份独立审查。worker 自称完成不算完成。
- **诚实红线（贯穿 V3 全程执行）**：不以 Mock/人工改库冒充模型结果；无真实凭据/设备时交付阻塞证据；报告数字以实测为准（「2 秒」「59 项全绿」类旧报告宣称不当作实现事实）。
- **本文档的已知局限**：各产品线的「用户体验级」验证深度不一（多数卡有 headless/单测级证据，三端实机走查类受设备限制转 HUMAN_INBOX）；性能数字仅在标注处有真模型 bench 支撑。

## 0.5 名词表（冷读者必读，24 条）

- **wtNNN**：舰队 worker 会话编号；交付物在 `v3-output/WTNNN-<任务名>/`，工作分支 `agent/<node>/wtNNN/<task>`。
- **门 / 门后**：day7 JOURNEY 终门（2026-09-28 08:00，/tmp/gate_day7.py）；「门后」=终门后的集中执行窗口。
- **TCC**：macOS 隐私与安全性授权（用户勾选 ZCode 辅助功能权限+重启 App）——O-01 浏览器取阿里云凭据的前置，**非云侧机制**。
- **L0/L1/L2/L3（E 线口径）**：请求分层——L0 直答/L1 轻量/L2 中量/L3 重（SLO 六项挂其上）；「L0 首帧前移」=L0 层首帧优化。
- **L1–L5（U 线口径）**：UI 质量闸门层级（L2=双审查 APPROVE、L4=闸门注册、L5=headless 契约层，详 U-line.md）——**与 E 线 L 层不同体系**。
- **台账**：v3/06_agent_fleet/DYNAMIC_ISSUES.md，V3 缺陷/动态登记表；FIX-NNN=行号。
- **销账**：任务卡状态 TODO→done 并留三源证据（非删账）。
- **三源核验**：tasks.json status + fleet done 名单 + git 主干交付 SHA（wt759 全量一次）。
- **五源核验**：三源+代码开文件亲证+测试实跑（深挖章口径）。
- **GJ**：Golden Journey，Q-02 的 20 条核心旅程终验用例（GJ01-GJ20）。
- **M1-M4**：JOURNEY 日循环四个里程碑门（定义在 fleet state notes 流）。
- **R2 / receipt**：第二轮独立审查 / 审查回执文档（REVIEW_RECEIPT.md）。
- **INV-1..7**：O-05 restore 一致性校验器七条不变量。
- **诚实 FAIL**：验收卡合法交付形态——评测照实判 FAIL 且失败证据原样保留（Q-04/Q-02 行使过）。
- **contract-simulation**：Q-01 260 场景判定语义——跑确定性参考实现而非真模型全链（「260 全绿」≠「产品全绿」）。
- **orphan-by-design**：交付时如实留白的未接线面（带豁免条件，如「群 AI 面接入时接线」）。
- **HEAVY/MEDIUM/LIGHT**：卡资源档位（并发/时长约束；HEAVY 同期至多一张）。
- **满编铁律**：舰队恒 6 并发槽不空转的调度纪律。
- **ADR-0011**：v2 执行包架构裁决（原文在 sparkle-cosmos 仓 docs/，本仓无副本）。
- **DoD**：Definition of Done，v3/V3_DEFINITION_OF_DONE.md（V3-0..V3-10 逐 gate）。
- **SLO / tier 塌缩 / TTFT**：服务级目标 / LLM 分层路由失效全落同档 / 首 token 时间。
- **ratchet（棘轮）**：质量基线只许变好不许回退的门禁。
- **shadow/live**：新能力三态发布 off/shadow/live；shadow=影子运行不生效可观测。
- **fail-closed**：异常时拒绝服务而非放行（安全默认）。

## 1. V3 是什么（真实意图）

**一句话**：三层架构 AI 学习成长系统（Flutter Mobile → Go Gateway :8080 → Python AI Engine gRPC :50051 + FastAPI :8000；PG16+AGE+pgvector/Redis/MinIO/Celery）的参赛冲刺版本——把「AI 陪伴学习成长」从可用推向可交付的产品完整度。

**V3 的核心主张（来自 MASTER_DESIGN 与卡面体系，107 卡 14 条产品线（tasks.json stream 权威口径；文档早期误记 13，v0.7 勘正））**：
1. **主链**：任务卡住 → 澄清/用户纠正 → 实际任务改变 → 重开后可见 → 完成反馈（学习成长的真实闭环，不是聊天玩具）
2. **Human/Agent/Hybrid 执行模型**：AI 降摩擦但不偷走目标（J-06 旗舰旅程；X 线 ActionPlan 契约族）
3. **Aurora 受限自适应**：有边界的个性化（A 线 8 卡：决策契约/干预目录/摩擦诊断/有界策略补丁）
4. **State/Memory/Knowledge/Events 四分上下文**（C 线 8 卡 + M 线 10 卡）
5. **可恢复 Run**：chat 轨去重命中改返结果（FIX-334→wt640 修复链），跨重启幂等（461/469/487 耐久链）
6. **真实结果与可纠正记忆**：证据融合（evidence/ 贝叶斯族）、Memory Epoch/Provenance（M-07/M-08）
7. **Galaxy 星系可视化**：Evidence-aware 的掌握度成长地图（G 线）
8. **诚实性作为产品价值**：失败可见、不静默兜底、模板不冒充模型输出（贯穿 FIX 族的修复方向）

**阶段目标**：内部交付 10/4，官方截止 10/7（天马 hackathon）；JOURNEY 七日真实驱动验证 **7/7 收官（day7 终门 PASS 2026-09-28 08:19，升栈当日代码后 M1-M4 全 200，state day7_done+自动备份，/tmp/day7_gate_run.log 在案）**。本文「门后」=终门后执行窗口（已开始）。

## 2. 系统架构现状

```
Flutter Mobile (Riverpod+GoRouter, :app)
  └─ WS/HTTP → Go Gateway :8080 (鉴权/限流/CQRS worker/WS 代理/幂等去重)
       ├─ gRPC → Python AI Engine :50051 (ChatOrchestrator/AgentService.StreamChat)
       │            └─ FastAPI :8000 (REST API 全量)
       └─ PostgreSQL 16 (AGE 图 + pgvector) / Redis (streams+pub/sub+cache) / MinIO / Celery
```

- **proto 单一事实来源**（buf 管理，三语言生成；含 GetRequestResult 回放 RPC）
- **DB schema 唯一入口 Alembic**（当前单头 wt598_20260927）
- **CQRS 侧**：community/galaxy 两组 BaseWorker 消费 Redis streams；outbox/DLQ/processed_events 三清理器齐备（487 后）
- ⏳ 深挖中：各模块内细节（本节将随轮次扩充为模块清单+关键设计决定）

## 3. 107 卡全景与完成度

**当前：102/107 done**。三源核验（wt759，2026-09-28）：15 张三源齐 + 84 张销账核正；此后 S-01（wt763 APPROVE）→100、O-05（wt782 APPROVE+销账前置全履）→102。余 5 张见下表。

**剩余 5 张（102/107，2026-09-28 03:42）**：
| 卡 | 状态 | 阻塞点 |
|---|---|---|
| J-02 Onboarding: Value Before Profile | PARTIAL（wt764 交付+wt282 增量在主干；simulator 证据卡门后执行） | FIRST_3_MINUTES 清单：fresh install+3min 脚本+截图（需设备） |
| E-08 AI Stack 集成 Bench | partial（wt372 104 条真模型 bench 已交付 a1418084；wt755 L0 首帧前移在分支待门后集成） | 真模型复测（有 key 环境）+ review receipt |
| O-01 公网 Staging HTTPS/WSS 一键部署 | 未启动 | 云凭据（用户 TCC 授权解锁后立即可做；ECS i-2ze439t934c2gsdqm778 已配） |
| Q-07 Chaos/Recovery/Offline/Restore Storm 终验 | 未启动 | 依赖 O-01 |
| Q-08 V3 Final Gate Audit / Commercial RC | 未启动 | 压轴（Q-07 后；day7 终门 09-28 08:00 先行） |

已销账补记（均为 v0.5-v0.5.1 时点）：
- **O-06**：wt765 交付 + wt771 审查 APPROVE（真栈 shadow 回滚事故实录=验收模型教科书样本）；ops 面 OPS_SURFACE.md。
- **O-05**：wt773 交付 1680d16c + wt782 独立审查 APPROVE（14/14 复跑 + 变异 M1/M1b/M2/M4 红 + CLI e2e rc=1）。
- **O-05 销账前置三项全履**：①被撞号顶丢的原 FIX-504 行补登为 FIX-531（FIXED@1680d16c）②FIX-505 范围纠偏（prod compose 已 `--dir /data`，真错位面=dev compose；AOF yes + RDB-only backup 新残差转 ops）③FIX-532 审查附带四项登记（bash3.2 空数组崩溃等）。

**各线完成度**（14 线全量表见 wt759 报告）：A 线 8/8｜B 线 6/6｜C 线 8/8｜D 线 6/8（D-07/D-08 已销账✓ 实为 8/8——待复核）｜E 线 7/8｜G 线 5/5｜J 线 7/8｜M 线 10/10｜O 线 6/7（O-05/O-06 已销账；余 O-01 卡 TCC）｜P 线 6/6｜Q 线 6/8（Q-04 诚实 FAIL 形态计 done，修而不复跑见 §4 Q 线）｜S 线 5/5｜U 线 10/10｜X 线 10/10
（⏳ 此表 v0.2 将逐线复核修正——D 线两卡的销账依据需重列）

## 4. 各线深度状态（14 线全部深挖完成，v0.6）

每线将包含：**意图（卡面目标）→ 实际交付（关键 SHA+功能面）→ 验证证据（测试/review receipt/运行级）→ 残差与已知限制 → V4 注意点**。

- **B 线 Baseline（6/6，已深挖，详章 v3-output/WT769-DOC-BC/B-line.md）**：V3 诚实性红线第一执行者——4 张零产品码审计卡+2 张 harness 卡；B-02 直接/间接催生 FIX-01/256/257/258/329-331，B-06 催生 FIX-259/260/275/276/289/291/356。B-01 重开为 759 模块四态审计（690 ALIVE/55 PARTIAL/12 DEAD/2 ORPHAN）。**残差**：B-02 红测未入库（reviewer 已抓）；FIX-256/290/291/385 OPEN；community_context_boundary 528 行零生产 import（orphan-by-design 豁免——**V4 群 AI 面必须接线**）；B-05 成本表/能力矩阵为旧时点。
- **C 线 Context（8/8，已深挖，详章 v3-output/WT769-DOC-BC/C-line.md）**：10 个模块主干生产消费方逐一亲证**全活**，有跨卡复用网（J-06 复用 citation_markers 做 503 诚实失败）；13 测试文件 235 测试函数。**「就绪未激活」面（交付时如实留白，非缺陷）**：C-05 冲突定向澄清参数在但 validation_engine.py:361 未传（开文件亲证）；C-08 消融为 mock hermetic（56 场景×4 臂）真模型效用未做；C-01 proto 零触碰→跨语言 parity 未发生。
- **A 线 Aurora（8/8，已深挖，详章 v3-output/WT774-DOC-AJ/A-line.md）**：逐卡 SHA 全链主干亲证。**A-05 边界机制五层硬约束面开文件亲证**（六面白名单 sha256 双钉——「改 prompt/代码/模型参数」无合法 surface 名走不到任何写路径、payload 键值双封闭、patch 仅作确定性决策输入、生命周期状态机封闭、证据门只认真源；策略版本进缓存键）。**A-08 四臂终态（V4 最重要发现之一）**：方法论可信（真实服务面+确定性判据+judge 0 次+--verify-repro），但**修后终值=accuracy 0.45/0.55/0.45/0.30（臂序 full/no_memory/no_experience/fixed_policy；效用 full −9.2/fixed −24.8）且 no_memory 臂（0.55、效用 0.0）双指标反超 full（0.45/−9.2）——模拟人口上记忆面净贡献为负**（早前流传的 0.65 vs 0.30 是修前值）。A-06 Why-this 数据流真实（真实检索 receipt 驱动，零新写路径）。残差：shadow/live 对比机制在库但零次真实运行记录。
- **J 线 Journey（7/8 交付+J-02 PARTIAL，已深挖，详章 v3-output/WT774-DOC-AJ/J-line.md）**：**七段验证深度分层**——真驱动=J-01（macOS 真后端 5 persona+101 截图）/J-03/J-05（真模拟器 32 截图）/JOURNEY 日循环；J-04/J-06 的「真实」在工具链层（真实 ToolExecutor+真实检索零 mock），独立真模型运行记录未定位；三端实机全线转 HUMAN_INBOX。**JOURNEY 门循环（M1-M4）验证的是 J-03 面+任务生命周期日界闭环，不含 J-04~J-08 旗舰旅程——V4 引用时不得扩展口径**。J-01 机会图：5/11 项已修、6 项（O2/O4/O6-O9）如实留白零台账跟踪（O6 备考文案仍在主干）。J-02=PARTIAL（工程面合格，唯一缺口卡面明列 simulator 实测，补证卡排门后）。
- **M 线 Memory（10/10，已深挖，详章 v3-output/WT770-DOC-MX/M-line.md）**：Memory Epoch/Provenance 是**真实数据流**（代码亲验）——M-01 契约模块派生五型/七态/scope（唯一新列 epistemic_class/superseded_by_id/epoch）；M-07 统一失效管线四动作（状态+审计+epoch bump+memory.invalidated 事件）**同事务原子**，读侧 epoch 门 fail-closed，「删偏好永久复活」主通道关闭（红→绿实证）；M-08 `/memory/provenance/*` 七路由+why-this 按 receipt 查；M-10 chat 回执深链+五面客户端级联失效。**M-09 是缺陷发现器**：真模型探针（qwen3.8-flash 真实 API 25 次硬预算）4/5 稳定通过、P01-D1 0/5 实锤 FIX-36（渲染器不渲染偏好值）；82-case 门禁曾 RED 20 失败实锤 FIX-35——双 P1 均修，门禁现 82/82。关键取舍：语义层（存储门/自检）默认关，生产决策面=规则层；生产降档率 66.67% 由 M-05 主导。M 线核心 273 用例实跑绿。
- **X 线 Action（10/10，已深挖，详章 v3-output/WT770-DOC-MX/X-line.md）**：X-01 契约（43942d23）→X-10 E2E（3b5a99bc，含 X-05B/P2 增量）。**Human/Agent/Hybrid 真模型证据面分层**：85 场景盲评与 X-10 77 场景（77/77、allocation 100%、high-risk auto=0、false success=0）均为规则层+服务层（`real_llm_calls=0` 显式断言）；**真模型证据**在 E-04 五面探针（收敛轮 15/15 含注入对抗）、J-04（LLM 建议 agent 被分配策略拦回=学习守卫生效）、J-06（真实 ToolExecutor 检索零 mock）、JOURNEY day1-6 真驱动；三端实机转 HUMAN_INBOX。**V4 教材级考古**：X-06 合入当日 chat 管道 100% 断（models `__init__` 漏注册，热修 f2e9f22e）——大改后冒烟必须当日；幂等洗白三轮修复链（FIX-40→417→447）；FIX-330 裁定 AgentRun/AgentToolCall/outcome_ledger 为生产三账本。X 线核心 403 用例实跑绿。
- **D 线 Data（8/8，已深挖，详章 v3-output/WT776-DOC-DE/D-line.md）**：契约先行、读模型优先。D-01 词表 40 名 sha256 本档独立复算吻合（29 live/10 reserved/1 observed_unregistered 诚实设计）；D-03 五维真实表聚合+celery beat 在册；D-07 三类洞察卡 **goal-progress 有真数据、friction/helped 结构就绪生产零数据**（供给断链=FIX-507）；PredictiveInsightsCard 假精确面整体删除；D-08 双臂配对闭环 10/10+`--verify-repro` 可复算。
- **E 线 AI（7/8+E-08，已深挖，详章 v3-output/WT776-DOC-DE/E-line.md）**：**证据必须按真模型/规则层/结构就绪三层分开看**——E-04 是真模型证据最厚卡（收敛 15/15+注入三修）；E-03 三段收口（部分达成→FIX-439 裁决 b 字面收窄→残差移交 E-08）。**E-08 完整性能图景**：修前=wt372 104 条 bench（L3 TTFT p95 113s、tier 塌缩 85/85、SLO 2/6）；已修=tier 塌缩+计量盲区+L3-ACK（400 样本 0.06s）；未修=L0 直答缺位/L2 total ~48s；复测路径=Q-06 同构 bench+wt755 集成后重采。
- **U 线 UI（10/10，已深挖，详章 v3-output/WT775-DOC-UPSG/U-line.md）**：L2 双审查 APPROVE 达成；L4 闸门面达成但**注册表仅 8 seam**（chat/galaxy 主屏未接闸）；L5=headless 契约层（11 用例+允许差异表），**45 张真机截图矩阵是就绪清单非已采集证据**。DS.* 约束力=守卫冻结型（22,129 处引用+双 ratchet）；chat 余 80 处 fontSize 字面量存量未迁移。GOV-015/WS6 删除（~3,958 行）全是未接线孤儿面，UI 健康度无损。
- **P 线 Proactive（6/6，已深挖，详章 v3-output/WT775-DOC-UPSG/P-line.md）**：**双通道并存**——nudge 家族（真投递）vs P-01 事件管线（已接线但 shadow 默认无环境翻面）。P-01/P-02 数据流全链亲证（7 触发器×10 事件→fail-closed 抑制→四问相关性封闭词表→Prometheus 审计）；零 LLM 是 import 面级红线。P-05 效应量级=seeded persona 模型不可外推真人。
- **S 线 Community（5/5，已深挖，详章 v3-output/WT775-DOC-UPSG/S-line.md）**：S-01 五面真相（M-3 消解、实时走引擎内 ConnectionManager——**多实例是 V4 第一个重设计点**、CQRS community 投影零生产者=FIX-495 三路裁量素材）；S-02 红线守卫在库，orphan-by-design 豁免移除条件=群 AI 面接入（V4 义务）。
- **G 线 Galaxy（5/5，已深挖，详章 v3-output/WT775-DOC-UPSG/G-line.md）**：星图三路写入亲证——**主流量（任务完成 spark）仍走 legacy 时间公式封顶 40**；outcome 走 Kalman（TASK_OUTCOME 0.6/SELF_REPORT 隔离/TIME_ON_TASK 0）；「证据地图」主张真实但打折——**把 X-01 completion evidence 分型接进完成链是 V4 最低成本杠杆**。AGE 真实使用=GraphRAG 读侧活+graph_sync 消费者活，但写侧镜像零生产流量；outcome 撤销→已吸收效果回滚未闭环。
- **O 线 Ops（6/7 done，已深挖，详章 v3-output/WT779-DOC-OQ/O-line.md）**——四要点：
  1. **就绪度必须三层分开看，混读会高估**：机制层（O-02/03/04/07 四卡 09-21 R2 PASS+O-06 双审查链，O+Q 线 445 用例本次实跑绿）＞演练层（O-06 真栈 shadow 回滚、O-05 一次性容器栈——全 localhost 形态，staging 级演练从未发生）＞生产部署层（O-01 零交付，卡用户 TCC 凭据 H-002；/tmp 弹药易失；但工程面准备度其实很高：compose.prod+deploy 六脚本在库）。
  2. **全舰队供血最多的被依赖线**：O-04 entitlement 判官被 O-07 budget_matrix 消费；O-07 背压/安全错误面是 Q-06 修复落点基底；O-06 release manifest 是 Q-08 RC 前身；O-05 INV-1..7 是 Q-07 现成判据——**V4 裁撤任何面前先查依赖网**。
  3. 单卡要点：O-02 trace 脊柱 9 阶段+finish-in-finally 亲证在位，但运行级 GJ 重建证据全库缺一口；O-04 双侧单一判官且 D-REDEEM 扩展存活；O-06 是唯一走完「审查抓真运行级缺陷→补丁→APPROVE」全链的卡。
  4. **O-05 重大发现=备份链此前静默失效**（MinIO 容器无 tar→cron 夜备份从未产出完整包；restore 曾吞 2156 SQL 错=假成功），已修+INV 校验器+GJ03 11/11 演练（详 FIX-531/505/532 行）。
- **Q 线 Quality（6/8 done，已深挖，详章 v3-output/WT779-DOC-OQ/Q-line.md）**——四要点：
  1. **「诚实 FAIL」是合法交付形态且已行使两次**：Q-04 总判定 FAIL（precision 0.0/invalid 硬门×10/overpersonalization 41.67%/uplift 0.0pp 原样交付）；Q-02 首轮 13 PASS/6 FAIL/1 RESTRICTED、0 waive 全转动态卡——全库诚实性教义最重的两个样本。
  2. **「修而不复跑」是 Q 线最大结构残差**：Q-02/Q-04 修复全部闭账但均无修复后全量重跑，终态=首轮诚实判定+逐缺陷修复+局部复验/锁级证据——Q-08 必须显式三选一裁决（补全量重跑/按锁级证据判/NOT_REMEASURED，驱动都在库可复跑）。
  3. 证据形态好于 D/E 线（四产物目录在库、台账零死链）。Q-01 260 场景亲数（integration 54/model 122/simulator 84，V3-001..260 无缺无重）且 **verdict_semantics=contract-simulation 钉死——「260 全绿」≠「产品全绿」**（model 型走 mock-provider、simulator 型是 stub，证据强度按路由分层）；Q-06 L3-ACK 400 样本 7.03s FAIL→0.06s 转、SLO 4/6（L0/L2 FAIL=E-08 族未修）。
  4. **Q-04 uplift 0.0pp + A-08 no_memory 双指标反超=两个独立 eval 同向：记忆/个性化面净贡献未证明为正——V4 最重负面输入，任何「越用越懂我」叙事必须先回答这两个数字**。Q-07/Q-08 执行计划已草案（DoD V3-0..V3-10 逐 gate 证据图+四个预裁决项+release-manifest 缺 git SHA 缺口；FIX-530 系 Q-07 直接前置缺陷建议先修；**详章 §Q.4：v3-output/WT779-DOC-OQ/Q-line.md**）。

## 5. 质量与可靠性态势（FIX 台账模式学）

**台账规模**：V3-FIX-001→534（364 行，FIXED 273/OPEN 60/CLOSED 3/WONTFIX 1+27 行旧格式自由态——口径=状态格行首枚举机器可复算，与 §9 同口径）。**零假账纪律**贯穿：每个 FIXED@ 指针经「集成即纠指」指向主干可达 SHA。

**修复族谱（暴露的系统性弱点与已收口状态）**——这是 V4 最应读的一节：
1. **竞态/并发族**（全收口）：UserStreakStats 三入口（451/457/467+479，uuid5 同源三件套+PG 实证）；aurora 融合跨进程锁（418）；状态估计 claim（193）
2. **关停耐久族**（全收口）：chat 关停批不丢（427）、PEL 滞留重投（461）、幂等闸格式假设（469）、LRU 有界（481）、清理接线（487）——CQRS 全链 at-least-once+吸收闸
3. **代理信任链族**（480/482/483/484 收口）：TRUSTED_PROXY_CIDRS 判据、WS 代理 XFF 追加、dev trust-all 收紧、IP 形态校验
4. **软删/拉黑读面门族**（419/449/465 收口中）：community 读写各面闸门补齐
5. **审计/可观测静默失效族**（491/493 收口）：publish 签名错配被吞→修复+计数器
6. **孤儿代码族**（489/490 PURGE）：不可达屏 3300 行删除（证据链+原子留档）
7. ⏳ v0.2 将补：完整族谱分布统计（P1-P4 数量、按模块热点图）

## 6. 测试与 CI 态势

- **测试规模**（首次完整裁决时点数；当前规模详 §9）：backend ~12,340（139F/12,340P 裁决时）→现 13,799；gateway 692→现 746 测试函数（静态 grep 口径）；flutter 2,636→现 2,628（差值=group 包裹/参数化计数口径，详 metrics.md L131-L132）；integration/e2e 面多层
- **CI：两连绿基线确立（第 23 次 36343384107 + 第 25 次 36350830485，2026-09-28）**——第 24 次红系 wt777 FIX-510 调用形状修复（不在 23 次树）暴露的测试钉旧 bug 形状+ope_gatekeeper 预存孤儿（FIX-537）双问题，均已正修；mypy 基线按 CI 实数对齐 77（本地口径 55）；首绿时点 04:15——22 次失败后洋葱 21 层剥尽（proto 双布局→goimports→PEL 竞态→OpenAPI 重冻结→BA-ROUTES→backend 三分片→flutter→coverage merge→build artifacts→journey smoke）；12 个执行 job 全 ✓（Simulation Benchmark 系 PR 事件专属设计跳过）。**V4 教训固化：从未全量跑过的管线自带腐烂——21 层缺陷没有一层能在部分运行中暴露，V4 初期就应建立全绿基线**
- **mypy 棘轮**：922→132→113→94→91→76→70→**55**（十一批+wt777 探针，零 cast/零 ignore/真 bug 停手登记纪律——顺带挖出 491/492/529 等真 bug；CI 侧口径差异待第 24 次实测对齐）
- **ruff/l10n**：evidence 目录全净；en/zh 10061 键双向零缺失；EN 占位符清零

## 7. 已知债务与未决清单

**待产品/用户裁量**：FIX-495（community post CQRS 闲置接线：零生产者零消费者，S-01 证实现状实时走引擎内进程——裁决建议：留档 post-RC 接线或拆除）；EXACT 带 8 草稿键（chatConfidence×3/chatCompletion×5）；FIX-465 已裁决派修中。
**等用户解锁**：H-001~009（HUMAN_INBOX：FIX-293 生产回填、云端 TCC、Dependabot #111-113、T36 B/D、49 冻结键、FIX-97/290、FIX-189 env 审计；**H-009=真机段汇总行**——U-09 45 张矩阵/G-05 FPS 批/U-08 a11y/B-04 走查/U-06 simulator 段/WT394 波次箱等 10 子项，wt783 回填、20 锚点零死指针，详 v3-output/WT783-HUMANINBOX/notes.md）。
**技术债登记**：KNOWN_CODE_DEBT_LEDGER（动统计/排行榜/card_protocol 前先读）；FIX-443③ stage34 死绑定（稳定性优先缓修）；FIX-375/379②③（post-10/4 结构性）。
**挂起待集成**：wt755 分支 938e845c（E-08 SLO L0，热路径门后集成；其新登记撞号项改 498——**预编号**，集成时才建行，当前无台账行非断链；wt785 预审 APPROVE 含重编号三处同步点）。

## 8. 诚实边界（V4 设计者必读）

1. **LLM 面**：CI/多数测试环境无 key→demo 模式路径广覆盖；真模型证据集中在 E-08 bench（104 条）、E-04 五面探针（收敛 15/15 含注入对抗）、M-09 探针（qwen3.8-flash 真实 API 25 次硬预算）、A-08 四臂（真实服务面）与 JOURNEY 驱动（day1-6 实测）。
2. **三端实机**：Android/Web/macOS 真机走查类验收转 HUMAN_INBOX（无设备/浏览器权限）；mobile 验证以 widget test+analyze 门为准。
3. **性能数字**：仅 §4-E 线标注的 bench 有真模型支撑；「2 秒」类旧报告宣称不采信。
4. **云端部署**：未部署（O-01 卡凭据）；本地栈形态是唯一已验证运行形态。
5. **演示数据**：guest 登录播种 6 演示群+演示用户（friend 行共享）；journey 主用户 ns001 数据为真实七日驱动。

## 9. 度量快照（2026-09-28 03:25，wt780 全本机实测@9a4ea3d4，详 v3-output/WT780-METRICS/metrics.md）

- **代码规模**：手写生产 ~113.5 万行——backend/app 1,356 文件/533k 行；mobile/lib 手写 1,187 文件/564k 行（排除 vendored 与生成物）；gateway 105 文件/38k 行（+141 测试文件 27k 行）。测试文件：backend 1,443 + gateway 141 + mobile 518。
- **模块依赖**：35 顶层包/192 边/34 对双向依赖；最重边 services→core 314、services→models 310；**core↔services 双向对是 V4 分层解环首批对象**。
- **测试分布**：backend/tests 收集 **13,799 用例 0 错误**（unit 占 70.8%）；tests_e2e 36+1 收集错误（死文件 FIX-528）；gateway 746 测试函数（静态 grep；运行口径 692，差值详 metrics.md L131）；flutter 2,628（静态）。测量卫生：worktree 需先补 gen 否则数字失真。
- **FIX 台账**：364 条数据行，**FIXED 273（75%）/OPEN 60/CLOSED 3/WONTFIX 1**+27 行旧格式自由态（计数口径=状态格行首枚举，机器可复算：awk -F'|' 取 NF-1 首词）；P0 5/5 全闭；P1 OPEN 仅 **FIX-530**（engine FastAPI 进程被 Redis 瞬时断连杀死——billing 消费循环异常上抛整进程退出，2026-09-28 03:02 实录死亡 30 分钟，心跳探活抓获，已复活+门后派修；「唯一 OPEN P1=FIX-53」系 FIX-53 行混合状态格机器误报，FIX-512 已当场纠指收口）；底重金字塔（P3 占 44%——分母=全部数据行）。热点 top4：services 90/mobile 68/models 45/orchestration 45（完整 top10 详 metrics.md FIX 统计节）。
- mypy **55**（本日 922→70→55：wt777 集成 −6 + wt778 批十一 −15，合并态冷缓存实测与台账逐数对账；CI 侧 77=第 23 次首绿实测、基线已对齐 77；与本地 55 差 22 条系 runner 平台 python/mypy stub 代际差，方向稳定）；卡片 **102/107**（O-05 已销账：wt782 独立审查 APPROVE+前置全履）；本地栈三容器 healthy、gateway 200+engine /health 200（engine 03:02 曾死 30 分钟已复活，见 FIX-530；生产部署 N/A）。

## 10. V4 设计建议输入（v0.8 收敛版）

初版要点（基于 V3 执行观察）：
1. **结构性限制**：不增加 Java 后端/双数据库/第二套身份记忆系统（本阶段资源选择，ADR-0011）；proto→生成物/Alembic 唯一入口的治理结构值得 V4 延续
2. **高杠杆机会**：E 线首帧前移的 L1/L2/L3 已勘察未实施（StreamChat 前奏/门并行化/拥塞治理——wt755 notes 有完整归因）；Galaxy evidence-aware 接线（G-02 后的深化）
3. **避免重蹈**：账本三源漂移（V4 应从第一天用主干 SHA 记账）；worker 报告与实际交付的错位模式（本档 §5 的验收模型已解决，V4 沿用）；CI 从未完整跑过的管线自带腐烂（V4 初期就要全量绿基线）
4. **散点收敛清单（v0.8 自 §4 十四线提炼）**：①记忆/个性化净贡献未证为正（Q-04 uplift 0 + A-08 no_memory 反超）——任何相关叙事先回答这两个数字；②数据飞轮中段断链（FIX-507：D-05 lifecycle 写路径零生产调用方，friction/helped 洞察卡生产零数据）；③O 线依赖网裁撤前必查（§4 O 线第 2 点）；④orphan-by-design 接线义务清单（community_context_boundary 群 AI 面/J-06 hybrid 旅程面 FIX-535/C-05 冲突澄清参数/C-08 真模型消融）；⑤S 线多实例重设计（实时面走引擎内 ConnectionManager）；⑥G 线最低成本杠杆（X-01 completion evidence 分型接进完成链）；⑦单进程栈可用性单点（FIX-530：进程守护必上）；⑧CI 从未全绿=管线自带腐烂（V4 初期建全绿基线）；⑨账本三源漂移（V4 第一天起主干 SHA 记账）；⑩worker 报告错位模式→验收模型（READY_FOR_REVIEW→receipt）沿用；⑪A-05 五层硬约束面范式（六面白名单 sha256 双钉）值得延续到 V4 所有边界机制

---

## 更新日志

（排序=新→旧；v0.1 时间戳原误写 03:00 已按 git 实取修正为 02:03；v0.2-v0.5 段时间系撰写估写±数分钟，v0.5.1 起为 commit 实取）

- v0.8（2026-09-28 04:36）：**冷读可用性轮**（wt787 审计 P1 批量修复）：新增 §0.5 名词表 24 条（wt 代号/门/TCC/双 L 层体系/诚实 FAIL/contract-simulation 等——G2/G3/G4/G5/G7/G8/U2 七项一并治）；O/Q 线与「已销账补记」三段超长句拆编号 bullet（U1）；§6/§9 测试规模桥接+口径补全（C6/G9）；§8.1 真模型清单扩至 E-04/M-09/A-08（C8）；§10 第 4 条 ⏳ 兑现为 11 点散点收敛清单（G6）；changelog 时序重排+v0.1 时间 git 实取修正（C7）；Q-07/Q-08 计划路径/ADR-0011 出处补指针（G10/G11）。P2=15 项留后续打磨。
- v0.7（2026-09-28 04:20）：**P0 勘正轮**（wt787 冷读审计 34 条中 P0=5 全修）：①文首元数据 v0.5→v0.7 与全文对齐（102/107、364 行）；②§3 头条 100/107→102/107（wt759 时点数未标时点的病）；③**线数 13→14**（tasks.json stream 权威=14，「13 条产品线」系计数错误，历史更新日志原文保留不回改）；④§5/§9 台账数字统一为同口径 364 行 FIXED 273/OPEN 60（并写明机器可复算口径）；⑤A-08 四臂终值补臂名与指标口径（照抄 A-line.md:146 原始锚）。附修：FIX-498 标注预编号非断链、P/S/G 详章补链接。P1=14/P2=15 清单见 v3-output/WT787-DOCAUDIT/report.md（门后打磨轮执行）。
- v0.6（2026-09-28 03:54）：**13/13 线深挖全部完成**——O/Q 收官章并入（wt779 五源逐卡核验：主干 SHA 祖先亲证+代码开文件+O/Q 线 445 用例实跑绿+产物抽读+台账逐行复核）。§3 修正 Q 线实为 6/8（Q-01~Q-06 全有交付；「Q 线 1/8」系陈旧口径）。**FIX-512 当场收口**：FIX-53 行「OPEN 补记FIXED@」混合状态格系机器误报源，「唯一 OPEN P1=FIX-53」不成立——收口后 **P1 OPEN 仅剩 FIX-530**。FIX-511 闭账（wt783：H-009+10 子项入中央箱，20 锚点零死指针，补漏 5 组含 WT394 波次箱全量）。新登 FIX-513（42 feature portfolio 双真源词表分裂——DoD 五态 vs MODULE_PORTFOLIO 扩展词表，V3-0「唯一状态」文档层不可直接满足，Q-08 前须裁决）/FIX-514（O-05 交付 commit 幻影号勘误：号 504/520 均无效，检索锚=commit 1680d16c 本体）。台账终态 362 行 FIXED 273。
- v0.5.1（2026-09-28 03:42）：**O-05 销账→102/107**（wt782 独立审查 APPROVE 附前置全履：FIX-531 补登被撞号顶丢行 FIXED@1680d16c、FIX-505 范围纠偏 dev compose+AOF 新残差、FIX-532 四项附带登记）；wt781（FIX-506 演示群标记）+wt778（mypy 批十一 76→61）集成收口，**合并态 mypy 55**（70−15 逐数对账）；**FIX-530 登记**（engine 03:02 被 Redis 瞬时断连杀死、30 分钟后心跳抓获复活——单进程栈可用性单点，V4 需进程守护）；合并态测试 288 过+1 环境错配归因（integration 套件 PG 预建 schema 口径，conftest:58 create_all 注释在案）。
- v0.5（2026-09-28 03:05）：**A/J/U/P/S/G 六线并入**（wt774/wt775，11/13 线完成，O/Q 收官批在航）。**A-08 终态数字修正**（0.45/0.55/0.45/0.30，no_memory 臂双指标反超 full——模拟人口上记忆面净贡献为负；早前 0.65 vs 0.30 系修前值）；A-05 五层硬约束面亲证；JOURNEY 门循环口径限定（不含 J-04~J-08 旗舰旅程）；U 线 L4/L5 诚实分层；P 线双通道并存；S 线多实例重设计点；G 线「证据地图打折」与 V4 最低成本杠杆。新登 FIX-506（S-03 演示群标记未兑现）/510（FIX-377 行缺失补行）/511（真机段 HUMAN_INBOX 承诺从未回填——P2 系统性漏看风险）。
- v0.4（2026-09-28 03:00）：**D/E 线深挖并入**（wt776）：D 线读模型优先叙事+D-07 供给断链（FIX-507 P2：intervention lifecycle 写路径零生产调用方——数据飞轮中段断链被测试全绿掩盖）；E 线三层证据方法论+E-08 完整性能图景（修前/已修/未修/复测路径）。**FIX-508 账实不符实锤并收口**：491/492/493 行 OPEN 而修复在主干（行内容于跨批合并丢失，FIX-504 同族第四例）——当场补闭@1e3b6ebf；FIX-509（D/E receipt 断链同型）。深挖章的独立审查价值二次实证：文档过程本身在抓真问题。
- v0.3（2026-09-28 02:40）：**B/C 线深挖并入**（wt769 五源核验）：B 线诚实性红线执行者叙事+残差六项；C 线 10 模块亲证全活+「就绪未激活」面三项；**FIX-258 行补闭**（@52fbed29，闭账曾被行重建回退——台账指针会腐烂的实证）；新登 FIX-504。
- v0.2（2026-09-28 02:10）：**M/X 线深挖并入**（wt770，代码亲验级）：Memory Epoch/Provenance 真实数据流、M-09 缺陷发现器叙事、X 线真模型证据分层、V4 教材级考古三条；新登记 FIX-502（M/X 卡级 receipt 断链）/FIX-503（FIX-36 真模型复验承诺未兑现）。详章 v3-output/WT770-DOC-MX/。
- v0.1（2026-09-28 02:03，git 实取 b3e3068b；原文误写 03:00）：首版。骨架+当日三源核验快照+FIX 族谱初版+诚实边界。各线深挖章节标注 ⏳ 待填充。
