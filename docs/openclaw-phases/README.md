# Sparkle x OpenClaw 深度整合 — 6阶段执行方案

## 执行顺序

按以下顺序依次喂给coding agent:

| 阶段 | 文件 | 范围 | 核心交付 |
|------|------|------|---------|
| **Phase 1** | `PHASE_1_EXECUTION_UX_NATIVE.md` | Flutter | 3个新widget + 重构BottomControls + 感官反馈绑定 + 拒绝理由sheet |
| **Phase 2** | `PHASE_2_AI_SYSTEM_INTEGRATION.md` | Python + Flutter | Orchestrator执行意图检测 + UX信封第6模式 + 聊天流建议卡/内联结果 |
| **Phase 3** | `PHASE_3_PROFILE_DEEP_LOOP.md` | Python | 4条新学习信号 + 执行画像聚合服务 + 画像API + Replanner增强 |
| **Phase 4** | `PHASE_4_CONNECTION_ARCHITECTURE.md` | Flutter + Python | 连接管理服务 + 设置页 + 健康检查 + 连接状态感知 |
| **Phase 5** | `PHASE_5_RESULT_DISPLAY_AND_LLM_OPT.md` | Flutter + Python | 结果渲染器 + 分类缓存 + 模板prompt优化 + 结果预验证 |
| **Phase 6** | `PHASE_6_OBSERVABILITY_AND_POLISH.md` | Flutter + Python | 报告板块 + 管理Dashboard + 自动降级 + 文案体系 + 无障碍 |

## 依赖关系

```
Phase 1 (无依赖)
  ↓
Phase 2 (依赖Phase 1的widget)
  ↓
Phase 3 (依赖Phase 2的AI链路)
  ↓
Phase 4 (依赖Phase 1的执行UI)  ← 可与Phase 3并行
  ↓
Phase 5 (依赖Phase 1+2的widget)  ← 可与Phase 4并行
  ↓
Phase 6 (依赖全部)
```

## 总改动量估算

- **新文件**: ~16个 (9 Flutter, 7 Python)
- **修改文件**: ~20个 (跨6个Phase, 部分重叠)
- **新增测试**: ~15个测试用例

## 每阶段完成后的检查命令

```bash
# Flutter
cd mobile && flutter analyze --no-fatal-infos

# Python
cd backend && python -m pytest tests/ -x -q
```
