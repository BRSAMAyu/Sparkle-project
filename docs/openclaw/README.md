# OpenClaw 集成

Sparkle 与 OpenClaw 的深度整合文档。

## 核心文档

| 文档 | 内容 |
|------|------|
| [OPENCLAW_QUICKSTART](./SPARKLE_OPENCLAW_QUICKSTART.md) | 快速入门 |
| [OPENCLAW_CONNECTION_GUIDE](./OPENCLAW_CONNECTION_GUIDE.md) | 连接指南 |
| [SPARKLE_OPENCLAW_IMPLEMENTATION_SPEC_v1.0](./SPARKLE_OPENCLAW_IMPLEMENTATION_SPEC_v1.0.md) | 完整实施规范 |
| [OPENCLAW_COMMERCIAL_GRADE_MASTERPLAN](./OPENCLAW_COMMERCIAL_GRADE_MASTERPLAN.md) | 商业级方案（Phase 5-10） |
| [ALIGNMENT_REVIEW_v1.5](./SPARKLE_OPENCLAW_ALIGNMENT_REVIEW_v1.5.md) | 最新对齐评审 |

## 6阶段执行方案

按以下顺序依次执行：

| 阶段 | 文件 | 范围 |
|------|------|------|
| **Phase 1** | [PHASE_1_EXECUTION_UX_NATIVE](./PHASE_1_EXECUTION_UX_NATIVE.md) | Flutter |
| **Phase 2** | [PHASE_2_AI_SYSTEM_INTEGRATION](./PHASE_2_AI_SYSTEM_INTEGRATION.md) | Python + Flutter |
| **Phase 3** | [PHASE_3_PROFILE_DEEP_LOOP](./PHASE_3_PROFILE_DEEP_LOOP.md) | Python |
| **Phase 4** | [PHASE_4_CONNECTION_ARCHITECTURE](./PHASE_4_CONNECTION_ARCHITECTURE.md) | Flutter + Python |
| **Phase 5** | [PHASE_5_RESULT_DISPLAY_AND_LLM_OPT](./PHASE_5_RESULT_DISPLAY_AND_LLM_OPT.md) | Flutter + Python |
| **Phase 6** | [PHASE_6_OBSERVABILITY_AND_POLISH](./PHASE_6_OBSERVABILITY_AND_POLISH.md) | Flutter + Python |

## 每阶段验证

```bash
cd mobile && flutter analyze --no-fatal-infos
cd backend && python -m pytest tests/ -x -q
```
