# Sparkle Cosmos · 任务包 v2 撰写信息包

**用途**：为专家二撰写新版任务包（v2）提供全量信息——项目代码实况、v1 任务包的完整内容与缺陷、产品愿景、专家回应2 的增量、执行状态、已知债务与风险、以及对 v2 的具体改进建议。
**撰写人**：工程侧 Coding Agent（Mac 端，GLM），2026-09-17
**信息来源**：v1 任务包 zip（SHA256 全部校验通过）、sparkle-cosmos 仓库（`thequipster/sparkle-cosmos`，私有）、旧公开仓库（`BRSAMAyu/Sparkle-project`）、产品愿景 v1.0、专家回应2、以及本人在仓库上的全部实际工程工作。

---

## 0. 先读摘要（专家二最需要知道的 10 件事）

1. **比赛时间硬约束**：内部交付 **10/4 20:00**，10/5–10/7 只留缓冲；官方征集期至 10/7（精确时刻仍待 H-A01 核验）。今天 9/17，**剩余 17 天**。
2. **G1（可信写入门）原锚点 9/18 已不现实**：T04–T16（G1 泳道的全部实质工作）尚未开始，v2 必须诚实重校门槛日期，而不是按旧表假装可行。
3. **执行体系已在运行**：v1 包已被收编进仓库（`docs/competition/2026-tmall-hackathon/卡片库/`），叠加了 ADR-0010 卡片制接力机制；T00 已由 B 签收 DONE，T01/T02/T03 可领。v2 不是从零开始，是**在运行中的体系上换版**，需要迁移策略。
4. **工程基线已大幅改善**：CI 从"建成以来从未真正运行过"被修到 lint 作业首次全绿（详见 §7.2）。这段工作（提交 `56885a3..422ce28`，共 18 笔）与 T02 验收标准高度重合，**v2 的 T02 应直接继承其成果作为证据基线**。
5. **命名存在三方冲突，必须先拍板**：v1 包 PRODUCT_SPEC 拍板"产品名保留 **Spark/火花**，Cosmos 为内部工程名"；专家回应2 开篇要求"项目统一叫 **Sparkle**"；仓库 AGENTS.md 写"项目名 Sparkle Cosmos；运行主体是 Sparkle"。v2 动笔前 A 必须一句话定死。
6. **专家回应2 的五大增量已逐项与 v1 包规格核对**（§6.2）：执行权分配（Human/Agent/Hybrid）、系统四分法、确定性预筛、Intervention Catalog、Agent Run 状态机——这五项 v1 包确实没有；但认知阶梯、Attempt Ledger、命令协议、记忆四类对象 v1 包已有对应物，v2 不要重复建设。
7. **代码库远比"重构目标"丰富也远比它混乱**：约 43 个 feature、95 个 router、208 张 ORM 表、34 个移动端 feature 目录、Python 侧 450k 行。v1 包的方向（收口而不是重写）是对的，v2 应坚持。
8. **存量债务已量化并全部登记在案**（§7.4 债务台账 #0–#14）：Go lint 185 项、mypy 8315 项、Flutter analyze 148 警告+3202 信息、若干半接线功能（含一个 prompt 注入面的安全问题）。v2 应把"债务清偿"显式纳入任务体系，而不是只靠验收门槛间接压迫。
9. **两套仓库并行**：私有 `sparkle-cosmos`（比赛开发主线，Windows 队友 + Mac 工程侧双机协作）与公开旧仓库 `Sparkle-project`（冻结不动，赛后做内容同步）。v1 包对此没有描述，v2 需要写明仓库策略。
10. **合规边界已清理过一轮，不能回退**：商业 BGM（久石让等 10 首）与牛津词典数据已删除/替换，`inner-cosmos-extract/`（Apache-2.0 参考项目）只作设计参考不作产品宣称。v2 的任务卡必须延续这些边界（v1 包 T02 的 forbidden_paths 已含 `inner-cosmos-extract/**`，保留此纪律）。

---

## 1. 比赛与团队现实

- **赛事**：2026 天猫 AI 黑客松（高校挑战赛）。官方允许开源二次开发（活动页参赛须知已存档于仓库 `docs/competition/2026-tmall-hackathon/`），有原创性声明要求；评审维度与官方材料的差异也已存档。
- **团队三人 + 多 Agent**：
  - **A**：产品与最终责任人（对外主张、数据授权、提交、原创口径官方确认——H-A01 仍未完成）。
  - **B**：工程集成与运行责任人（合并队列、组件锁、基线回滚；Windows/WSL 侧主力，T00 由其签收）。
  - **C**：体验质量与证据责任人（真实用户试用、录屏、匿名记录；容量接近上限 19h 假设，A 需共同主持用户研究）。
  - **Agent 分工**：GLM 实现（本 Mac 端即 GLM）、Codex 独立审查/高风险决策、Gemini 辅助阅读与素材。并发上限 4 实现/2 审查/1 合并队列、待审 PR ≤ 3。
- **容量核算（v1 包数字，规划估计非实测）**：核心人工 A 20.08h / B 23.75h / C 15.50h，+20% 缓冲；可选评审另计 2.75h。原表假设 19 天 A/B 各 38h、C 19h。
- **关键待核验事项**：官方截止精确时刻、既有项目参赛资格与原创声明口径（H-A01，A 负责，至今未闭环）。

---

## 2. 代码库实况（v2 任务卡的路径与实体依据）

### 2.1 总架构（保留不变，v1 包拍板"不推倒技术栈"）

```
Flutter Mobile (Riverpod + GoRouter, 移动端)
    │  WebSocket /ws/chat + REST
Go Gateway :8080 (鉴权/限流/WS/gRPC 桥/CQRS)
    │  gRPC
Python AI Engine (gRPC :50051 + FastAPI :8000)
    │
PostgreSQL 16 (pgvector + Apache AGE) / Redis / MinIO / Celery
```

核心链路：`Flutter → /ws/chat → Go Gateway → AgentService.StreamChat(gRPC) → ChatOrchestrator`。

### 2.2 Python 引擎（backend/app，约 450k 行）

顶层模块（.py 文件数）：

| 模块 | 文件数 | 说明 |
|---|---|---|
| `services/` | 486 | 最大域；子域：analytics 28、**card_protocol 21（迁移 mid-flight，v1 包 T 任务明确"shadow 验证通过后才退役 legacy"，最大单体清理目标）**、galaxy 14、simulation 8、personalization 8、**evidence 7（贝叶斯证据融合）**、report 6、llm 6 |
| `api/` | 116 | v1 路由约 95 个 router；`api/v1/community.py` 单文件 5056 行 |
| `models/` | 100 | 约 208 张 ORM 表 |
| `orchestration/` | 90 | 编排核心：orchestrator、planning_workflow（5099 行）、prompts（4581 行）、双核路由、bert_intent_classifier、circuit_breaker、capability_selection_policy 等 |
| `signals/` | 73 | spine_orchestrator（4958 行，信号编排）、absence_detector 等 |
| `core/` | 70 | config、celery_tasks（**单文件 3600+ 行，巨型任务文件**）、security_monitor、websocket 等 |
| `aurora/` | 63 | **Aurora runtime_v1**：decision_loop、chat_adapter、energy_controller、correction_feedback、spine_confluence、migration 等——专家回应2 说的"Aurora 重定义为 Adaptive Control Layer"，映射对象就是这里 |
| `agents/` | 29 | StateGraph 聊天 agent（enhanced_agents、graph/nodes 等） |
| `tools/` | 22 | growth_strategy_tools、entity_cards（表驱动 lambda 注册）等 |
| `learning/` | 21 | bayesian_learner、self_model_bridge、outcome_consumer 等 |
| 其他 | — | routing 10、tasks 8、consumers 8、adapters 7、task_assistant 6、db 6、data 5、workers 4、sprint_packs/scenario_packs 各 4 |

**巨型文件 Top（v2 若含"热点重构"任务，这是清单）**：planning_workflow.py 5099、community.py 5056、spine_orchestrator.py 4958、prompts.py 4581、prediction_theater_service.py 3887、orchestrator.py 3755、guest_seed_service.py 3710、celery_tasks.py 3600+。

### 2.3 Go 网关（backend/gateway，17 个内部包）

`agent / chaos / config / cqrs / db / error_book / galaxy / handler / i18n / infra / logsafe / metrics / middleware / service / worker` + cmd。
- **CQRS 子系统**：event bus（Redis）、outbox（publisher/repository）、projection（builder/handlers/manager）、saga、worker（base/dlq）——v1 包的 outbox 复用策略就落在这里。
- **middleware**：auth、rate_limit、cors、i18n、security、ws_auth、chaos_guard、internal_api、ab_test 等。
- **workers**：galaxy_sync、community_sync、task_sync、outbox_relay。
- **db**：sqlc 生成（`schema.sql` 是从 Alembic 自动导出的快照，手改无效——硬规则）。
- 测试基建：miniredis（Redis 模拟）、httptest；全套测试已本地绿（CGO_ENABLED=0）。

### 2.4 Flutter 移动端（mobile/lib，34 个 feature 目录）

`achievement aurora auth calendar chat cognitive community document documents error_book experience file focus galaxy goal home insights intent knowledge leaderboard memory mirofish notification_center onboarding openclaw photon plan reflection report reviews seed_library settings shop simulation splash task theater tools translation user visual_elements vocabulary`
- 设计令牌体系 `core/design/`（UI 消费令牌，有 design_system 守卫脚本）。
- vendored 插件 `third_party_plugins/`（7 个 fork，多为 Apple Silicon/ARM 兼容）。
- 已知产品级问题：leaderboard 整链（1143 行）**未挂路由**；三个统计仓库 `fetchFromApi` 返回硬编码 mock 且 mock 进 Isar 暖缓存（债务台账 #1/#2/#3）。

### 2.5 契约与工具链（proto/，buf 管理）

- `buf.gen.yaml`：Go 走 buf 远程插件（protocolbuffers/go:v1.36.5 + grpc/go:v1.5.1）；Python 走 `scripts/generate_python_protos.sh`（grpcio-tools）；Dart 走 docker 工具链（`docker/proto-toolchain.Dockerfile`，Dart 3.6.1 + protoc_plugin 22.3.0 + dart symlink）。
- proto 文件：根级 agent_service / community_service / error_book / galaxy_service / stt_service / user_state / websocket（声明 `package *.v1` 的三个服务，Python 侧产物需归位 `app/gen/<svc>/v1/` 嵌套目录）+ `sparkle/` 子树（inference/rag/signals 各 v1）。
- 硬规则：**永不手改 `*/gen/`、`*_pb2.py`、Dart gen、SQLC 产物**；改 proto 后 `make proto-gen`。

### 2.6 两个仓库的关系（v1 包未覆盖，v2 必须写明）

- **sparkle-cosmos（私有）**：比赛主线。以 9/16 11:01 的 Sparkle 文件快照为初始提交（**与旧仓库无共同 git 历史**，这对 v2 意味着：任何"cherry-pick 回旧仓库"的说法都不成立，赛后同步是内容级快照导入）。Windows 队友与 Mac 工程侧双机协作，历史中出现过并行推送（已通过接力日志+rebase 流程消化）。
- **Sparkle-project（公开）**：冻结状态（push 被守卫禁用），赛后做单向内容同步回公开仓库，需排除比赛内部材料并保留 Apache-2.0 来源记录（inner-cosmos-extract 的 LICENSE 与 NOTICE 义务）。
- 环境陷阱实录（v2 的工程任务卡应引用）：Windows 快照丢失全部 POSIX 可执行位（已修，见 §7.2）；Mac 端 `~/.cache` 与 `~/.pub-cache` 是指向未挂载卷的软链接（buf/flutter 需 `XDG_CACHE_HOME`/`PUB_CACHE` 重定向）；本地 Go 验证用 `CGO_ENABLED=0`。

---

## 3. v1 任务包（Spark_Tmall_Execution_Pack_20260916）完整摘要

### 3.1 结构与真源

144 文件、2.6MB。目录：`00_decisions`（审计裁决）、`01_product`、`02_engineering`、`03_execution`（任务真源）、`04_agents`、`05_quality`、`06_competition`、`07_sources`、`reference/`（SQLite 命令语义参考实现 action_kernel.py，28 项单元测试）、`tools/`（validate_pack.py / next_tasks.py，离线无模型）。

真源纪律：`tasks.json` 是任务 ID/依赖/归属真源；`human_tasks.json` 是人工工时真源；Markdown 任务卡不能与 JSON 分叉；完成必须附当前代码 SHA、测试/运行证据、人类验收记录。

### 3.2 五个拍板（产品宪法）

1. 不做"更复杂的学习超级 App"——切口是"有明确成果的自主成长任务"。
2. 不靠一次长回复展示 AI——核心体验是五步闭环：理解卡点→可执行下一步→有权限的真实改变→产出证据→纠正后的下一次适配。
3. 不推倒技术栈——保留 Flutter/Go/Python/PG/Redis/Celery/对象存储，在既有 Aurora、TaskService、画像、事件总线上做边界内重构。
4. 不把并行当无人治理——GLM/Codex/Gemini 分工 + B 控合并队列 + A 控产品 + C 控体验证据。
5. 不承诺获奖——真实性、差异化、完成度、用户证据、答辩表现作为可执行变量。

### 3.3 七个逻辑边界（架构核心）

Context Compiler / Decision Service / Command Executor / Experience Projector / Aurora Policy Adapter / Attempt Ledger / UX Presenter。**包里明确：接口命名是逻辑设计，不代表源代码已有这些类；T00/T08 输出实体映射，有相同权威时复用；不能加第二套用户/任务数据库。**

写入协议（A-5 裁决，全包最重要的一条）：`解释 → 必要澄清 → 可读差异提案 → 明确授权 → 权限/版本校验 → task+receipt+outbox 同事务 → 返回已提交事实`。自然语言"已经改好了"没有任何授权或完成证明效力。Proposal 状态机：`needs_clarification/proposed/approved/applying/applied/rejected/failed/conflict/expired/cancelled`。

TaskService 裁决（T10 的核心）：审计定位 TaskService.update 自己 commit——必须改可注入 UnitOfWork、内部 flush、最外层唯一 commit。

### 3.4 门槛体系（v2 应保留的骨架）

| 门槛 | 条件 | 原锚点 |
|---|---|---|
| G0 基线 | 仓库/环境/身份/隔离数据/工具链可定位 | 立即 |
| **G1 可信写入** | 3 次真实完整闭环 + 全部负例（无 key、全失败、取消、重复确认、版本冲突、未授权任务、新旧记忆冲突、断线查询）；30 次 live 流程 ≥29 完成且无高危/假成功 | **9/18（已不可达，见 §8.1）** |
| G2 试用范围 | 一个真实主场景、干净候选、固定脚本、未验收功能关闭 | 9/21 |
| M 经验适配 | 40 组跨会话序列；有效纠正应用 ≥90%；违规使用（跨用户/被删/过期/无同意）=0 | 个性化主张前置 |
| P 主动 | 20 组触发/抑制场景；静音/同意/冷却违反 =0 | 仅 G1 后 |
| S 社群 | 两真实账号完整链路 + 隔离/撤回/重连负例 | 仅核心稳定后 |
| G3 功能冻结 | 发布套件、M、用户证据、真实数据、无阻断主路径 | 9/28 |
| G4 封包 | SHA+模型+flags+载体+证据+文稿匹配，冷启动可复现 | 10/3 封板、10/4 20:00 提交 |

另有 F0–F5（决赛）、C0–C3（公司化）后置门槛。

### 3.5 任务体系

- **63 张 Agent 卡**（gate 分布：G0×4、G1×13、G2×10、M×5、G3×6、G4×4、P×3、S×4、F×5、C×6 等）+ 30 项人工任务。
- 任务卡 schema（v2 建议保留）：`id / title / depends_on / stage / human_acceptor / human_review_minutes / component_lock / path_seeds / work / acceptance / risk / gate / status / implementation_agent / independent_reviewer / definition_of_done / forbidden_paths / must_read / outputs / parallel_rule / required_locks / rollback / stop_conditions / test_instructions`。
- **组件锁清单**：schema、contract、ai-provider、ai-orchestration、task-core、memory、privacy、gateway-auth、mobile-shell、mobile-chat、mobile-task、mobile-profile、analytics、community、workers、release（+T00 的 baseline）。
- 四条核心泳道：可信核心（T00→T02/03/04/08→T05-07/09-11/13→T14/15/16）、经验效果（T19→T20/21→T22/23→T24；T17/18/40 供指标）、体验（T36/25/26/27/28）、质量交付（T01/37/38/42/43/47 持续，T39/41/44/45 收尾，T48 贯穿）。可选泳道：主动 T29–31、社群 T32–35。
- **模型接入**：主链优先验证 Qwen（非强制）；三级角色 fast/planner/difficult；总交互截止 20s；最多初始+1 次修复；输入上下文预算默认 6000 tokens；运行时模型与开发 Agent（GLM/Codex）分开计费举证。

### 3.6 审计裁决（A-1~A-9、C-1）要点

- A-1/A-4：LIVE 缺 key 必须明确失败；fixture 显式进入、独立命名空间、禁真实写入；LIVE 对任意字符串不能命中假回复。
- A-2：**拒绝"只加 metadata"**——用户必须看见 AI 失败，模板不得宣称已修改。
- A-3/C-1：requested/actual model、attempt、provider_request_id、usage 来源（actual/estimated/unknown）分开；unknown 保持 unknown；禁止两处双计。
- A-5：**采用正式命令协议而非 prompt-only 保证**（见 §3.3）。
- A-6：due_date / scheduled_at+timezone / estimated_minutes 分开；省略≠null；时长 1–480 分钟。
- A-7：纠偏语义统一（"不要改"≠"取消刚才"≠"我不是不会"）；关键词只做候选信号。
- A-8：能力驱动路由（role/capability/enabled/probe），fallback 不丢能力。
- A-9：更新/纠偏/权限敏感请求不能用旧文本冒充新推理；读缓存绑定 user/object_version/memory_epoch/policy_version。

### 3.7 数据与评测口径（v1 包已相当完整，v2 保留）

- 指标口径表（实际专注时长/计划投入/自报/活跃天数/连续天数/纠正/已执行变更/产物闭环各自的定义与禁混项）；历史 `actual or estimated or 15` 不可恢复则标 `legacy_unknown`。
- 事件协议（共同字段 + 优先业务事件清单）；客户端体验事件不是业务写入权威。
- **北极星：每周完成至少一个目标相关成果闭环的活跃用户数**（同时报分母）。
- 周报：先 SQL 产事实 JSON，再让模型解释；数值与引用只能来自白名单事实。
- usage 唯一账本字段集（见 A-3/C-1）；Redis 缓存过期不丢账。
- 性能目标：非模型操作 p95≤1s、提案 p50≤4s/p95≤12s、本地反馈≤300ms、硬截止 20s、受控 20 并发；≥100 次请求才报分位数。
- 发布验收矩阵（G1 smoke/核心回归 30 次/结构与执行/M 记忆 40 组/材料/性能/P/S/交付）。
- 112 条离线场景（40 memory + 20 proactive + …），scenarios.jsonl，`case_id` 稳定；开发 30 组 + 独立复核 10 组流程隔离。

### 3.8 交互状态矩阵与产品底线

每个能改数据的界面必须覆盖 11 种状态（尚无数据/正在解释/需要澄清/提案待确认/提交中/已提交/结果未知/版本冲突/模型不可用/权限失效/删除中）。R0–R4 能力层次；陌生用户无开发者解释可完成核心流程；33 个 feature 不重做、商店/金币/全站榜单本届关闭。

---

## 4. 产品愿景 v1.0 要点（与 v1 包的关系）

愿景文档是 v1 包产品层的叙事展开（Spark Moment、今天/目标/我的、我卡住了、Smallest Useful Step、记忆四类+Scope、可控纠正、Evidence-driven Reflection、主动式懂得安静、社群围绕成果、星图重定义为成果可视化、Day 0–14 生命周期、评委六幕、DoD）。**内容与 v1 包 PRODUCT_SPEC 基本一致无冲突**，价值在于叙事完整性（评委叙事、用户感受目标）。两点注意：

1. 愿景文档通篇用 "Spark"，与专家回应2 的 "Sparkle" 要求冲突（见 §0.5）。
2. 愿景文档尚未进仓库归档——v2 期间建议由 A 决定其归档位置（如 PRODUCT_SPEC 前置叙事），避免两份"最高层约束"并存。

---

## 5. 专家回应2 的核心主张（v2 的设计输入）

（此处只列要点；专家二本人最清楚内容，给全交叉核对结论即可）

1. Sparkle = **adaptive action system**（system > agent）：World State + Aurora + Memory + Knowledge + Execution Runtime + UI；LLM/Agent 运行其上。
2. **执行权分配**（Human/Agent/Hybrid Action）成为 Action Proposal 一级属性；Hybrid 最有价值（AI 帮用户完成目标而非替代目标）。
3. **Aurora = Adaptive Control Layer**（State→Aurora→Intervention→Outcome→State' 的 decision loop），不是提醒模块。
4. **Bounded Plasticity**：可自适应（颗粒度/是否多问/偏好/策略/主动度/人机比例/干预策略）vs 不可自变（schema/权限/安全/账本/删除语义/隔离/事务/秘密/生产代码）。
5. **系统四分法**：Current State（结构化 DB）≠ User Memory ≠ Knowledge（RAG）≠ History/Events；Context = 四者按需组合。
6. **确定性预筛**：scope/过期/删除/权限由程序先砍 99%，LLM 只做剩余语义相关性。
7. **Context Compiler 是核心技术组件**，每条 Context 带来源（memory_391 式可追溯）。
8. 越用越好 = Observe→Infer→Act→Observe Outcome→Update；**Experience/Intervention Memory**（"什么情境下什么帮助对这个用户有效"）替代人格画像。
9. Aurora v1 = 规则约束 + LLM 判断 + Experience Memory + **Intervention Catalog**（clarify/explain/retrieve/rescope/split/schedule/delegate/execute/co-execute/pause/remind/abstain），不上 RL。
10. **"只有语义不确定性需要 AI"** 的 LLM/非 LLM 分界表；**Cognition Ladder** L0 无模型→L1 fast→L2 主推理→L3 Agent Run；绝大多数交互几百 ms~3s。
11. 统一 Agent Runtime（非几十个 personality agent）：Aurora 为 controller，工具带权限，run 带 objective/budget/completion_condition。
12. 四个 Plane：State / Intelligence / Execution / Experience（逻辑边界非微服务）。
13. Agent 永不是事实来源；run 状态机（QUEUED→RUNNING→AWAITING_APPROVAL→EXECUTING→SUCCEEDED/FAILED/CANCELLED/TIMED_OUT）+ run_id 恢复 + tool call 审计 + 幂等键。
14. 部署：App 瘦客户端→网关→后端+Agent Worker Pool；key 只在服务端；run 跨会话存活。
15. 主动式 = event trigger（deadline approaching/task overdue/slot missed/user active/upstream completed/goal stalled）→ 规则先判 → Aurora 决策（NO_ACTION/SUGGEST/AUTO_EXECUTE）。
16. 竞争标准已升高（ChatGPT Memory/Tasks/Work、Notion Agents、Reclaim/Motion），差异必须落在 **"How should human and AI jointly move a human goal forward?"**。
17. 需求真实性：intention–action gap 有文献支撑（implementation intentions 元分析）；但当前形态 PMF 未证明。首发用户 = **self-directed builders**（比赛项目/side project/作品集/paper/内容创作）。
18. 十条系统原则 + **"先完成新的核心设计文档再大规模 Coding"的建议**（对这条的工程侧意见见 §8.2）。

---

## 6. 交叉核对结论（工程侧逐项验证过，v2 直接引用）

### 6.1 专家回应2 与 v1 包**已有内容**的重合（不要重复建设）

| 回应2 概念 | v1 包对应物 | 备注 |
|---|---|---|
| Attempt Ledger | T05 + DATA_AND_OBSERVABILITY §5 字段集 | 几乎逐字段一致 |
| 命令协议/幂等/回执 | T08/T10 + ARCHITECTURE §3/§4 + action_kernel.py 参考实现（28 测试） | 回应2 的"每次写操作带 idempotency key"= T10 验收 |
| 记忆语义四类（事实/偏好/观察/假设）+ scope + 删除不复活 | MEMORY.md §1–§3 + T19–T24 | 回应2 的 memory scope JSON 结构示例可作 T20 实现参考 |
| 认知分级 | ARCHITECTURE §6 fast/planner/difficult 三角色 | 回应2 补了 L0（无模型）与 L3（Agent Run）形式化 |
| 主动抑制/同意/冷却 | PROACTIVE 设计 + P 门槛 + T29–31 | 回应2 的事件触发清单是可落地的触发器枚举 |
| 竞品对照与"组合价值"口径 | BUSINESS_AND_DIFFERENTIATION 的 W03–W06 表 | 同源同结论 |
| 越用越好不等于训练模型 | MEMORY.md §5/§6（M 门槛）+ T24 评测器 | 一致 |

### 6.2 专家回应2 的**真实增量**（v1 包确实没有，v2 需吸收）

| # | 增量 | v1 包现状 | v2 建议落点 | 决策人 |
|---|---|---|---|---|
| 1 | **Human/Agent/Hybrid 执行权分配**（Action 一级属性） | 全文检索无此概念 | T08 提案契约加 `execution_mode`；T09 卡点语义；MODULE_SPECS"计划修改"行；旗舰故事补 Hybrid 例子（论文 Related Work 五步协作） | A（产品语义） |
| 2 | **系统四分法**（State/Memory/Knowledge/Events 命名空间分离） | 只有记忆语义四类，无系统级分离原则 | ARCHITECTURE 增补一节 + T19 实体映射按四分法组织 | B |
| 3 | **确定性预筛再语义检索**（程序先砍 99%） | MEMORY.md §4 有"检索不是答案复用"，无此工程规则 | MEMORY 规格增补 + T20 验收加预筛测试 | B |
| 4 | **Intervention Catalog**（12 类枚举） | 无枚举目录 | PROACTIVE 规格增补 + Aurora Policy Adapter 规格；Aurora v1 = 规则+LLM+Experience Memory 的实现骨架 | A |
| 5 | **Agent Run 状态机**（run_id 恢复/审计/tool call 记录） | 部分（T08 回执/T10 幂等/T14 刷新/T47 生命周期/action_kernel），无统一 run 框架 | T47 扩展一节；完整 Agent Runtime 是赛后（R4） | B |

### 6.3 工程侧对回应2 两点的保留意见

1. **"先写完整核心设计文档再大规模 Coding"**：按字面执行会烧掉 2–3 天纯设计期，G1 更加不可达。正确姿势是每项增量一页规格增补 + 一条 ADR（总量约一个下午人工），T08/T09 开工时增量已在契约里。增量落点集中在 G1/G2/M 泳道，与 T01–T03（基线/工具链/迁移）完全正交，**T01–T03 不应等待**。
2. **完整蓝图的时间盒裁剪**：Agent Worker Pool 常驻化、RL/contextual bandit、Bounded Plasticity 全套机制、四 Plane 服务化——全部属于赛后 R4。本届 G1 只要 3 次真实闭环 + 负例 + 30 次回归。v2 要明确"蓝图终点"与"本届交付线"的分层，避免卡片被蓝图带偏。

---

## 7. 执行状态实况（截至 2026-09-17 凌晨）

### 7.1 接力状态

- T00（仓库基线、实体映射与复现入口）：**DONE**，B 于 9/16 深夜签收，阻塞①–④解除并登记；base SHA `5d8f5b3`；证据在本地忽略目录 `outputs/tmall-stage1/tasks/T00/`。H-B01 同步完成。
- T01/T02/T03：**可领**（复核七个已报修复 / 干净克隆工具链与契约生成 / 迁移九头诊断与安全升级）。
- H-A01（官方原创口径确认）：**并行待办，未闭环**——G0 之"身份"项不整体宣称。
- 仓库侧叠加了 ADR-0010 卡片制接力（63 卡全解锁、单人跑、一次一 PR、待审 ≤3、接力日志留痕）。

### 7.2 工程侧已完成的大规模修复（CI 从"从未跑过"到 lint 全绿）

背景：v1 包的验证协议假设存在可运行的验证设施，但 cosmos 的 CI **自建成从未真正执行过**（旧仓库的 CI 同样从未跑通，其修复停留在 lint 层且最后一笔未推送）。9/16 晚至 9/17 凌晨，Mac 工程侧连续修复 **18 笔提交（`56885a3..422ce28`）**，每层以真实 CI 运行验证：

1. **移植层**：旧仓库的 CI 裁剪（17→6 工作流）、flutter-action 修复、gateway 全量格式化（117 文件）、golangci-lint 配置右移 + 基线机制（`new-from-rev` 重钉到 cosmos 自己的提交 `e139baf`——旧仓库基线哈希在 cosmos 检出不可达，基线过滤会失效）。
2. **exec 位恢复**：Windows 快照基线丢失全部 POSIX 可执行位 → 146 个脚本（93 .sh + 53 shebang .py）对照 Sparkle 侧逐文件恢复；非脚本误带 755 的维持 644。
3. **python-lzo**：lock 里唯一需现场编译的包 → 10 处 lock 安装点统一前置 `liblzo2-dev`。
4. **Ruff 存量清零**（156→0）：**9 个真 bug 修复**（monitoring 缺 logger、celery 缺 UUID、galaxy 两处缺 select、agent_grpc 越界变量、feedback `cutoff_str` 笔误、spine 缺类型导入、admin_audit hasattr、executor 闭包捕获）+ 12 处死存储删除（零行为变更）+ 17 项风格遗留按文件豁免。
5. **mypy 8315 error/704 文件**：无 baseline 机制可复制 Go 侧方案，CI 改非阻塞注解（注解每次可见），恢复条件入台账。
6. **Flutter 链**：lint 作业补 pub get；Flutter 从钉死的 3.24（Dart 3.5，无法解析团队 lock 要求的 Dart≥3.11）改为跟随 stable；vendored 插件移出分析范围（89/132 个 ERROR 来自上游 fork）；analysis_options 重复 analyzer 键修复（dart format 崩溃根因）；analyze 预算刷新至实测值（ERROR 预算保持 **0** 且已达成）；Flutter Tests 超时 30→60（首跑冷编译 46 分钟被杀）。
7. **Go 测试全绿**：config RBAC 测试补 JWT_SECRET（CI 裸环境 go test 必挂根因）；**一个产品级修复——匿名遥测 `events/batch` 移出鉴权组**（测试固化了正确意图、接线遗漏，登录前遥测原本会 401）；3 个出生起不可能通过的测试修复（prod+通配 Origin 握手、非法 UUID session_id、localhost:8080 空 Origin 白名单）；coverage-gap 脚本失败时转储 go test stdout（此前失败无从分诊）。
8. **下游作业**：trivy-action 0.28/0.29 复合 action 内部引用了未发布的 setup-trivy 版本 → 改 setup-trivy@v0.3.1 直连 CLI + SARIF 上传权限补 `security-events: write`；c17 RBAC 迁移对 `sparkle_galaxy` 的 GRANT 在全新库 InvalidSchemaName → 补幂等 CREATE SCHEMA；四个 pytest 步骤补 SECRET_KEY/JWT_SECRET；守卫作业补 proto 全量生成；`stage22_prompt_coverage_baseline` 写前建目录；**python proto 生成后归位 v1 嵌套目录**（agent/galaxy/stt 三个服务声明 `package *.v1`，Go 产物在 `gen/agent/v1`、测试导入 `app.gen.agent.v1`，唯独 python 脚本产平铺——Backend Tests 全部收集错误的根因）。
9. **技术债预算**：Go 覆盖率缺口 2852→2900bp（首两次实测 2884/2885，±数 bp 时序噪声；棘轮方向不变只许收紧）。

**当前 CI 状态**：Code Quality & Linting 与 Protobuf Validation **稳定全绿**；待验证（最新修复已推送）：Backend Tests（pytest 应能收集）、Security（SARIF 权限）、DB Schema Drift（alembic 已过，卡快照比对）、Rule Guards（4 个子问题：Rule AT/AH 登记、density 工件、`stage24_policy_ir_schema_v1.json` 缺失——旧仓库也没有，疑似需要 `--write` 自举、一个守卫内嵌测试在 SQLite 用了 Postgres 的 `LEAST()`）、Flutter Tests（部分测试文件编译失败 `Failed to load test/widget_test.dart` 等，疑与生成代码导入相关，部分通过如 websocket 集成测试）。

**与 T02 的映射**：T02 验收三条——①干净环境可生成并导入（CI proto-gen 已在干净检出跑通）②Go/Python/Dart 契约一致（嵌套归位后布局一致）③生成两遍无漂移（未显式验证）。正式领 T02 时可直接引用 `56885a3..422ce28` 为证据基线，**建议在接力日志补记此映射**。

### 7.3 合规与资产边界（已完成的清理，不可回退）

- 删除 `mobile/assets/audio/bgm/curated/` 全部 10 首商业录音（约 153MB，含久石让配乐）；可授权曲目补配任务已派 B（Musopen/IMSLP/CC，9/27 材料 v1 前）。
- 词典 starter 包由 Oxford OALD 第三方数据整体替换为团队自编 `open-dict-starter`（114 词条，source=sparkle-team）；服务端仅保留通用 MDX 加载能力。
- `inner-cosmos-extract/`：Apache-2.0 的 Inner Cosmos 参考副本（React/TS/Vite 前端 + 设计稿 + 愿景文档），**只作交互/动效参考，不搬代码、不新增 ECharts、不整套引入 React/Spring Boot**；"倾倒困惑→结构化理解"是可撤回的 Flutter 入口候选，去留按 9/18 与 9/21 门槛决定；`ThoughtShredderSection.tsx` 仅交互参考；不含"粒子库直接搬运"的宣称。
- Sparkle README 自述 MIT 但顶层无 LICENSE——已列交件核对项，不由 Agent 代补。

### 7.4 债务台账全量（docs/engineering/KNOWN_CODE_DEBT_LEDGER.md，#0–#14 + 早期条目）

| # | 内容 | 状态/处置 |
|---|---|---|
| 1 | 三个统计仓库 fetchFromApi 返回硬编码 mock（successRate 0.95 等） | 接真实 API 或下线 |
| 2 | mock 数据写入 Isar 暖缓存并作为过期兜底长期供给 UI | 与 #1 一并修：mock 不许进缓存 |
| 3 | leaderboard 整链 1143 行未挂路由（后端/端点常量/l10n 均已就绪） | 产品决策：上线或整链删除 |
| 4 | card_protocol 迁移 mid-flight（legacy_adapter 39 处标记等） | 先查 shadow 验证状态；最大单体清理目标 |
| 5 | routing_engine/galaxy_service/aurora/migration 带退役计划的过渡代码 | 跟随各自迁移计划 |
| 6 | 全仓 101 文件含 deprecated/legacy/to-be-deleted 标记 | 按目录分批 |
| 7 | mock_community_repository | 有意设计非债务 |
| 8 | third_party_plugins 7 个 fork 无上游 commit 登记 | 已补 README；后续对照上游 |
| 9 | 网关弃用构造函数 2 处 | 随手清 |
| 0 | Go lint 基线 185 项（errorlint 34/bodyclose 26/…） | 基线 `e139baf`，新代码全量检查；按安全价值清偿 |
| 10 | Ruff 存量（已清零）+ 豁免 17 项 | E731×11（entity_cards 表驱动）等按文件豁免 |
| 11 | mypy 8315/704 文件 | CI 非阻塞注解；分模块清偿后按目录恢复门禁 |
| 12 | **半接线功能清单（需产品分诊）**：①prompts.py idiographic 消毒值算了没用，模板拿未消毒原文（**prompt 注入面，优先**）②achievement is_first 未写入 ChronicleEntry ③galaxy 推荐 limit 读出未应用 ④growth_strategy ctx_user_id 注释声称优先 runtime_context 但从未使用 | 各自接线或删除；①安全相关优先 |
| 13 | Flutter analyze 预算刷新（W148/I3202/15 个 code 预算抬至实测） | 新代码不得增长；REQUIRE_TRAILING_COMMAS 979 项可 dart fix 批量 |
| 14 | Go 覆盖率缺口预算 2852→2900bp（噪声余量） | 棘轮只许收紧 |
| 早期 | 网关死代码清理记录（community.go 等）、根目录孤儿 gitlink 等 | 已删除 |

### 7.5 多机协作与仓库治理实况

- Windows（B 主力，WSL，dev-sync 脚本）↔ Mac（工程侧）并行开发已实际发生：出现过守卫期间并行推送、接力日志"origin 并行提交融合复核"。B 已主动对齐 Mac 侧规范（`117e1f1` 补可执行位"对齐 ab9feea exec bit 约定"）。
- 旧公开仓库 push 已被禁用守卫（`remote.origin.pushurl=no-push-frozen-during-hackathon`，恢复：`git config --unset remote.origin.pushurl`）——旧仓库还有一笔本地未推送提交（90daac8，lint 全量历史检出），解冻推送后它会依次撞上 cosmos 已修的全部 CI 坑，修复都在 cosmos 历史里可对照。
- 赛后同步公开仓库的方法已在工程侧论证：内容级快照导入（一个"导入黑客松成果"提交）+ 排除清单（比赛内部文档、可选排除 inner-cosmos-extract）+ 完整历史可推成 `hackathon-2026` 存档分支。

---

## 8. 对任务包 v2 的具体改进建议（按优先级）

### 8.1 重校时间线（最高优先）

- G1 原锚 9/18 已不可达（T04–T16 未启动）。建议 v2 按"剩余 17 天倒排"重设：G1 → 9/23±、G2 → 9/26、M → 9/30、G3 冻结 → 10/1、G4 封板 → 10/3（把缓冲留给上传与阻断）。**宁可门槛日期诚实，不可门槛含义注水**——v1 包自己写过"不因日期到来假报通过"，v2 的日期必须配得上这句话。
- 容量重算：v1 包人时基于 9/16 起步，实际 9/17 才开始领卡；且 CI 修复消耗的工程时间（约一个整晚 + 后续收尾）未计入任何任务卡。v2 应把"工程基础"显式定价。

### 8.2 新增"工程基础泳道"（v1 包的结构性缺口）

v1 包假设了验证设施存在，但没有一张卡负责"让验证设施真正跑起来"。实际这块工作量大且已完成大半。建议 v2 增设：
- **EB-1 CI 全绿收尾**（继承 §7.2 剩余四项：Backend Tests / Rule Guards 四子问题 / Schema 快照比对 / Flutter 测试编译）——注意 Schema 快照比对涉及"`schema.sql` 是自动导出快照"的治理规则，可能需要按 `make sync-db` 流程重新导出，属 B 权限。
- **EB-2 债务清偿队列**（把台账 #0–#14 变成有估时的卡片，至少把 #12 的四项半接线功能——尤其 prompt 注入面——排进 G1 前的泳道；#1/#2/#3 统计与排行榜 mock 决策权在 A）。
- **EB-3 多机协作协议固化**（exec 位/行尾/PUB_CACHE/XDG_CACHE_HOME 环境陷阱、并行推送处理流程，写进 AGENTS 或接力机制附录）。
- **EB-4 赛后同步公开仓库的预案**（快照导入 + 排除清单 + 存档分支，作为 G4 后置任务）。

### 8.3 吸收专家回应2 五增量的落点（详见 §6.2 表）

每项一页规格增补 + 一条 ADR，总量约一个下午；不要按"先写完整设计文档再 Coding"字面执行（§6.3 保留意见）。T08 契约是最大受益卡（`execution_mode` 字段 + run 状态机语义）；T19/T20 吃到四分法与预筛；Aurora 规格吃到 Intervention Catalog。

### 8.4 治理与真源改进

1. **双真源收敛**：仓库卡片库与 zip 包已分叉（仓库版带实时状态）——v2 应声明"仓库内卡片库为唯一真源，zip 仅为发布快照"，并在 v2 发布时以一次收编 commit 完成（沿用上次的收编流程 + 接力日志登记）。
2. **状态同步机械化**：TASK_INDEX 的"当前接力"段是手写的，已出现过与 tasks.json 状态的轻微延迟。建议 v2 规定：状态只改 tasks.json，TASK_INDEX 段落由 `tools/next_tasks.py` 之类的脚本生成（包里已有工具雏形）。
3. **验收即测试**：63 张卡的 acceptance 建议加一个字段 `ci_hook`（哪个 CI 作业/脚本证明它），延续"验收以可失败测试呈现"的 T02 模式——CI 已经绿的部分（proto/vet/lint/ruff）让卡片引用作业名即可，别再要求人工复跑。
4. **任务卡 path_seeds 更新**：v1 包的 path_seeds 写于 T00 之前（"路径是审计导航种子"）；T00 已产出实体映射（证据在 `outputs/tmall-stage1/tasks/T00/`，注意在忽略目录不入库），v2 的卡片应直接引用映射后的真实路径（本文 §2 的模块清单可直接用）。

### 8.5 内容层增补建议

- **旗舰故事升级为 Hybrid 版**（回应2 §2 的论文 Related Work 五步协作），纯 Human 版（画趋势图）保留为入门例。
- **主动触发枚举**直接采用回应2 §20 清单（deadline approaching / task overdue / planned slot missed / user became active / upstream task completed / goal stalled），与 v1 包 PROACTIVE 的触发候选合并。
- **评委叙事**：愿景文档六幕 + 回应2 §28 的"Aurora 原愿景在 2026 技术条件下兑现"叙事线合并——这条线比"换了更强模型"高级，且真实。
- **竞品表更新**：v1 包的 W03–W06 表基于 9/16 官网快照；v2 若重写商业节，注意来源日期标注纪律（包的 SOURCE_REGISTER 已有此规范）。
- **明确"本届交付线 vs 蓝图终点"分层**：R0–R4 保留，把回应2 的 Agent Runtime/Worker Pool/RL/Plasticity 机制全部标 R4。

### 8.6 v1 包做得好、v2 必须保留的东西

五拍板、七边界"逻辑设计非既有类"的声明、A-5 命令协议与 A-2 拒绝 metadata 修复、G1 负例清单、交互状态矩阵（11 状态）、数据口径表与北极星、防伪完成四道检查、BLOCKED 不是耻辱、任务卡 schema 的 stop_conditions/rollback/forbidden_paths 字段、reference/action_kernel.py 参考实现、tools 离线校验器、SHA256 清单与 VALIDATION_REPORT 的"没执行不宣称"边界声明。

---

## 9. 工程侧风险清单（v2 排期时应计入）

1. **G1 负例工程量被低估的风险**：负例（断线恢复/两设备冲突/幂等重放）需要客户端配合改造（T14），比服务端协议更耗时。
2. **celery_tasks.py 与 card_protocol 的 mid-flight 状态**：任何 task-core 写路径改造（T10）都会碰到这两处历史分层，v1 包只给了"shadow 验证后再退役"的原则，没给验证步骤卡——v2 建议补一张"card_protocol shadow 验证状态核查"前置卡。
3. **Flutter 首跑成本**：CI 冷编译 46+ 分钟（已放宽到 60），本地多机各自暖缓存；v2 的体验类卡（T25–T28）排期要计入这个反馈周期。
4. **schema 快照与迁移的漂移**（当前 CI 未过项之一）：9 heads 的迁移链 + `sparkle_galaxy` 这类"开发库有、全新库无"的隐式依赖可能不止一处（c17 只是第一个撞上的）。v2 的 T03（迁移九头诊断）应把"全新库可升级"列为显式验收（现在 CI 已经在替你们做这件事）。
5. **守卫体系的工件自举**：stage22/stage24 等守卫期望的工件在两个仓库都不存在（需要 `--write` 自举或生成步骤），v2 把守卫任务化时注意区分"守卫逻辑坏了"和"守卫依赖的工件没生成"。
6. **两套 AGENTS.md 的指令权威**：包的 04_agents/AGENTS.md 与仓库根 AGENTS.md（Sparkle Cosmos 版）内容不同（仓库版含接力机制与 Windows 环境声明）。包里写过"先由 B 把兼容规则合并到仓库 AGENTS.md"——此事仍未发生，v2 收编时应一并处理。
7. **H-A01（官方原创口径）不闭环的风险**：允许开源二次开发的参赛须知已存档，但"既有项目参赛资格 + 原创声明口径"没有官方确认前，G0 的"身份"项悬空——这是 A 的人工任务，任何 Agent 卡片无法替代。

---

## 10. 附录

### 10.1 关键文件索引（v1 包内）

- 入口：`README_START_HERE.md` / `MASTER_PLAN.md` / `MANIFEST.json` / `VALIDATION_REPORT.md`
- 裁决：`00_decisions/AUDIT_DECISIONS.md`（A-1~A-9/C-1 全表）、`ISSUE_COVERAGE.md`（36 项 + 24 类补充债务去向）
- 产品：`01_product/PRODUCT_SPEC.md`、`BUSINESS_AND_DIFFERENTIATION.md`
- 工程：`02_engineering/ARCHITECTURE.md`、`MODULE_SPECS.md`、`MEMORY.md`、`DATA_AND_OBSERVABILITY.md`、`PROACTIVE_AND_COMMUNITY.md`
- 执行：`03_execution/TASK_INDEX.md`、`tasks.json`、`human_tasks.json`、`capacity.json`、`state.example.json`、`dependency_graph.mmd`、`GATES_AND_PRIORITY.md`、`HUMANS.md` + `humans/{A,B,C}.md`
- Agent：`04_agents/AGENTS.md`、`WORKFLOW.md`、`ROLE_PROMPTS.md`、`START_PROMPT.md`
- 质量：`05_quality/EVALUATION.md`、`CLAIMS_LEDGER.md`、`USER_RESEARCH_KIT.md`
- 比赛：`06_competition/SUBMISSION.md`、`PITCH_AND_DEMO.md`、`FINALS.md`
- 参考：`reference/action_kernel.py`（+28 单测）、`tools/validate_pack.py`、`tools/next_tasks.py`

### 10.2 仓库内对应位置

`docs/competition/2026-tmall-hackathon/`：`卡片库/`（收编版任务体系，含实时状态）、`卡片执行方案.md`（ADR-0010）、`接力日志.md`、`接力机制.md`、`验证与提交清单.md`、`specs/current_project_reverse_spec.md`（Luna 静态审查）、`决策研究/`、提交页截图与来源链接。债务台账：`docs/engineering/KNOWN_CODE_DEBT_LEDGER.md`。CI 设计：`docs/engineering/CI.md`。工作区构成与融合边界：仓库根 `COSMOS.md`。

### 10.3 18 笔工程提交索引（56885a3..422ce28，供 T02 证据引用）

```
56885a3 工具链修复移植（buf/Dart3.6.1/PEP668/symlink）
9110bce CI 修复链移植（17→6、flutter-action、proto-gen 前置、lint 全量历史）
e139baf gateway 全量格式化（117 文件，lint 基线）
24029fc lint 配置右移 + 基线重钉 e139baf + 台账 #0
ab9feea 恢复 146 个脚本可执行位
dea96d9 lock 安装前补 liblzo2-dev
e0c11c1 Ruff 存量清零（9 真 bug + 12 死存储）+ mypy 非阻塞（台账 #10/#11/#12）
7719a68 Flutter Analyze Gate 前补 pub get
e4376dc Flutter 跟随 latest stable
b7472dc vendored 排除分析 + flutter-test 补 proto + 门禁明细输出
dc51e44/7099d17 analysis_options 重复键修复
c1b5600 analyze 预算刷新（台账 #13）
cd54a90 config 测试补 JWT_SECRET（go test CI 首个真实失败）
85e7116 coverage-gap 脚本转储 stdout
fc79553 4 个测试修复 + 匿名遥测鉴权边界产品修复
5df4029 bodyclose（新代码检查按设计拦截）
ed1070d/fa70cf3/d02ad79 覆盖率缺口预算重校（台账 #14）
7e49842/d7846a2/422ce28 下游五项 + trivy 直连 + SARIF 权限 + python proto 嵌套归位
```

### 10.4 数据速查

- 代码规模：Python 引擎约 450k 行（services 486 文件/25+ 子域）；网关 17 内部包；移动端 34 feature 目录；全仓 6100+ 文件。
- 任务体系：63 Agent 卡 + 30 人工任务；核心人工约 59.3h（+20% 缓冲）；组件锁 16 个。
- 质量基线（首测）：Go lint 基线 185；mypy 8315/704 文件；Flutter analyze W148/I3202（ERROR=0）；Go 测试全套绿（CGO_ENABLED=0）；Python 测试与 Flutter 测试在 CI 首跑中（见 §7.2）。
- 场景集：112 条离线场景（40 memory/20 proactive）；评测矩阵 9 类；G1 负例 8 类。

---

## 11. 给专家二的最后三点提醒

1. **v2 是换版不是重启**：接力体系在运行、T00 已签收、CI 已绿大半——v2 发布本身需要一次迁移设计（哪些卡作废、哪些继承、状态怎么迁移、`tasks.json` 版本号怎么跳），建议 v2 里放一张"v1→v2 迁移卡"。
2. **所有"已修复/已绿"的表述都对应可验证证据**（提交哈希或 CI 作业名），本文档已尽量给出；没有证据的部分都标了"待验证"或"未闭环"。请延续这个纪律——v1 包的 VALIDATION_REPORT 是最好的模板。
3. **最大的两个未决项需要 v2 逼着团队立刻拍板**：①产品名（Spark vs Sparkle，三方冲突见 §0.5）；②G1 重校日期（§8.1）。这两件事不定，v2 的其他内容都会在锚点上摇摆。
