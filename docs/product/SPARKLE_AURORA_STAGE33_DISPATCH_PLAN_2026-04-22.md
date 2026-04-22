# Sparkle Aurora Stage 33 Dispatch Plan

## 范围

Stage 33 聚焦 Vision Compliance Closure，只处理四件事：

1. Social -> Router + Prompt
2. SRL -> Router + Prompt
3. Working Memory -> Prompt
4. `user.registered` / `plan.created` Journey Event 补全

## 默认模式

所有 Stage 33 开关默认 `shadow`：

- `AURORA_STAGE33_MODE`
- `AURORA_STAGE33_SOCIAL_MODE`
- `AURORA_STAGE33_SRL_MODE`
- `AURORA_STAGE33_WM_PROMPT_MODE`
- `AURORA_STAGE33_EVENTS_MODE`

## 已落地交付

### WS-33-01

- `social_context_v1` 进入 `DualCoreRoutingInput.social_signals`
- Prompt 新增 `## 社群信号 [L2 引导]`
- `routing_decision_log` 写入 `stage33_shadow_delta.social` / `stage33_contributions.social`

### WS-33-02

- `ProfileContext.user_insight_state.srl_phase` 进入 `DualCoreRoutingInput.srl_phase_hint`
- Prompt 新增 `## 学习自调节阶段`
- Router 支持 `forethought / performance / reflection` 三态约束
- shadow/live 均可写 `stage33_shadow_delta.srl`

### WS-33-03

- `working_memory_snapshot` 经 `ContextBuilderMixin` 注入用户上下文
- Prompt 新增 `## 工作记忆（近 30 分钟）`
- 使用硬上限 300 token，超限时直接压缩 section

### WS-33-04

- 注册成功后发布 `user.registered`
- `PlanService.create()` 直接建计划路径发布 `plan.created`
- `shadow/live` 事件都附带 `metadata.stage33_mode`

## 守卫

- Rule AS: `scripts/guards/check_rule_as_vision_compliance.py`
- Rule Z social: `scripts/guards/check_rule_z_social_cross_user.py`
- 两者均已加入 `scripts/rule_guard_manifest.tsv`

## 演练

- 脚本: `scripts/stage33/drill_transitions.sh`
- 路径: `off -> shadow -> live -> shadow -> off`
- 每次切换都会写一条本地审计记录
