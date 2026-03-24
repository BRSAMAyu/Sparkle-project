<div align="center">

# Sparkle

**AI-Powered Growth Operating System**

Not just answering questions — understanding you, growing with you, helping you become your best self.

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

<table>
<tr>
<td width="33%" align="center"><b>Traditional AI</b></td>
<td width="33%" align="center"><b>Learning/Productivity Apps</b></td>
<td width="33%" align="center"><b>Sparkle</b></td>
</tr>
<tr>
<td valign="top">

No memory — starts from scratch every time

Passive Q&A — no proactive guidance

Fragmented information — no system

Single conversation — no follow-up

Pure tool — no warmth

</td>
<td valign="top">

Static tags — coarse categorization

Preset paths — one size fits all

Linear notes — manual organization

Simple stats — no real insights

Random matching — shallow community

</td>
<td valign="top">

**Evolving cognitive profile** that deepens over time

**Goal-driven** — from "what to ask" to "who to become"

**Knowledge Galaxy** — auto-builds your knowledge network

**7-stage growth loop** — continuous companionship

**Cognitive matching** — find truly compatible partners

</td>
</tr>
</table>

---

## Core Capabilities

<table>
<tr>
<td width="50%" valign="top">

### AI Micro-Tutor

Not just answering — diagnosing your cognitive state.

When you say "this is hard", it analyzes your knowledge gaps, dynamically adjusts explanation depth, recommends targeted exercises, and tracks comprehension. 10+ specialized Agents collaborate dynamically to decompose complex problems.

</td>
<td width="50%" valign="top">

### Knowledge Galaxy

Your personal knowledge network visualized as a cosmic map.

Each concept is a star, mastery determines brightness, relationships form constellations. AI auto-identifies blind spots. The GraphRAG hybrid engine ensures every query understands context.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### Smart Task System

Six task types, AI-recommended based on your cognitive profile.

Learn, Review, Practice, Project, Reading, Custom — with built-in focus timer and mindfulness mode. Task completion auto-updates your profile, creating a learning flywheel.

</td>
<td width="50%" valign="top">

### Achievement Engine

Gamification that actually works.

Streaks build habits. Milestones record breakthroughs. Growth contracts provide commitment. Hidden achievements create surprise. Achievements aren't just numbers — they're proof of your growth.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### Community Learning

Intelligent matching based on cognitive profiles.

Accountability partners with similar thinking styles, study squads for long-term growth, sprint groups for goal focus, sync check-ins for mutual accountability.

</td>
<td width="50%" valign="top">

### Multi-Sensory Experience

A unified immersive experience design system.

Context-aware BGM and ambient audio that shifts with each screen. Semantic haptic feedback makes every interaction tangible. Entrance animations and celebration systems make growth visible. Graceful accessibility degradation.

</td>
</tr>
</table>

---

## Technical Moat

Sparkle's competitive edge isn't any single feature — it's the **combinatorial barrier of system-level architectural innovations**:

| Technical Barrier | Implementation | Industry Status |
|:-----------------|:---------------|:----------------|
| **Dual-Core Architecture** | Execution Core + Cognitive Core collaborate in real-time | Most products have a single conversation pipeline |
| **Evidence-Based 4D Profile** | Knowledge, Cognition, Motivation, Social — each backed by behavioral evidence | Typically static tags or simple statistics |
| **GraphRAG Hybrid Retrieval** | pgvector semantic search + Apache AGE graph traversal, fused ranking | Pure vector retrieval, no relational reasoning |
| **LangGraph Multi-Agent Orchestration** | 10+ Agent state machine, handoff, snapshots, interruptible streaming | Single Agent or simple chains |
| **7-Stage Growth Loop** | Sense > Clarify > Plan > Execute > Reflect > Reinforce > Adapt | Linear task flows, no closed loop |
| **Unified Multi-Sensory UX** | 5 experience profiles + sensory budget + particle budget + a11y degradation | Scattered animations, no system design |

---

## Architecture Overview

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

**Why three layers?**

- **Flutter** handles presentation and experience only — no business logic
- **Go Gateway** handles high-concurrency connections, auth, caching — no AI reasoning
- **Python Engine** handles all AI intelligence — no user authentication

Each layer has clear responsibilities and scales independently. The Gateway handles 10K+ WebSocket connections while the Engine scales AI compute horizontally.

---

<details>
<summary><b>Dual-Core Growth Operating System</b> (click to expand)</summary>

Sparkle's core innovation splits the AI system into two collaborative cores:

```
  ┌──────────────────────────┐    ┌──────────────────────────┐
  │    Execution Core         │    │    Cognitive Core         │
  │                          │    │                          │
  │  Goal Clarity → Assess   │    │  User Profile → Memory   │
  │      ↓                   │    │      ↓                   │
  │  Staged Plan → Execute   │    │  Cognitive Prism → EQ    │
  │      ↓                   │    │      ↓                   │
  │  Dynamic Adjustment      │    │  Continuous Companion    │
  └───────────┬──────────────┘    └──────────┬───────────────┘
              │                               │
              └──── Collaboration Layer ──────┘
                 Event Bus · Context Agg · Sync
```

The **Execution Core** handles "getting things done": defining goals, assessing feasibility, breaking down plans, providing execution guidance, adjusting strategies based on reality.

The **Cognitive Core** handles "understanding the user": continuously updating the 4D profile, accumulating long/short-term memory, perceiving thinking patterns through the Cognitive Prism, recognizing emotional states for personalized motivation.

The two cores don't run in isolation — they collaborate in real-time through an event bus. Execution results update the cognitive profile; cognitive understanding shapes execution strategy.

</details>

<details>
<summary><b>7-Stage Growth Loop</b> (click to expand)</summary>

Every Sparkle interaction is a complete growth cycle:

```
              Sense
                │
    ┌───────────┼───────────┐
    ↓           ↓           ↓
  Clarify     Plan      Execute
    ↑                       │
    │        Reflect        │
    │       ←───────────────┘
    │           │
    │     ┌─────┴─────┐
    │     ↓           ↓
    │  Reinforce    Adapt
    │                 │
    └─────────────────┘
```

| Stage | Responsibility | Technical Implementation |
|:------|:---------------|:-------------------------|
| Sense | Passively capture user signals | Behavior tracking, emotion recognition, learning trajectory |
| Clarify | Understand true intent | Intent recognition, context understanding, clarifying questions |
| Plan | Generate executable paths | Goal decomposition, path planning, resource matching |
| Execute | Run specific tasks | Task scheduling, tool invocation, progress tracking |
| Reflect | Analyze results | Outcome evaluation, error attribution, effect quantification |
| Reinforce | Consolidate learning | Spaced repetition, memory curves, achievement motivation |
| Adapt | Adjust strategy | Profile updates, strategy optimization |

</details>

<details>
<summary><b>Evidence-Based 4D Cognitive Profile</b> (click to expand)</summary>

We don't just track "what you know" — we understand "how you think". Every dimension is backed by **behavioral evidence**:

```
  ┌─────────────────────────────────────────────────┐
  │              4D Cognitive Profile                 │
  ├────────────────────┬────────────────────────────┤
  │                    │                            │
  │  Knowledge         │  Cognition                 │
  │  · Mastery (0-100) │  · Metacognition           │
  │  · Forgetting curve│  · Cognitive load          │
  │  · Learning rate   │  · Thinking style          │
  │  · Knowledge gaps  │  · Problem-solving style   │
  │                    │                            │
  ├────────────────────┼────────────────────────────┤
  │                    │                            │
  │  Motivation        │  Social                    │
  │  · Self-efficacy   │  · Collaboration style     │
  │  · Intrinsic ratio │  · Communication traits    │
  │  · Interest map    │  · Community contribution  │
  │  · Goal commitment │  · Peer influence          │
  │                    │                            │
  └────────────────────┴────────────────────────────┘
```

**Evidence sources**: conversation analysis, task completion quality and timing, review intervals and effectiveness, error pattern clustering, emotional signal recognition, community interaction behavior.

</details>

<details>
<summary><b>GraphRAG Hybrid Retrieval Engine</b> (click to expand)</summary>

Breaking through traditional RAG limitations by fusing semantic vector search with knowledge graph traversal:

```
  Query → ┬── pgvector Semantic Search (< 200ms)
          │    Semantically similar content chunks
          │
          ├── Apache AGE Graph Traversal (< 500ms)
          │    Prerequisites, follow-ups, related concepts
          │
          └── Fused Ranking
               Dedup → Dependency chain → Profile weighting → Context compression
               │
               ↓
           Personalized Response (total < 800ms)
```

| Capability | Traditional RAG | Sparkle GraphRAG |
|:-----------|:----------------|:-----------------|
| Semantic understanding | Vector similarity | Vector similarity |
| Knowledge relations | None | Graph traversal |
| Prerequisites | Not identified | Auto-linked |
| Personalization | None | Profile-weighted |
| Learning paths | None | Dependency chain generation |

</details>

<details>
<summary><b>LangGraph Multi-Agent Orchestration</b> (click to expand)</summary>

10+ specialized Agents collaborate dynamically:

```
  User Input → Orchestrator (Intent → Split → Dispatch → Aggregate)
                   │
         ┌─────────┼─────────┬─────────┬─────────┐
         ↓         ↓         ↓         ↓         ↓
      Knowledge   Math     Code    Reasoning  Planner
       Agent     Agent    Agent     Agent     Agent
         │         │         │         │         │
         └─────────┴─────────┴─────────┴─────────┘
                             │
                    Streaming Output (Interruptible)
```

- **Handoff mechanism**: Seamless context transfer between agents
- **State snapshots**: Checkpoint/resume for long tasks
- **PONR confirmation**: High-risk operations require user approval
- **Full observability**: Complete execution traces and decision chains

</details>

<details>
<summary><b>Multi-Sensory Experience System</b> (click to expand)</summary>

Not scattered animations — a **unified experience design system**:

| Layer | Capability | Details |
|:------|:-----------|:--------|
| **Experience Profiles** | 5 scene presets | Productive dashboard, AI conversation, immersive focus, warm social, celebration |
| **Audio Policy** | Page-level BGM + stage override | SceneAudioScope manages uniformly, no hard-cuts allowed |
| **Motion Primitives** | Staggered entry, attention pulse, exit transition | SparkleStagger / AttentionPulse / ExitTransition |
| **Haptic Feedback** | 27 semantic events | Same action triggers same feedback everywhere, global sensory budget |
| **Celebration System** | 3 intensity tiers + rarity glow | Global particle budget, auto-degrades on low-end devices |
| **Accessibility** | reduceMotion / large font / semantic labels | All enhancements degrade gracefully |

</details>

---

## Tech Stack

| Layer | Technology | Version | Rationale |
|:------|:-----------|:--------|:----------|
| **Mobile** | Flutter | 3.24+ | Cross-platform consistency, hot reload, rich widgets |
| | Riverpod | 2.x | Compile-time safe, declarative state management |
| **Gateway** | Go | 1.22+ | High concurrency, low memory, compiled |
| | Gin + gRPC | — | High-performance HTTP + strongly-typed cross-language calls |
| **AI Engine** | Python | 3.11+ | Rich AI ecosystem |
| | LangGraph | 0.3+ | Observable state machine, complex orchestration |
| | Celery | 5.x | Mature async task queue |
| **Data** | PostgreSQL | 16+ | ACID + rich extensions |
| | pgvector | 0.7+ | Native vector index |
| | Apache AGE | 1.5+ | PostgreSQL graph extension, Cypher queries |
| | Redis | 7+ | Cache, pub/sub, vector cache |
| **Storage** | MinIO | — | S3-compatible object storage |
| **Observability** | Prometheus + Grafana + Loki + Tempo | — | Metrics, logs, traces, alerts |

---

## Quick Start

### Prerequisites

| Dependency | Version | Notes |
|:-----------|:--------|:------|
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
cd backend && pytest                    # Python tests
cd backend/gateway && go test ./...     # Go tests
cd mobile && flutter test               # Flutter tests
```

---

## Project Structure

```
Sparkle-project/
├── mobile/                             # Flutter mobile client
│   ├── lib/
│   │   ├── core/                       # Core infrastructure
│   │   │   ├── design/                 # Design System V2 (tokens, components, motion)
│   │   │   ├── experience/             # Experience profile system
│   │   │   └── services/               # Global services (BGM, haptics, audio policy)
│   │   ├── features/                   # Feature modules (35 domain modules)
│   │   │   ├── chat/                   # AI conversation
│   │   │   ├── task/                   # Task management
│   │   │   ├── galaxy/                 # Knowledge galaxy
│   │   │   ├── focus/                  # Focus mode
│   │   │   ├── achievement/            # Achievement system
│   │   │   ├── community/              # Community
│   │   │   └── ...                     # Plan, cognitive, error book, shop, etc.
│   │   └── gen/                        # Protobuf generated code
│   └── test/                           # 81 test files
│
├── backend/
│   ├── gateway/                        # Go gateway layer
│   │   └── internal/
│   │       ├── handler/                # HTTP/WebSocket handlers
│   │       ├── agent/                  # gRPC client
│   │       ├── service/                # Business services
│   │       └── db/                     # Database layer (SQLC)
│   │
│   └── app/                            # Python AI engine
│       ├── orchestration/              # LangGraph orchestration
│       ├── services/                   # gRPC service implementations
│       ├── tools/                      # AI tool registry
│       └── core/                       # Core (context, event bus, profiles)
│
├── proto/                              # Protobuf definitions (API contract source)
├── monitoring/                         # Prometheus, Grafana, Loki, Tempo, alerts
├── scripts/                            # Deploy, backup, verification scripts
├── docker-compose.yml                  # Development orchestration
├── docker-compose.prod.yml             # Production orchestration (blue/green)
├── Makefile                            # Build scripts
└── CLAUDE.md                           # AI development assistant guide
```

---

## Documentation

| Document | Description | Audience |
|:---------|:------------|:---------|
| [CLAUDE.md](CLAUDE.md) | Dev guide, architecture rules, code patterns | Developers |
| [Technical Architecture](docs/00_项目概览/02_技术架构.md) | 3-layer architecture deep dive | Developers |
| [Knowledge Galaxy Design](docs/02_技术设计文档/02_知识星图系统设计_v3.0.md) | GraphRAG implementation details | Developers |
| [API Design](docs/02_技术设计文档/05_API设计.md) | gRPC + WebSocket interfaces | Developers |
| [CHANGELOG](CHANGELOG.md) | Version history | Everyone |
| [Frontend Experience Spec](docs/engineering/前端改进对齐文档_2026-03-22.md) | Multi-sensory experience system spec | Frontend devs |

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
