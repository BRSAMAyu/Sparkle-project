<div align="center">

# Sparkle

**AI 驱动的成长操作系统**

不只是回答问题，而是理解你、陪伴你、帮你成为更好的自己。

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

<table>
<tr>
<td width="33%" align="center"><b>传统 AI 助手</b></td>
<td width="33%" align="center"><b>学习/效率类 App</b></td>
<td width="33%" align="center"><b>Sparkle</b></td>
</tr>
<tr>
<td valign="top">

没有记忆，每次从零开始

被动问答，不会主动引导

信息碎片化，缺乏系统性

单次对话，无后续跟进

纯工具感，没有温度

</td>
<td valign="top">

静态标签，粗粒度分类

预设路径，千人一面

线性笔记，手动整理

简单统计，缺乏洞察

随机匹配，社群无深度

</td>
<td valign="top">

**持续进化的认知画像**，越用越懂你

**目标驱动**，从"问什么"到"成为谁"

**知识星图**，自动构建你的知识网络

**七阶段成长闭环**，全程陪伴

**认知匹配**，找到真正合拍的伙伴

</td>
</tr>
</table>

---

## 核心能力

<table>
<tr>
<td width="50%" valign="top">

### AI 微调导师

不只是答题，而是诊断你的认知状态。

当你说"这个好难"，它会分析你的知识盲区、动态调整讲解深度、推荐针对性练习、追踪理解进度。10+ 专业 Agent 动态协作，复杂问题自动拆解。

</td>
<td width="50%" valign="top">

### 知识星图

你的个人知识网络，以宇宙地图的形式呈现。

每个概念是一颗星，掌握度决定亮度，关系形成星座。AI 自动识别知识盲区，GraphRAG 混合检索引擎让每次查询都理解上下文。

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 智能任务系统

六种任务类型，AI 根据你的认知画像自动推荐。

学习、复习、练习、项目、阅读、自定义——内置专注计时器，支持正念模式。任务完成后自动更新画像，形成学习飞轮。

</td>
<td width="50%" valign="top">

### 成就引擎

真正有效的游戏化机制。

连击记录养成习惯，里程碑记录突破，成长合约提供承诺机制，隐藏成就制造惊喜。成就不只是数字——它是你成长的证明。

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 社群学习

基于认知画像的智能匹配。

责任伙伴找到认知风格相近的同伴，学习小组提供长期稳定的成长环境，冲刺群聚焦目标，同步打卡互相督促。

</td>
<td width="50%" valign="top">

### 多感官体验系统

统一的沉浸式体验设计。

场景化 BGM 和环境音随页面切换，语义化触觉反馈让每个操作都有感知，入场动效和庆祝系统让成长可见可感。无障碍优雅降级。

</td>
</tr>
</table>

---

## 技术壁垒

Sparkle 的竞争力不在于单个功能，而在于**系统级架构创新**的组合壁垒：

| 技术壁垒 | 实现方式 | 竞品现状 |
|:---------|:---------|:---------|
| **双核协作架构** | 执行核 + 认知核实时协作，不是并行孤立 | 大多数产品只有单一对话管线 |
| **证据驱动的 4D 画像** | 知识、认知、动机、社交四维度，每项都有行为证据 | 通常只有静态标签或简单统计 |
| **GraphRAG 混合检索** | pgvector 语义搜索 + Apache AGE 知识图谱遍历，融合排序 | 纯向量检索，缺乏关系推理 |
| **LangGraph 多智能体编排** | 10+ Agent 状态机协作，handoff、快照、可中断流式输出 | 单 Agent 或简单 chain |
| **七阶段成长闭环** | 感知 > 澄清 > 计划 > 执行 > 反思 > 巩固 > 适应 | 线性任务流，无闭环 |
| **统一多感官体验** | 5 种体验画像 + 感官预算 + 全局粒子预算 + 无障碍降级 | 零散动效，无系统性 |

---

## 架构总览

```
                          ┌──────────────────────────┐
                          │     Flutter Mobile App    │
                          │   Riverpod  Design System │
                          │ Multi-Sensory Experience  │
                          └────────────┬─────────────┘
                                       │
                                WebSocket / HTTP
                                       │
                          ┌────────────┴─────────────┐
                          │       Go Gateway          │
                          │  Auth  Rate-Limit  Cache  │
                          │  WebSocket  gRPC Bridge   │
                          └────────────┬─────────────┘
                                       │
                                   gRPC (TLS)
                                       │
                          ┌────────────┴─────────────┐
                          │    Python AI Engine       │
                          │  LangGraph Orchestrator   │
                          │  GraphRAG  Cognitive Core │
                          │  Tool Registry  Celery    │
                          └──┬─────────┬──────────┬──┘
                             │         │          │
                      ┌──────┴──┐  ┌───┴───┐  ┌──┴───┐
                      │ PG 16   │  │ Redis │  │ MinIO│
                      │pgvector │  │ 7+    │  │      │
                      │AGE Graph│  │       │  │      │
                      └─────────┘  └───────┘  └──────┘
```

**为什么是三层？**

- **Flutter** 只负责展示和体验——不做业务逻辑
- **Go Gateway** 负责高并发连接管理、认证、缓存——不做 AI 推理
- **Python Engine** 负责全部 AI 智能——不做用户认证

每层职责清晰，独立扩缩容。Gateway 能扛住万级 WebSocket 连接，Engine 能水平扩展 AI 算力。

---

<details>
<summary><b>双核成长操作系统</b>（点击展开）</summary>

Sparkle 的核心创新是将 AI 系统拆为两个协作核心：

```
  ┌──────────────────────────┐    ┌──────────────────────────┐
  │     执行核 (Execution)    │    │     认知核 (Cognitive)    │
  │                          │    │                          │
  │  目标澄清 → 充分性评估    │    │  用户画像 → 长短期记忆     │
  │      ↓                   │    │      ↓                   │
  │  分阶段计划 → 任务执行    │    │  认知棱镜 → 情感理解       │
  │      ↓                   │    │      ↓                   │
  │  动态调整               │    │  持续陪伴                │
  └───────────┬──────────────┘    └──────────┬───────────────┘
              │                               │
              └──────── 协作层 ────────────────┘
                  事件总线 · 上下文聚合 · 同步
```

**执行核**负责"把事做成"：帮用户定义目标、评估可行性、拆解计划、提供执行指导、根据实际灵活调整。

**认知核**负责"理解用户"：四维画像持续更新、长短期记忆积累、认知棱镜洞察思维模式、情感状态识别与个性化激励。

两个核心不是并行孤立运行，而是通过事件总线实时协作——执行核的任务结果会更新认知核的画像，认知核的理解会影响执行核的策略。

</details>

<details>
<summary><b>七阶段成长闭环</b>（点击展开）</summary>

每次 Sparkle 交互都是一个完整的成长循环：

```
              感知 (Sense)
                 │
    ┌────────────┼────────────┐
    ↓            ↓            ↓
  澄清        计划         执行
 (Clarify)   (Plan)     (Execute)
    ↑                        │
    │         反思            │
    │       (Reflect) ←──────┘
    │            │
    │     ┌──────┴──────┐
    │     ↓             ↓
    │   巩固          适应
    │ (Reinforce)   (Adapt)
    │                   │
    └───────────────────┘
```

| 阶段 | 职责 | 技术实现 |
|:-----|:-----|:---------|
| 感知 | 被动捕获用户信号 | 行为追踪、情绪识别、学习轨迹 |
| 澄清 | 理解真实意图 | 意图识别、上下文理解、澄清式提问 |
| 计划 | 生成可执行路径 | 目标拆解、路径规划、资源匹配 |
| 执行 | 执行具体任务 | 任务调度、工具调用、进度追踪 |
| 反思 | 分析执行结果 | 效果评估、错误归因、效果量化 |
| 巩固 | 固化学习成果 | 间隔重复、记忆曲线、成就激励 |
| 适应 | 调整策略模型 | 画像更新、策略优化 |

</details>

<details>
<summary><b>证据驱动的 4D 认知画像</b>（点击展开）</summary>

我们不只追踪"你知道什么"，更理解"你怎么思考"。每个维度都有**行为证据**支撑：

```
  ┌─────────────────────────────────────────────────┐
  │              4D 认知画像                          │
  ├────────────────────┬────────────────────────────┤
  │                    │                            │
  │  知识维度           │  认知维度                   │
  │  · 掌握度 (0-100)  │  · 元认知（自我监控）        │
  │  · 遗忘曲线半衰期   │  · 认知负荷评估              │
  │  · 学习速率         │  · 思维风格（抽象/具象）      │
  │  · 知识盲区图       │  · 问题解决策略              │
  │                    │                            │
  ├────────────────────┼────────────────────────────┤
  │                    │                            │
  │  动机维度           │  社交维度                   │
  │  · 自我效能感       │  · 协作风格                  │
  │  · 内外在动机比     │  · 沟通特征                  │
  │  · 兴趣图谱         │  · 社区贡献度                │
  │  · 目标承诺度       │  · 同伴影响敏感度            │
  │                    │                            │
  └────────────────────┴────────────────────────────┘
```

**证据来源**：对话内容分析、任务完成质量与时间、复习间隔与效果、错误模式聚类、情绪信号识别、社区互动行为。

</details>

<details>
<summary><b>GraphRAG 混合检索引擎</b>（点击展开）</summary>

突破传统 RAG 局限，将语义向量搜索与知识图谱遍历融合：

```
  查询 → ┬── pgvector 语义搜索（< 200ms）
         │    语义相似的内容片段
         │
         ├── Apache AGE 图遍历（< 500ms）
         │    前置知识、后续概念、关联关系
         │
         └── 融合排序
              去重 → 依赖链构建 → 画像加权 → 上下文压缩
              │
              ↓
          个性化响应（总延迟 < 800ms）
```

| 能力 | 传统 RAG | Sparkle GraphRAG |
|:----|:---------|:-----------------|
| 语义理解 | 向量相似度 | 向量相似度 |
| 知识关系 | 无 | 图遍历推理 |
| 前置知识 | 无法识别 | 自动关联 |
| 个性化 | 无 | 画像加权 |
| 学习路径 | 无 | 依赖链生成 |

</details>

<details>
<summary><b>LangGraph 多智能体编排</b>（点击展开）</summary>

10+ 专业 Agent 动态协作：

```
  用户输入 → 编排器（意图 → 拆分 → 分发 → 聚合）
                │
        ┌───────┼───────┬───────┬───────┐
        ↓       ↓       ↓       ↓       ↓
     知识     数学     代码    推理    规划
     Agent   Agent   Agent   Agent   Agent
        │       │       │       │       │
        └───────┴───────┴───────┴───────┘
                        │
                  流式输出（可中断）
```

- **Handoff 机制**：Agent 之间无缝上下文传递
- **状态快照**：长任务支持断点续传
- **PONR 确认**：高风险操作需用户确认
- **全链路可观测**：完整执行轨迹和决策链

</details>

<details>
<summary><b>多感官体验系统</b>（点击展开）</summary>

不是零散加动画，而是一套**统一的体验设计系统**：

| 层次 | 能力 | 说明 |
|:----|:----|:----|
| **体验画像** | 5 种场景预设 | 高效仪表盘、AI 对话、沉浸专注、社交温暖、庆祝时刻 |
| **音频策略** | 页面级 BGM + 阶段级覆盖 | SceneAudioScope 统一管理，不允许页面自行硬切 |
| **动效原语** | 错峰进场、注意力脉冲、退场过渡 | SparkleStagger / AttentionPulse / ExitTransition |
| **触觉反馈** | 27 种语义事件 | 同类行为触发同类反馈，全局感官预算防过载 |
| **庆祝系统** | 三档庆祝强度 + 稀有度光效 | 全局粒子预算，低端设备自动降级 |
| **无障碍** | reduceMotion / 大字体 / 语义标签 | 所有增强均可优雅退化 |

</details>

---

## 技术栈

| 层 | 技术 | 版本 | 选型理由 |
|:---|:----|:-----|:---------|
| **移动端** | Flutter | 3.24+ | 跨平台一致性、热重载、丰富组件 |
| | Riverpod | 2.x | 编译期安全、声明式状态管理 |
| **网关** | Go | 1.22+ | 高并发、低内存、编译型 |
| | Gin + gRPC | — | 高性能 HTTP + 强类型跨语言调用 |
| **AI 引擎** | Python | 3.11+ | AI 生态丰富 |
| | LangGraph | 0.3+ | 可观测状态机、复杂编排 |
| | Celery | 5.x | 成熟异步任务队列 |
| **数据** | PostgreSQL | 16+ | ACID + 丰富扩展 |
| | pgvector | 0.7+ | 原生向量索引 |
| | Apache AGE | 1.5+ | PostgreSQL 图扩展，Cypher 查询 |
| | Redis | 7+ | 缓存、发布订阅、向量缓存 |
| **存储** | MinIO | — | S3 兼容对象存储 |
| **可观测** | Prometheus + Grafana + Loki + Tempo | — | 指标、日志、追踪、告警全覆盖 |

---

## 快速开始

### 前置条件

| 依赖 | 版本 | 说明 |
|:----|:-----|:----|
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
cd backend && pytest                    # Python 测试
cd backend/gateway && go test ./...     # Go 测试
cd mobile && flutter test               # Flutter 测试
```

---

## 项目结构

```
Sparkle-project/
├── mobile/                             # Flutter 移动端
│   ├── lib/
│   │   ├── core/                       # 核心基础设施
│   │   │   ├── design/                 # 设计系统 V2（Token、组件、动效原语）
│   │   │   ├── experience/             # 体验画像系统
│   │   │   └── services/               # 全局服务（BGM、触觉、音频策略）
│   │   ├── features/                   # 功能模块（35 个领域模块）
│   │   │   ├── chat/                   # AI 对话
│   │   │   ├── task/                   # 任务管理
│   │   │   ├── galaxy/                 # 知识星图
│   │   │   ├── focus/                  # 专注模式
│   │   │   ├── achievement/            # 成就系统
│   │   │   ├── community/              # 社群
│   │   │   └── ...                     # 计划、认知、错题本、商店等
│   │   └── gen/                        # Protobuf 生成代码
│   └── test/                           # 81 个测试文件
│
├── backend/
│   ├── gateway/                        # Go 网关层
│   │   └── internal/
│   │       ├── handler/                # HTTP/WebSocket 处理器
│   │       ├── agent/                  # gRPC 客户端
│   │       ├── service/                # 业务服务
│   │       └── db/                     # 数据库层（SQLC）
│   │
│   └── app/                            # Python AI 引擎
│       ├── orchestration/              # LangGraph 编排层
│       ├── services/                   # gRPC 服务实现
│       ├── tools/                      # AI 工具集
│       └── core/                       # 核心组件（上下文、事件总线、画像）
│
├── proto/                              # Protobuf 定义（API 契约源）
├── monitoring/                         # Prometheus、Grafana、Loki、Tempo、告警
├── scripts/                            # 部署、备份、验证脚本
├── docker-compose.yml                  # 开发环境编排
├── docker-compose.prod.yml             # 生产环境编排（蓝绿部署）
├── Makefile                            # 构建脚本
└── CLAUDE.md                           # AI 开发助手指南
```

---

## 文档

| 文档 | 说明 | 受众 |
|:----|:----|:----|
| [CLAUDE.md](CLAUDE.md) | 开发指南、架构规则、代码模式 | 开发者 |
| [技术架构](docs/00_项目概览/02_技术架构.md) | 三层架构深度讲解 | 开发者 |
| [知识星图设计](docs/02_技术设计文档/02_知识星图系统设计_v3.0.md) | GraphRAG 实现细节 | 开发者 |
| [API 设计](docs/02_技术设计文档/05_API设计.md) | gRPC + WebSocket 接口 | 开发者 |
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
