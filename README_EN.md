<div align="center">

# Sparkle

### AI-Powered Growth Operating System

**Not just answering questions — understanding you, growing with you, helping you become your best self.**

[![Flutter](https://img.shields.io/badge/Flutter-3.24+-02569B?style=flat-square&logo=flutter&logoColor=white)](https://flutter.dev)
[![Go](https://img.shields.io/badge/Go-1.22+-00ADD8?style=flat-square&logo=go&logoColor=white)](https://go.dev)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.3+-FF6B6B?style=flat-square)](https://langchain-ai.github.io/langgraph/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.0.0-blue?style=flat-square)](CHANGELOG.md)

**[中文](README.md)** &nbsp;&middot;&nbsp; [Quick Start](#-quick-start) &nbsp;&middot;&nbsp; [Documentation](docs/)

</div>

---

## Sparkle in One Sentence

> Every AI assistant on the market is a tool — you use it and leave. Sparkle is a **continuously evolving growth companion** that remembers who you are, understands how you think, helps you break down goals, tracks execution, and provides just the right support when you're stuck.

---

## The Problem Sparkle Solves

| Traditional AI | Learning/Productivity Apps | Sparkle |
|:---|:---|:---|
| No memory — starts from scratch every time | Static tags — coarse categorization | **Evolving cognitive profile** that deepens over time |
| Passive Q&A — no proactive guidance | Preset paths — one size fits all | **Goal-driven** — from "what to ask" to "who to become" |
| Fragmented information — no system | Linear notes — manual organization | **Knowledge Galaxy** — auto-builds your knowledge network |
| Single conversation — no follow-up | Simple stats — no real insights | **7-stage growth loop** — continuous companionship |
| Pure tool — no warmth | Random matching — shallow community | **Cognitive matching** — find truly compatible partners |

---

## Core Capabilities

**AI Micro-Tutor** — Not just answering — diagnosing your cognitive state. When you say "this is hard", it analyzes knowledge gaps, adapts explanation depth, recommends targeted practice, and tracks comprehension. The chain runs through Sparkle's production orchestration with plan generation, review, user approval, execution, and replanning.

**Knowledge Galaxy** — Your personal knowledge network visualized as a cosmic map. Each concept is a star, mastery determines brightness, relationships form constellations. AI auto-identifies blind spots. The GraphRAG hybrid engine ensures every query understands context.

**Smart Task System** — Six task types, AI-recommended based on your cognitive profile. Built-in focus timer with mindfulness mode. Tasks can enter the OpenClaw delegation flow with approval, comparison, self-verification, and profile feedback.

**Achievement Engine** — Gamification that actually works. Streaks build habits. Milestones record breakthroughs. Growth contracts provide commitment. Hidden achievements create surprise. Achievements aren't just numbers — they're proof of your growth.

**Mirofish Group Agent System** — Turning multi-agent orchestration into a real product surface. Chat can short-circuit into Insight Hub, Simulation, Knowledge Theater, and Learning Report so prediction, scenario modeling, reporting, and next actions happen in one connected experience.

**Multi-Sensory Experience** — A unified immersive experience design system. Context-aware BGM and ambient audio shift with each screen. Semantic haptics make interactions tangible. Motion intensity, celebration states, and accessibility modes are tuned as one coherent system.

---

## Technical Moat

Sparkle's competitive edge isn't any single feature — it's the **combinatorial barrier of system-level architectural innovations**:

| Technical Barrier | Implementation | Industry Status |
|:---|:---|:---|
| Dual-Core Architecture | Execution Core + Cognitive Core collaborate in real-time | Most products have a single conversation pipeline |
| Self-Built Orchestrator + LangGraph Planning | Core production control stays in Sparkle; LangGraph handles complex planning | Many products hand business control directly to agent frameworks |
| Evidence-Based 4D Profile | Knowledge, Cognition, Motivation, Social — each backed by behavioral evidence | Typically static tags or simple statistics |
| GraphRAG Hybrid Retrieval | pgvector semantic search + Apache AGE graph traversal, fused ranking | Pure vector retrieval, no relational reasoning |
| Mirofish Productized Group Agents | Expert catalog, custom experts/teams, bridge previews, deep links into product surfaces | Most products stop at "multi-agent chat UI" |
| OpenClaw Execution Loop | Handoff, offline queue, pairing, approval, comparison, self-verification, degradation | Most products stop at advice or one-shot automation |
| 7-Stage Growth Loop | Sense > Clarify > Plan > Execute > Reflect > Reinforce > Adapt | Linear task flows, no closed loop |
| Unified Multi-Sensory UX | 5 experience profiles + sensory budget + particle budget + a11y degradation | Scattered animations, no system design |

---

## Architecture Overview

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

**Why three layers plus an external executor?**

- **Flutter** handles presentation and experience only — no business logic
- **Go Gateway** handles high-concurrency connections, auth, caching — no AI reasoning
- **Python Engine** handles orchestration, planning, review, and execution control — no user authentication
- **OpenClaw** is an external executor and does not own Sparkle's business brain

Each layer has clear responsibilities and scales independently. The Gateway handles 10K+ WebSocket connections, the Engine scales AI compute horizontally, and OpenClaw closes the digital execution loop.

<details>
<summary><b>Dual-Core Growth Operating System</b> (click to expand)</summary>

Sparkle's core innovation splits the AI system into two collaborative cores:

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

The **Execution Core** handles "getting things done": defining goals, assessing feasibility, breaking down plans, reviewing strategies, dispatching execution, collecting results, and replanning based on reality.

The **Cognitive Core** handles "understanding the user": continuously updating the 4D profile, accumulating long/short-term memory, perceiving thinking patterns through the Cognitive Prism, recognizing emotional states for personalized motivation, and feeding execution outcomes back into future strategy.

The two cores don't run in isolation — they collaborate in real-time through an event bus.

</details>

<details>
<summary><b>7-Stage Growth Loop</b> (click to expand)</summary>

Every Sparkle interaction is a complete growth cycle:

```
                      +-----------------+
                      |    Sense        |
                      |  (passive)      |
                      +--------+--------+
                               |
          +--------------------+--------------------+
          |                    |                    |
          v                    v                    v
  +---------------+   +---------------+   +---------------+
  |   Clarify     |   |     Plan      |   |   Execute     |
  | true intent   |-->| executable    |-->| specific      |
  +---------------+   | paths         |   | tasks         |
          ^            +---------------+   +-------+-------+
          |                    |                   |
          |             +------+-------+           |
          |             |   Reflect    |<----------+
          |             | analyze      |
          |             +------+-------+
          |                    |
          |           +--------+--------+
          |           |                 |
          |  +---------------+  +---------------+
          |  |  Reinforce    |  |    Adapt      |
          +--| consolidate   |->| adjust        |
             +---------------+  | strategy      |
                                +-------+-------+
                                        |
          Enter next iteration <--------+
```

| Stage | Responsibility | Technical Implementation |
|:---|:---|:---|
| Sense | Passively capture user signals | Behavior tracking, emotion recognition, learning trajectory |
| Clarify | Understand true intent | Intent recognition, context understanding, clarifying questions |
| Plan | Generate executable paths | Goal decomposition, path planning, resource matching, version snapshot |
| Execute | Run specific tasks | Task scheduling, tool invocation, OpenClaw delegation, approval feedback |
| Reflect | Analyze results | Outcome evaluation, error attribution, comparison, self-verification |
| Reinforce | Consolidate learning | Spaced repetition, memory curves, achievement motivation |
| Adapt | Adjust strategy | Profile updates, strategy optimization, failure degradation and replanning |

</details>

<details>
<summary><b>Evidence-Based 4D Cognitive Profile</b> (click to expand)</summary>

We don't just track "what you know" — we understand "how you think". Every dimension is backed by **behavioral evidence**:

```
+--------------------------------------------------------------------+
|                    4D Cognitive Profile                              |
+--------------------------------+-----------------------------------+
|                                |                                   |
|  Knowledge                     |  Cognition                        |
|  - Mastery (0-100)             |  - Metacognition                  |
|  - Forgetting curve half-life  |  - Cognitive load assessment      |
|  - Learning rate               |  - Thinking style (abstract/concrete)|
|  - Knowledge gap map           |  - Problem-solving strategy       |
|                                |                                   |
+--------------------------------+-----------------------------------+
|                                |                                   |
|  Motivation                    |  Social                           |
|  - Self-efficacy               |  - Collaboration style            |
|  - Intrinsic/extrinsic ratio   |  - Communication traits           |
|  - Interest map                |  - Community contribution         |
|  - Goal commitment             |  - Peer influence sensitivity     |
|                                |                                   |
+--------------------------------+-----------------------------------+

Evidence sources: conversation analysis, task completion quality/timing,
review intervals/effectiveness, error pattern clustering, emotional signals,
community interaction behavior.
```

</details>

<details>
<summary><b>GraphRAG Hybrid Retrieval Engine</b> (click to expand)</summary>

Breaking through traditional RAG limitations by fusing semantic vector search with knowledge graph traversal:

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

| Capability | Traditional RAG | Sparkle GraphRAG |
|:---|:---|:---|
| Semantic understanding | Vector similarity | Vector similarity |
| Knowledge relations | None | Graph traversal reasoning |
| Prerequisites | Not identified | Auto-linked |
| Personalization | None | Profile-weighted |
| Learning paths | None | Dependency chain generation |

</details>

---

## Tech Stack

| Layer | Technology | Version | Rationale |
|:---|:---|:---|:---|
| **Mobile** | Flutter | 3.24+ | Cross-platform consistency, hot reload, rich widgets |
| | Riverpod | 2.x | Compile-time safe, declarative state management |
| **Gateway** | Go | 1.22+ | High concurrency, low memory, compiled |
| | Gin + gRPC | -- | High-performance HTTP + strongly-typed cross-language calls |
| **AI Engine** | Python | 3.11+ | Rich AI ecosystem |
| | LangGraph | 0.3+ | Observable state machine, complex orchestration |
| | Celery | 5.x | Mature async task queue |
| **Data** | PostgreSQL | 16+ | ACID + rich extensions |
| | pgvector | 0.7+ | Native vector index |
| | Apache AGE | 1.5+ | PostgreSQL graph extension, Cypher queries |
| | Redis | 7+ | Cache, pub/sub, event bus |
| **Storage** | MinIO | -- | S3-compatible object storage |
| **Observability** | Prometheus + Grafana + Loki + Tempo | -- | Metrics, logs, traces, alerts |

---

## Quick Start

### Prerequisites

| Dependency | Version | Notes |
|:---|:---|:---|
| Go | 1.22+ | Gateway development |
| Python | 3.11+ | AI engine development |
| Flutter | 3.24+ | Mobile development |
| Docker | 24+ | Containerized deployment |
| Docker Compose | 2.x | Service orchestration |

### One-Command Setup

```bash
# 1. Clone the project
git clone https://github.com/BRSAMAyu/Sparkle-project.git
cd Sparkle-project

# 2. Configure environment
cp .env.example .env
# Edit .env with required configs (LLM API Key, Database, Redis)

# 3. Start infrastructure (PostgreSQL, Redis, MinIO)
make dev-up

# 4. Initialize database
make sync-db

# 5. Start backend services (two terminals)
make grpc-server    # Terminal 1: Python AI Engine
make gateway-dev    # Terminal 2: Go Gateway

# 6. Start mobile client (third terminal)
make mobile-run
```

### Common Commands

```bash
# Development
make dev-up              # Start infrastructure
make gateway-dev         # Start Go gateway (hot reload)
make grpc-server         # Start Python gRPC server
make mobile-run          # Start Flutter app

# Code Generation
make proto-gen           # Generate Protobuf code
make sync-db             # DB migration + SQLC generation
make mobile-gen          # Flutter code generation

# Task Queue
make celery-up           # Start Celery Worker + Beat
make celery-status       # Check queue status

# Health Checks
make smoke               # All services health check
make env-check           # Environment config check

# Testing
cd backend && pytest                    # Python tests (311 files)
cd backend/gateway && go test ./...     # Go tests (34 files)
cd mobile && flutter test               # Flutter tests (131 files)
```

---

## Project Structure

```
Sparkle-project/
+-- mobile/                             # Flutter mobile client
|   +-- lib/
|   |   +-- core/                       # Core infrastructure
|   |   |   +-- design/                 # Design System V2 (tokens, components, motion)
|   |   |   +-- experience/             # Experience profile system
|   |   |   +-- services/               # Global services (BGM, haptics, audio policy)
|   |   +-- features/                   # Feature modules (24 route modules)
|   |   |   +-- chat/                   # AI conversation
|   |   |   +-- task/                   # Task management
|   |   |   +-- galaxy/                 # Knowledge galaxy
|   |   |   +-- mirofish/               # Mirofish group-agent UI support
|   |   |   +-- focus/                  # Focus mode
|   |   |   +-- achievement/            # Achievement system
|   |   |   +-- community/              # Community
|   |   |   +-- ...                     # Plan, cognitive, error book, shop, etc.
|   |   +-- gen/                        # Protobuf generated code (78 files)
|   +-- test/                           # 131 test files
|
+-- backend/
|   +-- gateway/                        # Go gateway layer
|   |   +-- internal/
|   |       +-- handler/                # HTTP/WebSocket handlers (46 files)
|   |       +-- agent/                  # gRPC client
|   |       +-- middleware/             # 16 middleware (Auth, RateLimit, Security...)
|   |       +-- service/                # Business services (12 files)
|   |       +-- db/                     # Database layer (143 tables, SQLC)
|   |
|   +-- app/                            # Python AI engine (319 .py files)
|       +-- orchestration/              # LangGraph orchestration
|       +-- adapters/openclaw/          # OpenClaw execution adapter
|       +-- services/                   # 26 service files
|       +-- tools/                      # AI tool registry
|       +-- core/                       # Core (context, event bus, profiles)
|
+-- proto/                              # 6 Protobuf definitions (API contract source)
+-- monitoring/                         # Prometheus + Grafana + Loki + Tempo + 11 alert rules
+-- scripts/                            # Deploy, backup, acceptance scripts (21 scripts)
+-- docker-compose.yml                  # Development environment (17 services)
+-- Makefile                            # Build scripts
+-- CLAUDE.md                           # AI development assistant guide
```

---

## Engineering Metrics

| Metric | Value |
|:---|:---|
| Python test files | 311 |
| Go test files | 34 |
| Flutter test files | 131 |
| Acceptance scripts | 21 |
| CI Workflows | 13 |
| Pre-commit Hooks | 10 |
| Proto files | 6 |
| Database tables | 143 |
| Alembic migrations | 52 |
| Docker services | 17 |
| SLO alert rules | 11 |
| Go lint rules | 22 linters |
| Flutter lint rules | strict-casts + strict-inference + strict-raw-types |

---

## Documentation

| Document | Description | Audience |
|:---|:---|:---|
| [CLAUDE.md](CLAUDE.md) | Dev guide, architecture rules, code patterns | Developers |
| [Developer Docs Entry](docs/README.md) | Main entry for current development documentation | Developers / Product |
| [Technical Architecture](docs/00_项目概览/02_技术架构.md) | 3-layer architecture deep dive | Developers |
| [Knowledge Galaxy Design](docs/02_技术设计文档/02_知识星图系统设计_v3.0.md) | GraphRAG implementation details | Developers |
| [OpenClaw Execution Review](docs/architecture/SPARKLE_OPENCLAW_ALIGNMENT_REVIEW_v1.5.md) | Handoff, approval, comparison, self-verification, degradation | Developers / Product |
| [Mirofish Verification Checklist](docs/verification/本地发布前完整签收清单_2026-03-21.md) | Acceptance scope for Mirofish and linked product flows | Developers / QA |
| [CHANGELOG](CHANGELOG.md) | Version history | Everyone |
| [Frontend Experience Spec](docs/engineering/前端改进对齐文档_2026-03-22.md) | Multi-sensory experience system specification | Frontend developers |

---

## Contributing

We welcome all forms of contributions: bug reports, feature proposals, documentation improvements, and code PRs.

```bash
# 1. Fork this repository
# 2. Create feature branch
git checkout -b feature/amazing-feature

# 3. Commit changes (Conventional Commits)
git commit -m 'feat: add amazing feature'

# 4. Push and create Pull Request
git push origin feature/amazing-feature
```

---

## License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

**Sparkle** &nbsp;&middot;&nbsp; v1.0.0

*Helping everyone become their best self*

[![Flutter](https://img.shields.io/badge/Flutter-02569B?style=for-the-badge&logo=flutter&logoColor=white)](https://flutter.dev)
[![Go](https://img.shields.io/badge/Go-00ADD8?style=for-the-badge&logo=go&logoColor=white)](https://go.dev)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-FF6B6B?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)

</div>
loper Docs Entry](docs/README.md) | Main entry for current development documentation | Developers / Product |
| [Technical Architecture](docs/00_项目概览/02_技术架构.md) | 3-layer architecture deep dive | Developers |
| [Knowledge Galaxy Design](docs/02_技术设计文档/02_知识星图系统设计_v3.0.md) | GraphRAG implementation details | Developers |
| [API Design](docs/02_技术设计文档/05_API设计.md) | gRPC + WebSocket interfaces | Developers |
| [OpenClaw Execution Review](docs/architecture/SPARKLE_OPENCLAW_ALIGNMENT_REVIEW_v1.5.md) | Handoff, approval, comparison, self-verification, degradation | Developers / Product |
| [Mirofish Verification Checklist](docs/verification/本地发布前完整签收清单_2026-03-21.md) | Acceptance scope for Mirofish and linked product flows | Developers / QA |
| [CHANGELOG](CHANGELOG.md) | Version history | Everyone |
| [Frontend Experience Spec](docs/engineering/前端改进对齐文档_2026-03-22.md) | Multi-sensory experience system spec | Frontend devs |
| [Last Five Multi-Sensory Rounds](mobile/docs/multisensory_recent_five_rounds_alignment.md) | Recent BGM, motion, haptics, and settings refinements | Frontend devs |

---

## Contributing

We welcome all forms of contributions: bug reports, feature proposals, documentation improvements, and code PRs.

```bash
# 1. Fork this repository
# 2. Create feature branch
git checkout -b feature/amazing-feature

# 3. Commit changes (Conventional Commits)
git commit -m 'feat: add amazing feature'

# 4. Push and create Pull Request
git push origin feature/amazing-feature
```

---

## License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

**Sparkle** &nbsp;&middot;&nbsp; v1.0.0

*Helping everyone become their best self*

[![Flutter](https://img.shields.io/badge/Flutter-02569B?style=for-the-badge&logo=flutter&logoColor=white)](https://flutter.dev)
[![Go](https://img.shields.io/badge/Go-00ADD8?style=for-the-badge&logo=go&logoColor=white)](https://go.dev)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-FF6B6B?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)

</div>
