<div align="center">

<!-- Logo placeholder - replace with actual logo -->
<!-- <img src="docs/assets/logo.png" alt="Sparkle" width="120"> -->

# ✨ Sparkle 星火

**不只是回答问题，而是理解学习者**

[![Flutter](https://img.shields.io/badge/Flutter-3.x-02569B?logo=flutter&logoColor=white)](https://flutter.dev)
[![Go](https://img.shields.io/badge/Go-1.21+-00ADD8?logo=go&logoColor=white)](https://go.dev)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-FF6B6B)](https://langchain-ai.github.io/langgraph/)
[![pgvector](https://img.shields.io/badge/pgvector-Vector_Search-4169E1?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)

<br>

基于**四维认知画像**的 AI 智能学习助手

深度理解你的 **认知模式 · 知识状态 · 学习习惯**，让 AI 成为真正懂你的学习伙伴

<br>

[核心特性](#-核心特性) · [技术亮点](#-技术亮点) · [快速开始](#-快速开始) · [文档](#-文档)

---

</div>

<br>

## 为什么选择 Sparkle？

<table>
<tr>
<td width="50%" valign="top">

### 现有工具的局限

- **千人一面** — 同样的问题，所有人得到相同回答
- **缺乏记忆** — 不知道你学过什么、哪里薄弱
- **被动应答** — 只能回答，不会主动引导
- **体验割裂** — 任务、笔记、复习散落各处

</td>
<td width="50%" valign="top">

### Sparkle 的不同

- **认知画像** — 四维模型持续追踪你的学习状态
- **越用越懂你** — 每次交互都让 AI 更了解你
- **主动引导** — 基于遗忘曲线提醒复习，发现知识盲区
- **一站闭环** — 对话、任务、知识图谱、复习无缝整合

</td>
</tr>
</table>

<br>

---

## 🎯 核心特性

<table>
<tr>
<td width="50%" valign="top">

### 🤖 AI 微导师

基于认知画像的自适应对话，能识别你的隐性需求。当你说"这个好难"，它不只是解释概念，还会诊断你的认知状态，调整讲解方式。

- 流式响应，实时打字机效果
- 多轮上下文记忆
- 自动识别薄弱点

</td>
<td width="50%" valign="top">

### 🌌 知识星图

你的个人知识网络可视化。每个知识点都有掌握度评分，基于遗忘曲线动态更新，自动发现关联概念和前置依赖。

- 知识点关系图谱
- 遗忘曲线追踪
- 智能关联推荐

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 📋 智能任务

6 种任务类型，AI 根据你的薄弱点自动推荐。内置番茄钟专注模式，帮你保持学习节奏。

- 学习 / 复习 / 练习 / 项目 / 阅读 / 其他
- 基于画像的任务推荐
- 番茄钟 + 激励机制

</td>
<td width="50%" valign="top">

### 📅 计划管理

告诉 AI 你的学习目标，它会帮你拆解成可执行的步骤。支持版本管理，多端同步，进度实时追踪。

- AI 辅助目标拆解
- 计划版本与冲突检测
- 进度预警与智能调整

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 📊 学习分析

错题自动归档并分析错误原因，多维度学习报告让你清楚自己的成长轨迹和薄弱环节。

- 错题归档 + 原因分析
- 学习效率统计
- 成长轨迹可视化

</td>
<td width="50%" valign="top">

### 👥 社群学习

基于认知画像智能匹配学习伙伴，组建学习小队或临时冲刺群，一起打卡互相激励。

- 画像匹配学习伙伴
- 学习小队 + 冲刺群
- 打卡与进度共享

</td>
</tr>
</table>

<br>

---

## 💡 技术亮点

### 四维认知画像引擎

我们不只追踪"你知道什么"，更理解"你如何思考"。

```
+-----------------------------------------------------------------------+
|                      COGNITIVE NEXUS ENGINE                           |
+-----------------------------------------------------------------------+
|                                                                       |
|  [Knowledge]        [Cognition]        [Motivation]       [Social]    |
|   知识掌握度         元认知能力          自我效能感         协作风格   |
|   记忆半衰期         认知负荷            学习偏好           贡献度     |
|   学习速度           思维模式            兴趣图谱           求助特征   |
|                                                                       |
|                    Every interaction updates the model                |
+-----------------------------------------------------------------------+
```

| 维度 | 追踪内容 | 应用场景 |
|:-----|:---------|:---------|
| **知识** | 掌握度 · 遗忘曲线 · 学习速度 | 精准复习推送 · 薄弱点预警 |
| **认知** | 元认知水平 · 认知负荷 · 思维模式 | 动态调整讲解深度 |
| **动机** | 效能感 · 偏好风格 · 兴趣分布 | 个性化激励策略 |
| **协作** | 社群贡献 · 沟通特征 | 智能匹配学习伙伴 |

<br>

### GraphRAG 混合检索

融合语义向量搜索与知识图谱遍历，突破传统 RAG 的局限。

```
                     Query: "什么是梯度下降？"
                                  |
              +-------------------+-------------------+
              |                                       |
              v                                       v
      +--------------+                        +--------------+
      | Vector Search|                        | Graph Traverse
      | (pgvector)   |                        | (Apache AGE) |
      +--------------+                        +--------------+
              |                                       |
      语义相似文档                              关联前置知识
      - 梯度下降定义                           - 偏导数
      - SGD vs Adam                            - 损失函数
              |                                       |
              +-------------------+-------------------+
                                  |
                          Result Fusion
                                  |
                         Contextualized Response
```

**性能**：向量检索 < 200ms · 图遍历 < 500ms · 综合 < 800ms

<br>

### LangGraph 多智能体编排

10+ 专业智能体动态协作，复杂问题自动拆解分发。

```
User Query ──> Orchestrator ──+──> Knowledge Agent (RAG 检索)
                              |
                              +──> Math Agent (数学推导)
                              |
                              +──> Code Agent (代码生成)
                              |
                              +──> Reasoning Agent (逻辑分析)
                              |
                              v
                       Response Stream (流式输出 + 可中断)
```

- **Handoff 机制** — 智能体间无缝交接
- **状态快照** — 支持断点续传
- **PONR 确认** — 高风险操作需用户确认

<br>

---

## 🏗 系统架构

```
+=============================================================================+
|                              MOBILE CLIENT                                  |
|                       Flutter · Riverpod · Design System V2                 |
+=================================+==========================================++
                                  |
                           WebSocket / HTTP
                                  |
+=================================+==========================================++
|                               GO GATEWAY                                    |
|              Auth · Rate Limit · Connection Pool · Protocol Bridge          |
+=================================+==========================================++
                                  |
                                gRPC
                                  |
+=================================+==========================================++
|                            PYTHON AI ENGINE                                 |
|                                                                             |
|    Cognitive Nexus ──> LangGraph FSM ──> Dynamic Tool Registry              |
|                              |                                              |
|                    GraphRAG Retrieval Layer                                 |
|               (pgvector + Apache AGE + Redis Cache)                         |
|                                                                             |
+=============================================================================+
         |                       |                       |
    PostgreSQL 16             Redis 7+               MinIO/S3
    + pgvector               (Session)              (Storage)
    + Apache AGE
```

### 技术选型

| 层级 | 技术栈 | 选型理由 |
|:-----|:-------|:---------|
| **移动端** | Flutter · Riverpod · Hive | 跨平台 · 声明式状态管理 · 本地缓存 |
| **网关层** | Go · Gin · WebSocket | 高并发 · 低延迟协议转换 |
| **智能层** | Python · LangGraph · Celery | AI 生态 · FSM 可观测 · 异步任务 |
| **向量库** | pgvector | 与业务库统一，运维简单 |
| **图数据库** | Apache AGE | PostgreSQL 原生扩展 |
| **协议** | Protobuf + gRPC | 强类型 · 流式传输 · 跨语言 |

<br>

---

## 🚀 快速开始

### 环境要求

- Go 1.21+
- Python 3.11+
- Flutter 3.x
- Docker & Docker Compose

### 本地开发

```bash
# 克隆项目
git clone <repo-url> && cd sparkle-flutter

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 LLM API Key 等

# 启动基础设施 (PostgreSQL, Redis, MinIO)
make dev-up

# 启动后端 (分别在新终端)
make grpc-server    # Python AI Engine
make gateway-dev    # Go Gateway

# 启动移动端
make mobile-run
```

### 常用命令

```bash
make proto-gen       # 生成 Protobuf 代码
make sync-db         # 数据库迁移 + SQLC
make smoke           # 服务健康检查
make celery-up       # 启动异步任务队列
```

<br>

---

## 📁 项目结构

```
sparkle-flutter/
├── mobile/                     # Flutter 客户端
│   └── lib/
│       ├── core/               # 设计系统 · 服务 · 工具
│       ├── features/           # 功能模块 (chat, task, galaxy...)
│       └── gen/                # Protobuf 生成代码
│
├── backend/
│   ├── gateway/                # Go 网关
│   │   └── internal/
│   │       ├── handler/        # HTTP/WebSocket 处理
│   │       ├── agent/          # gRPC 客户端
│   │       └── service/        # 业务逻辑
│   │
│   └── app/                    # Python AI 引擎
│       ├── services/           # gRPC 实现
│       ├── orchestration/      # LangGraph FSM
│       └── tools/              # AI 工具
│
├── proto/                      # Protobuf 定义 (接口契约)
└── docs/                       # 技术文档
```

<br>

---

## 📚 文档

| 文档 | 说明 |
|:-----|:-----|
| [CLAUDE.md](CLAUDE.md) | 开发指南 · 架构规范 · 代码模式 |
| [快速入门](docs/快速入门.md) | 本地开发与常用命令 |
| [技术架构](docs/00_项目概览/02_技术架构.md) | 三层架构详解 |
| [认知引擎](docs/09_Cognitive_Nexus/) | 四维画像设计 |
| [知识星图](docs/02_技术设计文档/02_知识星图系统设计_v3.0.md) | GraphRAG 实现 |
| [API 参考](docs/02_技术设计文档/03_API参考.md) | gRPC + WebSocket |
| [ADR 记录](docs/adr/) | 架构决策记录 |
| [性能基准测试](docs/性能基准测试.md) | Benchmark 运行说明 |

<br>

---

## 📈 开发进展

### 已完成

- [x] 四维认知画像系统
- [x] GraphRAG 双路检索 (pgvector + AGE)
- [x] LangGraph 多智能体编排
- [x] 知识星图可视化
- [x] 智能任务推荐 + 番茄钟
- [x] 计划版本管理
- [x] 社群功能 (好友/群组/打卡)
- [x] 遗忘曲线复习推送
- [x] Design System V2

### 进行中

- [ ] 错题归因分析增强
- [ ] 协作学习实时同步
- [ ] 性能优化

<br>

---

## 👥 关于

由 4 名计算机专业学生开发维护

**技术栈**: Python · Go · Flutter · LangGraph · PostgreSQL

<br>

---

<div align="center">

`v0.3.0`

<sub>Built with LangGraph · pgvector · Flutter</sub>

</div>
