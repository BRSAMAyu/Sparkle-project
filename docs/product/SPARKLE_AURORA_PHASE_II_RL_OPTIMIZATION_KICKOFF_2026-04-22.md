# SPARKLE AURORA Phase II RL Optimization Kickoff

架构师:请做最终签字验收。
- SGW dogfood: CONDITIONAL
- Kill Switch 三态化完成率: 12/12
- Phase I Exit Gate 建议: patch

日期: 2026-04-22  
阶段: Phase II kickoff draft

## 目标

Phase II 的唯一主题是: 用 SGW 的 RL 模式持续调优系统，而不是继续扩张新功能面。

首批优化目标:

1. `soft_violation_rate`
2. `authenticity_mean`
3. `session_completion_rate`

## 成功定义

在 `default` recipe 下完成 20 轮 RL 后，整体 reward 相比 Phase I 基线提升 `>= 15%`。

## 启动前提

1. SGW 必须有可重复的 OFF / SHADOW / RL 三模式入口。
2. `rl_trajectories`、`iterations`、dashboard artifacts 必须可稳定落盘。
3. Rule BD 需要从 `CONDITIONAL` 过渡到 `YES`，或者由架构师明确接受例外。

## Phase I -> Phase II Handoff

### 已就绪

- tri-state kill switch 基础设施已统一到 `backend/app/core/kill_switch.py`
- Rule AV / Rule BD guard 已入 manifest
- top-50 hot files 的 Core/Phase 声明头已脚本化补齐
- 12 个核心 kill switch drill 入口与 playbook 已落地
- RL scaffolding 自检 `26/26 tests passed`

### 待决项

1. SGW CLI 与 Stage 40 调度文不一致:
   - 缺少 `--rl-mode`
   - 缺少 `--rl-recipe`
   - 缺少 `--dashboard`
2. `docs/sgw/07_rl_system_handoff.md` 缺失，需补齐或确认替代规范
3. `stage39_memory_write_readiness_report.md` 未在当前仓库快照中发现

### 延后项

1. 全仓 Core/Phase 声明头补齐
2. SGW 非阻塞问题修复
3. quarantine 测试与任何需要的新 soak 规则

## 初始 Phase II Backlog

1. 暴露 SGW RL CLI 能力，使 Stage 40 dogfood 命令可原样执行
2. 把 dashboard 生成接到稳定 artifact 路径
3. 增加 policy snapshot / arm stats 的运行时导出
4. 用 holdout / diversity / exploration 指标建立 RL overfitting 观察面
5. 把 `soft_violation_rate / authenticity_mean / session_completion_rate` 作为默认 dashboard 头部 KPI

## 不在 Phase II 首周范围内

1. 新业务功能
2. proto 变更
3. mobile 新 surface
4. 非 RL 相关的治理返工
