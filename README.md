<div align="center">

# Sparkle 星火

### AI 驱动的成长操作系统

**不只是回答问题，而是理解你、陪伴你、帮你成为更好的自己。**

[![Flutter](https://img.shields.io/badge/Flutter-3.24+-02569B?style=flat-square&logo=flutter&logoColor=white)](https://flutter.dev)
[![Go](https://img.shields.io/badge/Go-1.22+-00ADD8?style=flat-square&logo=go&logoColor=white)](https://go.dev)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.3+-FF6B6B?style=flat-square)](https://langchain-ai.github.io/langgraph/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.0.0-blue?style=flat-square)](CHANGELOG.md)

**[English](README_EN.md)** &nbsp;&middot;&nbsp; [快速开始](#-快速开始) &nbsp;&middot;&nbsp; [技术文档](docs/)

</div>

---

## 一句话理解 Sparkle

> 市面上的 AI 是工具，用完即走。Sparkle 是一个**持续进化的成长伙伴**——它记住你是谁、理解你的思维模式、帮你拆解目标、追踪执行、在你卡住时给出恰到好处的支持。

---

## Sparkle 解决什么问题

| 传统 AI 助手 | 学习/效率类 App | Sparkle |
|:---|:---|:---|
| 没有记忆，每次从零开始 | 静态标签，粗粒度分类 | **持续进化的认知画像**，越用越懂你 |
| 被动问答，不会主动引导 | 预设路径，千人一面 | **目标驱动**，从"问什么"到"成为谁" |
| 信息碎片化，缺乏系统性 | 线性笔记，手动整理 | **知识星图**，自动构建你的知识网络 |
| 单次对话，无后续跟进 | 简单统计，缺乏洞察 | **七阶段成长闭环**，全程陪伴 |
| 纯工具感，没有温度 | 随机匹配，社群无深度 | **认知匹配**，找到真正合拍的伙伴 |

---

## 核心能力

**AI 微调导师** — 不只是答题，而是诊断你的认知状态。当你说"这个好难"，它会分析知识盲区、动态调整讲解深度、推荐针对性练习、追踪理解进度。链路已接入自研编排主系统，支持计划生成、审查、用户审批、执行和重规划。

**知识星图** — 你的个人知识网络，以宇宙地图的形式呈现。每个概念是一颗星，掌握度决定亮度，关系形成星座。AI 自动识别知识盲区，GraphRAG 混合检索引擎让每次查询都理解上下文。

**智能任务系统** — 六种任务类型，AI 根据你的认知画像自动推荐。内置专注计时器，支持正念模式。任务可进入 OpenClaw 委派链路，经历审批、结果对比、自验证和画像回流。

**成就引擎** — 真正有效的游戏化机制。连击记录养成习惯，里程碑记录突破，成长合约提供承诺机制，隐藏成就制造惊喜。成就不只是数字——它是你成长的证明。

**Mirofish 群体 Agent 系统** — 把多 Agent 从"技术能力"做成"产品能力"。聊天可以短链路桥接到 Insight Hub、Simulation、Knowledge Theater 和 Learning Report，让预测、推演、报告和行动建议在同一条体验链里完成。

**多感官体验系统** — 统一的沉浸式体验设计。场景化 BGM 和环境音随页面切换；语义化触觉反馈让每个操作都有感知；入场动效、庆祝系统和可调动效强度让成长可见可感。无障碍与低刺激模式优雅降级。

---

## 技术壁垒

Sparkle 的竞争力不在于单个功能，而在于**系统级架构创新**的组合壁垒：

| 技术壁垒 | 实现方式 | 竞品现状 |
|:---|:---|:---|
| 双核协作架构 | 执行核 + 认知核实时协作 | 大多数产品只有单一对话管线 |
| 自研编排主链 + LangGraph 规划增强 | 自研系统掌控生产执行，LangGraph 负责复杂规划 | 常见做法是把业务控制权直接交给 Agent 框架 |
| 证据驱动的 4D 画像 | 知识、认知、动机、社交四维度，每项都有行为证据 | 通常只有静态标签或简单统计 |
| GraphRAG 混合检索 | pgvector 语义搜索 + Apache AGE 知识图谱遍历，融合排序 | 纯向量检索，缺乏关系推理 |
| Mirofish 群体 Agent 产品化 | 专家目录、自定义专家/团队、桥接预览、深链跳转 | 多数产品只停留在聊天里的"多 Agent 展示" |
| OpenClaw 执行闭环 | 任务委派、离线排队、设备配对、审批、对比、自验证、失败降级 | 常见做法是止步于"给建议"或一次性自动化 |
| 七阶段成长闭环 | 感知 > 澄清 > 计划 > 执行 > 反思 > 巩固 > 适应 | 线性任务流，无闭环 |
| 统一多感官体验 | 5 种体验画像 + 感官预算 + 全局粒子预算 + 无障碍降级 | 零散动效，无系统性 |

---

## 架构总览

```
+====================================================================+
|                        Flutter Mobile App                          |
|         Riverpod  |  Design System V2  |  Multi-Sensory UX        |
|         732 Dart files  |  24 feature modules  |  131 tests        |
+========================================+===========================+
                                         |
                                  WebSocket / HTTP
                                         |
+========================================v===========================+
|                           Go Gateway (8080)                        |
|   Auth (JWT + Blacklist)  |  Rate Limiting  |  Caching  |  WS     |
|   16 Middleware  |  Security Headers  |  gRPC Bridge             |
+========================================+===========================+
                                         |
                                     gRPC (50051)
                                         |
+========================================v===========================+
|                        Python AI Engine                            |
|                                                                    |
|   +----------------------------------------------------------------+
|   |  Self-Built Orchestrator (LangGraph FSM)                       |
|   |  Dual-Core Router  |  UX Envelope  |  Plan Review             |
|   +----------------------------------------------------------------+
|   |  Cognitive Core            |  Execution Core                  |
|   |  Profile | Memory | Prism  |  Plan | Task | DAG Executor      |
|   +----------------------------------------------------------------+
|   |  GraphRAG  |  Event Bus  |  Tool Registry  |  Achievement     |
|   +----------------------------------------------------------------+
|   |  OpenClaw Adapter  |  Celery Tasks  |  LLM Service             |
|   +----------------------------------------------------------------+
+---+----------------+------------------+-----------------------------+
    |                |                  |
    v                v                  v
+--------+    +-----------+    +------------------+
| PG 16  |    | Redis 7+  |    | MinIO / S3       |
|pgvector|    | Stack     |    | Object Storage   |
|AGE     |    | Streams   |    |                  |
|143 tbl |    | Pub/Sub   |    |                  |
+--------+    +-----------+    +------------------+
                      |
            External Execution
                      |
            +---------v----------+
            | OpenClaw Gateway   |
            | Queue | Pairing    |
            | Approval | Verify  |
            +--------------------+
```

**为什么是三层 + 外部执行器？**

- **Flutter** 只负责展示和体验——不做业务逻辑
- **Go Gateway** 负责高并发连接管理、认证、缓存——不做 AI 推理
- **Python Engine** 负责编排、规划、审查、执行控制——不做用户认证
- **OpenClaw** 是外部执行器，不拥有 Sparkle 的业务主导权

每层职责清晰，独立扩缩容。Gateway 能扛住万级 WebSocket 连接，Engine 能水平扩展 AI 算力，而 OpenClaw 负责补齐数字执行闭环。

<details>
<summary><b>双核成长操作系统</b>（点击展开）</summary>

Sparkle 的核心创新是将 AI 系统拆为两个协作核心：

```
+=====================================+  +=====================================+
|          EXECUTION CORE             |  |          COGNITIVE CORE             |
|                                     |  |                                     |
|  Goal Clarification                 |  |  User Profile (4D)                  |
|         |                           |  |         |                           |
|         v                           |  |         v                           |
|  Sufficiency Evaluation             |  |  Long/Short-term Memory             |
|         |                           |  |         |                           |
|         v                           |  |         v                           |
|  Staged Plan (DAG)                  |  |  Cognitive Prism                    |
|         |                           |  |         |                           |
|         v                           |  |         v                           |
|  Task Execution                     |  |  Emotion & Motivation               |
|         |                           |  |         |                           |
|         v                           |  |         v                           |
|  Dynamic Adjustment                 |  |  Continuous Companion               |
+--------------------+----------------+  +--------------------+----------------+
                     |                                      |
                     +---------- Collaboration -------------+
                       Event Bus  |  Context Aggregation  |  Real-time Sync
```

**执行核**负责"把事做成"：帮用户定义目标、评估可行性、拆解计划、审查方案、发起执行、接收结果并根据实际重规划。

**认知核**负责"理解用户"：四维画像持续更新、长短期记忆积累、认知棱镜洞察思维模式、情感状态识别与个性化激励，并把执行结果回流到下一轮策略。

两个核心不是并行孤立运行，而是通过事件总线实时协作。

</details>

<details>
<summary><b>七阶段成长闭环</b>（点击展开）</summary>

每次 Sparkle 交互都是一个完整的成长循环：

```
                      +-----------------+
                      |  Sense (感知)   |
                      |  行为追踪       |
                      +--------+--------+
                               |
          +--------------------+--------------------+
          |                    |                    |
          v                    v                    v
  +---------------+   +---------------+   +---------------+
  | Clarify (澄清)|   |  Plan (规划)  |   | Execute (执行)|
  | 意图识别      |-->| 目标拆解      |-->| 任务调度      |
  +---------------+   +---------------+   +-------+-------+
          ^                                       |
          |             +---------------+         |
          |             | Reflect (反思)|<--------+
          |             | 结果分析      |
          |             +-------+-------+
          |                     |
          |           +---------+---------+
          |           |                   |
          |  +---------------+   +---------------+
          |  |Reinforce (巩固)|  | Adapt (适配)  |
          +--| 间隔重复      |   | 画像更新      |
             +---------------+   +-------+-------+
                                         |
           进入下一轮迭代 <---------------+
```

| 阶段 | 职责 | 技术实现 |
|:---|:---|:---|
| 感知 | 被动捕获用户信号 | 行为追踪、情绪识别、学习轨迹 |
| 澄清 | 理解真实意图 | 意图识别、上下文理解、澄清式提问 |
| 计划 | 生成可执行路径 | 目标拆解、路径规划、资源匹配、版本快照 |
| 执行 | 执行具体任务 | 任务调度、工具调用、OpenClaw 委派、审批回流 |
| 反思 | 分析执行结果 | 效果评估、错误归因、结果对比、自验证 |
| 巩固 | 固化学习成果 | 间隔重复、记忆曲线、成就激励 |
| 适应 | 调整策略模型 | 画像更新、策略优化、失败降级与重规划 |

</details>

<details>
<summary><b>GraphRAG 混合检索引擎</b>（点击展开）</summary>

突破传统 RAG 局限，将语义向量搜索与知识图谱遍历融合：

```
                             User Query
                                |
                 +--------------+--------------+
                 |                             |
                 v                             v
  +------------------------------+  +-----------------------------+
  | pgvector Semantic Search     |  | Apache AGE Graph Traversal  |
  |                              |  |                             |
  | - Similar content chunks     |  | - Prerequisites             |
  | - Topic matching             |  | - Follow-up concepts        |
  | - Context relevance          |  | - Related relationships     |
  |                              |  |                             |
  |         < 200ms              |  |         < 500ms             |
  +--------------+---------------+  +--------------+--------------+
                 |                                 |
                 +----------------+----------------+
                                  |
                                  v
                 +------------------------------+
                 | Fused Ranking Engine         |
                 |                              |
                 | 1. Deduplication             |
                 | 2. Dependency chain build    |
                 | 3. Profile-based weighting   |
                 | 4. Context compression       |
                 +--------------+---------------+
                                |
                                v
                 +------------------------------+
                 | Personalized Response        |
                 |         < 800ms total        |
                 +------------------------------+
```

| 能力 | 传统 RAG | Sparkle GraphRAG |
|:---|:---|:---|
| 语义理解 | 向量相似度 | 向量相似度 |
| 知识关系 | 无 | 图遍历推理 |
| 前置知识 | 无法识别 | 自动关联 |
| 个性化 | 无 | 画像加权 |
| 学习路径 | 无 | 依赖链生成 |

</details>

---

## 技术栈

| 层 | 技术 | 版本 | 选型理由 |
|:---|:---|:---|:---|
| 移动端 | Flutter | 3.24+ | 跨平台一致性、热重载、丰富组件 |
| | Riverpod | 2.x | 编译期安全、声明式状态管理 |
| 网关 | Go | 1.22+ | 高并发、低内存、编译型 |
| | Gin + gRPC | -- | 高性能 HTTP + 强类型跨语言调用 |
| AI 引擎 | Python | 3.11+ | AI 生态丰富 |
| | LangGraph | 0.3+ | 可观测状态机、复杂编排 |
| | Celery | 5.x | 成熟异步任务队列 |
| 数据 | PostgreSQL | 16+ | ACID + pgvector + Apache AGE |
| | pgvector | 0.7+ | 原生向量索引 |
| | Apache AGE | 1.5+ | PostgreSQL 图扩展，Cypher 查询 |
| | Redis | 7+ | 缓存、发布订阅、事件总线 |
| 存储 | MinIO | -- | S3 兼容对象存储 |
| 可观测 | Prometheus + Grafana + Loki + Tempo | -- | 指标、日志、追踪、告警全覆盖 |

---

## 快速开始

### 前置条件

| 依赖 | 版本 | 说明 |
|:---|:---|:---|
| Go | 1.22+ | 网关开发 |
| Python | 3.11+ | AI 引擎开发 |
| Flutter | 3.24+ | 移动端开发 |
| Docker | 24+ | 容器化部署 |
| Docker Compose | 2.x | 服务编排 |

### 一键启动

```bash
# 1. 克隆项目
git clone https://github.com/BRSAMAyu/Sparkle-project.git
cd Sparkle-project

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入必要配置（LLM API Key、数据库、Redis）

# 3. 启动基础设施（PostgreSQL、Redis、MinIO）
make dev-up

# 4. 初始化数据库
make sync-db

# 5. 启动后端服务（需要两个终端）
make grpc-server    # 终端 1：Python AI 引擎
make gateway-dev    # 终端 2：Go 网关

# 6. 启动移动端（第三个终端）
make mobile-run
```

### 常用命令

```bash
# 开发
make dev-up              # 启动基础设施
make gateway-dev         # 启动 Go 网关（热重载）
make grpc-server         # 启动 Python gRPC 服务
make mobile-run          # 启动 Flutter 应用

# 代码生成
make proto-gen           # 生成 Protobuf 代码
make sync-db             # 数据库迁移 + SQLC 生成
make mobile-gen          # Flutter 代码生成

# 任务队列
make celery-up           # 启动 Celery Worker + Beat
make celery-status       # 查看队列状态

# 健康检查
make smoke               # 全服务健康检查
make env-check           # 环境配置检查

# 测试
cd backend && pytest                    # Python 测试 (311 文件)
cd backend/gateway && go test ./...     # Go 测试 (34 文件)
cd mobile && flutter test               # Flutter 测试 (131 文件)
```

---

## 项目结构

```
Sparkle-project/
+-- mobile/                             # Flutter 移动端 (732 .dart files)
|   +-- lib/
|   |   +-- core/                       # 核心基础设施
|   |   |   +-- design/                 # 设计系统 V2（Token、组件、动效原语）
|   |   |   +-- experience/             # 体验画像系统
|   |   |   +-- services/               # 全局服务（BGM、触觉、音频策略、OpenClaw）
|   |   +-- features/                   # 功能模块（24 个路由模块）
|   |   |   +-- chat/                   # AI 对话
|   |   |   +-- task/                   # 任务管理
|   |   |   +-- galaxy/                 # 知识星图
|   |   |   +-- mirofish/               # Mirofish 群体 Agent UI 支撑
|   |   |   +-- focus/                  # 专注模式
|   |   |   +-- achievement/            # 成就系统
|   |   |   +-- community/              # 社群
|   |   |   +-- ...                     # 计划、认知、错题本、商店等
|   |   +-- gen/                        # Protobuf 生成代码 (78 files)
|   +-- test/                           # 131 个测试文件
|
+-- backend/
|   +-- gateway/                        # Go 网关层 (24 .go files)
|   |   +-- internal/
|   |       +-- handler/                # HTTP/WebSocket 处理器 (46 files)
|   |       +-- agent/                  # gRPC 客户端
|   |       +-- middleware/             # 16 个中间件 (Auth, RateLimit, Security...)
|   |       +-- service/                # 业务服务 (12 files)
|   |       +-- db/                     # 数据库层 (143 tables, SQLC)
|   |
|   +-- app/                            # Python AI 引擎 (319 .py files)
|       +-- orchestration/              # LangGraph 编排层
|       +-- adapters/openclaw/          # OpenClaw 执行适配层
|       +-- services/                   # 26 个服务文件
|       +-- tools/                      # AI 工具集
|       +-- core/                       # 核心组件（上下文、事件总线、画像）
|
+-- proto/                              # 6 个 Protobuf 定义（API 契约源）
+-- monitoring/                         # Prometheus + Grafana + Loki + Tempo + 11 告警规则
+-- scripts/                            # 部署、备份、验收脚本 (21 acceptance scripts)
+-- docker-compose.yml                  # 开发环境 (17 services)
+-- Makefile                            # 构建脚本
+-- CLAUDE.md                           # AI 开发助手指南
```

---

## 工程化指标

| 指标 | 数值 |
|:---|:---|
| Python 测试文件 | 311 |
| Go 测试文件 | 34 |
| Flutter 测试文件 | 131 |
| 验收脚本 | 21 |
| CI Workflows | 13 |
| Pre-commit Hooks | 10 |
| Proto 文件 | 6 |
| 数据库表 | 143 |
| Alembic 迁移 | 52 |
| Docker 服务 | 17 |
| SLO 告警规则 | 11 |
| Go Lint 规则 | 22 linters |
| Flutter Lint 规则 | strict-casts + strict-inference + strict-raw-types |

---

## 文档

| 文档 | 说明 | 受众 |
|:---|:---|:---|
| [CLAUDE.md](CLAUDE.md) | 开发指南、架构规则、代码模式 | 开发者 |
| [开发文档入口](docs/README.md) | 当前开发所需文档总入口 | 开发者 / 产品 |
| [技术架构](docs/00_项目概览/02_技术架构.md) | 三层架构深度讲解 | 开发者 |
| [知识星图设计](docs/02_技术设计文档/02_知识星图系统设计_v3.0.md) | GraphRAG 实现细节 | 开发者 |
| [OpenClaw 执行闭环审查](docs/architecture/SPARKLE_OPENCLAW_ALIGNMENT_REVIEW_v1.5.md) | 任务委派、审批、对比、自验证与降级 | 开发者 / 产品 |
| [Mirofish 融合签收清单](docs/verification/本地发布前完整签收清单_2026-03-21.md) | Mirofish 新链路与主流程验收范围 | 开发者 / QA |
| [CHANGELOG](CHANGELOG.md) | 版本变更记录 | 全部 |
| [前端体验对齐](docs/engineering/前端改进对齐文档_2026-03-22.md) | 多感官体验系统规范 | 前端开发者 |

---

## 参与贡献

欢迎各种形式的贡献：提交 Bug、提出新功能、改进文档、提交代码。

```bash
# 1. Fork 本仓库
# 2. 创建功能分支
git checkout -b feature/amazing-feature

# 3. 提交更改（遵循 Conventional Commits）
git commit -m 'feat: add amazing feature'

# 4. 推送并创建 Pull Request
git push origin feature/amazing-feature
```

---

## 许可证

本项目采用 [MIT License](LICENSE) 许可。

---

<div align="center">

**Sparkle** &nbsp;&middot;&nbsp; v1.0.0

帮助每个人成为更好的自己

[![Flutter](https://img.shields.io/badge/Flutter-02569B?style=for-the-badge&logo=flutter&logoColor=white)](https://flutter.dev)
[![Go](https://img.shields.io/badge/Go-00ADD8?style=for-the-badge&logo=go&logoColor=white)](https://go.dev)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-FF6B6B?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)

</div>
