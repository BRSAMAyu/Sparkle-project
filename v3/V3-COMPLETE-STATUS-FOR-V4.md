# V3 全量状态报告 —— V4 设计唯一入口文档

> **文档契约**：V4 设计者只看这一份文档做判断。因此本文档承载：V3 真实意图、全部实施细节、完成度证据、已知问题与诚实边界。持续更新（协调会话每轮维护），版本号+日期在文首。**本文档只写有三源证据（git 主干 SHA / 独立审查 receipt / 运行级实测）支撑的事实；推测与待验证项显式标注。**
>
> **当前版本**：v0.3（2026-09-28 03:40——B/C 线深挖并入+FIX-258 补闭；详章 v3-output/WT769-DOC-BC/）
> **维护者**：Sparkle v3 舰队协调会话（主会话）｜**权威数据源**：v3/.sparkle_v3_fleet_state.json notes 流、v3/07_tasks/tasks.json（99→100/107 已核正）、v3/06_agent_fleet/DYNAMIC_ISSUES.md（FIX 台账 339 行）

---

## 0. 阅读指南与诚实声明

- **完成度判据**：tasks.json status + fleet done 名单 + git 主干交付 SHA 三源核验（wt759 全量核验报告 v3-output/WT759-RECON/report.md，逐卡 SHA 证据链在案）。**零假账**：90 张 fleet 声称 done 全部有主干交付。
- **验收模型（ADR-0011）**：普通任务 DONE = 独立未参与会话审查 + 当前集成 SHA 可失败测试；高风险 = 2 份独立审查。worker 自称完成不算完成。
- **诚实红线（贯穿 V3 全程执行）**：不以 Mock/人工改库冒充模型结果；无真实凭据/设备时交付阻塞证据；报告数字以实测为准（「2 秒」「59 项全绿」类旧报告宣称不当作实现事实）。
- **本文档的已知局限**：各产品线的「用户体验级」验证深度不一（多数卡有 headless/单测级证据，三端实机走查类受设备限制转 HUMAN_INBOX）；性能数字仅在标注处有真模型 bench 支撑。

## 1. V3 是什么（真实意图）

**一句话**：三层架构 AI 学习成长系统（Flutter Mobile → Go Gateway :8080 → Python AI Engine gRPC :50051 + FastAPI :8000；PG16+AGE+pgvector/Redis/MinIO/Celery）的参赛冲刺版本——把「AI 陪伴学习成长」从可用推向可交付的产品完整度。

**V3 的核心主张（来自 MASTER_DESIGN 与卡面体系，107 卡 13 条产品线）**：
1. **主链**：任务卡住 → 澄清/用户纠正 → 实际任务改变 → 重开后可见 → 完成反馈（学习成长的真实闭环，不是聊天玩具）
2. **Human/Agent/Hybrid 执行模型**：AI 降摩擦但不偷走目标（J-06 旗舰旅程；X 线 ActionPlan 契约族）
3. **Aurora 受限自适应**：有边界的个性化（A 线 8 卡：决策契约/干预目录/摩擦诊断/有界策略补丁）
4. **State/Memory/Knowledge/Events 四分上下文**（C 线 8 卡 + M 线 10 卡）
5. **可恢复 Run**：chat 轨去重命中改返结果（FIX-334→wt640 修复链），跨重启幂等（461/469/487 耐久链）
6. **真实结果与可纠正记忆**：证据融合（evidence/ 贝叶斯族）、Memory Epoch/Provenance（M-07/M-08）
7. **Galaxy 星系可视化**：Evidence-aware 的掌握度成长地图（G 线）
8. **诚实性作为产品价值**：失败可见、不静默兜底、模板不冒充模型输出（贯穿 FIX 族的修复方向）

**阶段目标**：内部交付 10/4，官方截止 10/7（天马 hackathon）；JOURNEY 七日真实驱动验证（day1-6 全绿，day7=09-28 08:00 终门）。

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

**当前：100/107 done（93.5%）**。三源核验已完成（wt759，2026-09-28）：15 张三源齐 + 84 张销账核正 + S-01（wt763 独立审查 APPROVE）。

**剩余 7 张**：
| 卡 | 状态 | 阻塞点 |
|---|---|---|
| J-02 Onboarding: Value Before Profile | wt764 在航（partial 续做：wt282 增量已存在） | — |
| O-06 Kill Switch/Release/Rollback 统一面 | wt765 在航 | — |
| E-08 AI Stack 集成 Bench | partial（wt372 104 条真模型 bench 已交付 a1418084；wt755 L0 首帧前移在分支待门后集成） | 真模型复测（有 key 环境）+ review receipt |
| O-01 公网 Staging HTTPS/WSS 一键部署 | 未启动 | 云凭据（用户 TCC 授权解锁后立即可做；ECS i-2ze439t934c2gsdqm778 已配） |
| O-05 Backup/Restore 演练 | 未启动 | HEAVY 位排队（wt764 返航后） |
| Q-07 Chaos/Recovery/Offline/Restore Storm 终验 | 未启动 | 依赖 O-01 |
| Q-08 V3 Final Gate Audit / Commercial RC | 未启动 | 压轴（Q-07 后） |

**各线完成度**（13 线全量表见 wt759 报告）：A 线 8/8｜B 线 6/6｜C 线 8/8｜D 线 6/8（D-07/D-08 已销账✓ 实为 8/8——待复核）｜E 线 7/8｜G 线 5/5｜J 线 7/8｜M 线 10/10｜O 线 4/7｜P 线 6/6｜Q 线 1/8｜S 线 5/5｜U 线 10/10｜X 线 10/10
（⏳ 此表 v0.2 将逐线复核修正——D 线两卡的销账依据需重列）

## 4. 各线深度状态（⏳ v0.1 仅骨架，随轮次逐线深挖填充）

每线将包含：**意图（卡面目标）→ 实际交付（关键 SHA+功能面）→ 验证证据（测试/review receipt/运行级）→ 残差与已知限制 → V4 注意点**。

- **B 线 Baseline（6/6，已深挖，详章 v3-output/WT769-DOC-BC/B-line.md）**：V3 诚实性红线第一执行者——4 张零产品码审计卡+2 张 harness 卡；B-02 直接/间接催生 FIX-01/256/257/258/329-331，B-06 催生 FIX-259/260/275/276/289/291/356。B-01 重开为 759 模块四态审计（690 ALIVE/55 PARTIAL/12 DEAD/2 ORPHAN）。**残差**：B-02 红测未入库（reviewer 已抓）；FIX-256/290/291/385 OPEN；community_context_boundary 528 行零生产 import（orphan-by-design 豁免——**V4 群 AI 面必须接线**）；B-05 成本表/能力矩阵为旧时点。
- **C 线 Context（8/8，已深挖，详章 v3-output/WT769-DOC-BC/C-line.md）**：10 个模块主干生产消费方逐一亲证**全活**，有跨卡复用网（J-06 复用 citation_markers 做 503 诚实失败）；13 测试文件 235 测试函数。**「就绪未激活」面（交付时如实留白，非缺陷）**：C-05 冲突定向澄清参数在但 validation_engine.py:361 未传（开文件亲证）；C-08 消融为 mock hermetic（56 场景×4 臂）真模型效用未做；C-01 proto 零触碰→跨语言 parity 未发生。
- **A 线 Aurora（8/8）**：AURORADecision 契约/干预目录 V1/摩擦诊断/联合决策/有界策略补丁/Why-this 收据/回归策略/四臂消融（0.65 vs 0.30）。⏳ 深挖中（下一批）
- **J 线 Journey（7/8 交付，J-02 待审查销账）**：J-03 Cockpit（dashboard -810 行）/J-04 首个行动六环（02b82cd2）/J-05 卡住恢复/J-07 回归/J-08 完成反思已交付；J-02 Onboarding 快车道已交付（wt764，独立审查 wt772 在航：goal capture 最小提交+五问零裁减+namespace 证据）；J-01 First 3 Minutes 为机会图留档（B 线实测承接）。⏳ 深挖中（下一批）
- **M 线 Memory（10/10，已深挖，详章 v3-output/WT770-DOC-MX/M-line.md）**：Memory Epoch/Provenance 是**真实数据流**（代码亲验）——M-01 契约模块派生五型/七态/scope（唯一新列 epistemic_class/superseded_by_id/epoch）；M-07 统一失效管线四动作（状态+审计+epoch bump+memory.invalidated 事件）**同事务原子**，读侧 epoch 门 fail-closed，「删偏好永久复活」主通道关闭（红→绿实证）；M-08 `/memory/provenance/*` 七路由+why-this 按 receipt 查；M-10 chat 回执深链+五面客户端级联失效。**M-09 是缺陷发现器**：真模型探针（qwen3.8-flash 真实 API 25 次硬预算）4/5 稳定通过、P01-D1 0/5 实锤 FIX-36（渲染器不渲染偏好值）；82-case 门禁曾 RED 20 失败实锤 FIX-35——双 P1 均修，门禁现 82/82。关键取舍：语义层（存储门/自检）默认关，生产决策面=规则层；生产降档率 66.67% 由 M-05 主导。M 线核心 273 用例实跑绿。
- **X 线 Action（10/10，已深挖，详章 v3-output/WT770-DOC-MX/X-line.md）**：X-01 契约（43942d23）→X-10 E2E（3b5a99bc，含 X-05B/P2 增量）。**Human/Agent/Hybrid 真模型证据面分层**：85 场景盲评与 X-10 77 场景（77/77、allocation 100%、high-risk auto=0、false success=0）均为规则层+服务层（`real_llm_calls=0` 显式断言）；**真模型证据**在 E-04 五面探针（收敛轮 15/15 含注入对抗）、J-04（LLM 建议 agent 被分配策略拦回=学习守卫生效）、J-06（真实 ToolExecutor 检索零 mock）、JOURNEY day1-6 真驱动；三端实机转 HUMAN_INBOX。**V4 教材级考古**：X-06 合入当日 chat 管道 100% 断（models `__init__` 漏注册，热修 f2e9f22e）——大改后冒烟必须当日；幂等洗白三轮修复链（FIX-40→417→447）；FIX-330 裁定 AgentRun/AgentToolCall/outcome_ledger 为生产三账本。X 线核心 403 用例实跑绿。
- **E 线 AI（7/8）**：E-03 首反馈按「服务可知后 <500ms」字面口径双证达成（FIX-439 裁决 b），端到端前段延迟移交 E-08 SLO 族；wt755 L0 修复（intake ack 前移）待门后集成，L1/L2/L3 留登记。真模型 bench：L2 p95=5.75s/L3 p95=7.32s（修前）。
- **U 线 UI（10/10）**、**P 线 Proactive（6/6）**、**S 线 Community（5/5，S-01 本档 §3）**、**G 线 Galaxy（5/5）**：⏳ 逐线深挖（下一批）
- **O/Q 线运维与终验**：见 §3 表。

## 5. 质量与可靠性态势（FIX 台账模式学）

**台账规模**：V3-FIX-001→497（339 行，493 已 FIXED）。**零假账纪律**贯穿：每个 FIXED@ 指针经「集成即纠指」指向主干可达 SHA。

**修复族谱（暴露的系统性弱点与已收口状态）**——这是 V4 最应读的一节：
1. **竞态/并发族**（全收口）：UserStreakStats 三入口（451/457/467+479，uuid5 同源三件套+PG 实证）；aurora 融合跨进程锁（418）；状态估计 claim（193）
2. **关停耐久族**（全收口）：chat 关停批不丢（427）、PEL 滞留重投（461）、幂等闸格式假设（469）、LRU 有界（481）、清理接线（487）——CQRS 全链 at-least-once+吸收闸
3. **代理信任链族**（480/482/483/484 收口）：TRUSTED_PROXY_CIDRS 判据、WS 代理 XFF 追加、dev trust-all 收紧、IP 形态校验
4. **软删/拉黑读面门族**（419/449/465 收口中）：community 读写各面闸门补齐
5. **审计/可观测静默失效族**（491/493 收口）：publish 签名错配被吞→修复+计数器
6. **孤儿代码族**（489/490 PURGE）：不可达屏 3300 行删除（证据链+原子留档）
7. ⏳ v0.2 将补：完整族谱分布统计（P1-P4 数量、按模块热点图）

## 6. 测试与 CI 态势

- **测试规模**：backend ~12300+ 用例（首次完整裁决 139F/12340P 后大量修复）、gateway 13 包（692 用例）、flutter 2636 用例、integration/e2e 面多层
- **CI**：21 次追绿（本日），洋葱 19 层全剥——基础设施层（shard 污染/AT 守卫/隐藏文件/coverage 配置/goimports/PEL 测试赛跑）与真测试层（首完整裁决暴露的真实缺陷）都已收口；第 21 次在航（层 19 修复后）
- **mypy 棘轮**：922→132→113→94→**91**（十批烧减，零 cast/零 ignore/真 bug 停手登记纪律——顺带挖出 491/492 等真 bug）
- **ruff/l10n**：evidence 目录全净；en/zh 10061 键双向零缺失；EN 占位符清零
- ⏳ CI 首绿后的三后置 job（Build Artifacts/Simulation Benchmark/Journey Smoke）首跑结果待补

## 7. 已知债务与未决清单

**待产品/用户裁量**：FIX-495（community post CQRS 闲置接线：零生产者零消费者，S-01 证实现状实时走引擎内进程——裁决建议：留档 post-RC 接线或拆除）；EXACT 带 8 草稿键（chatConfidence×3/chatCompletion×5）；FIX-465 已裁决派修中。
**等用户解锁**：H-001~008（HUMAN_INBOX：FIX-293 生产回填、云端 TCC、Dependabot #111-113、T36 B/D、49 冻结键、FIX-97/290、FIX-189 env 审计）。
**技术债登记**：KNOWN_CODE_DEBT_LEDGER（动统计/排行榜/card_protocol 前先读）；FIX-443③ stage34 死绑定（稳定性优先缓修）；FIX-375/379②③（post-10/4 结构性）。
**挂起待集成**：wt755 分支 938e845c（E-08 SLO L0，热路径门后集成；其新登记撞号项改 498）。

## 8. 诚实边界（V4 设计者必读）

1. **LLM 面**：CI/多数测试环境无 key→demo 模式路径广覆盖；真模型证据集中在 E-08 bench（104 条）与 JOURNEY 驱动（day1-6 实测）。
2. **三端实机**：Android/Web/macOS 真机走查类验收转 HUMAN_INBOX（无设备/浏览器权限）；mobile 验证以 widget test+analyze 门为准。
3. **性能数字**：仅 §4-E 线标注的 bench 有真模型支撑；「2 秒」类旧报告宣称不采信。
4. **云端部署**：未部署（O-01 卡凭据）；本地栈形态是唯一已验证运行形态。
5. **演示数据**：guest 登录播种 6 演示群+演示用户（friend 行共享）；journey 主用户 ns001 数据为真实七日驱动。

## 9. 度量快照（2026-09-28 03:00）

- 卡片：100/107 done（三源核验）｜FIX 台账 339 行（493 FIXED/占比 72%+）
- mypy 91（冷缓存主干口径；CI 侧基线 380 系平台代际差待 CI 实数对齐下调）
- 测试：backend ~12.3k/gateway 692/flutter 2636 用例
- 磁盘/运行态：本地栈三容器 healthy、双端 200（生产部署 N/A）
- ⏳ v0.2 补：代码规模统计、模块依赖图、测试覆盖分布

## 10. V4 设计建议输入（⏳ v0.2 起充实）

初版要点（基于 V3 执行观察）：
1. **结构性限制**：不增加 Java 后端/双数据库/第二套身份记忆系统（本阶段资源选择，ADR-0011）；proto→生成物/Alembic 唯一入口的治理结构值得 V4 延续
2. **高杠杆机会**：E 线首帧前移的 L1/L2/L3 已勘察未实施（StreamChat 前奏/门并行化/拥塞治理——wt755 notes 有完整归因）；Galaxy evidence-aware 接线（G-02 后的深化）
3. **避免重蹈**：账本三源漂移（V4 应从第一天用主干 SHA 记账）；worker 报告与实际交付的错位模式（本档 §5 的验收模型已解决，V4 沿用）；CI 从未完整跑过的管线自带腐烂（V4 初期就要全量绿基线）
4. ⏳ 待深挖后补：各线产品判断的详细输入

---

## 更新日志

- v0.1（2026-09-28 03:00）：首版。骨架+当日三源核验快照+FIX 族谱初版+诚实边界。各线深挖章节标注 ⏳ 待填充。
- v0.2（2026-09-28 03:10）：**M/X 线深挖并入**（wt770，代码亲验级）：Memory Epoch/Provenance 真实数据流、M-09 缺陷发现器叙事、X 线真模型证据分层、V4 教材级考古三条；新登记 FIX-502（M/X 卡级 receipt 断链）/FIX-503（FIX-36 真模型复验承诺未兑现）。详章 v3-output/WT770-DOC-MX/。
- v0.3（2026-09-28 03:40）：**B/C 线深挖并入**（wt769 五源核验）：B 线诚实性红线执行者叙事+残差六项；C 线 10 模块亲证全活+「就绪未激活」面三项；**FIX-258 行补闭**（@52fbed29，闭账曾被行重建回退——台账指针会腐烂的实证，V4 记账工具应做机器可达性检查）；新登 FIX-504（原 502 撞号重编）。文档编辑两次换位误删（E 线/J 线）均即补——大文档 Edit 必须 diff 自检的教训再次实证。
