# Reviewer A — E03: Kill Switch实效性——off/shadow/live切换是否真正生效
Timestamp: 2026-04-26T11:35:00+08:00
Chain Index: 16

## Chain Flow Summary

Kill switch 是 Aurora 各阶段功能的安全阀门：运维可以通过 Redis/配置将任意功能设为 off（关闭）、shadow（计算但不生效）、live（全功能）。本链审计 tri-state 在 20+ 服务中是否真正按语义工作，shadow 模式是否真正"只计算不应用"，Prometheus 指标是否准确，drill 脚本是否覆盖关键路径。

## Critical Issues 🔴

**1. Idiographic Association shadow 模式 = live 模式 (数据污染)** `backend/app/services/idiographic_association_service.py:192`
- `compute_and_update()` 仅检查 `mode == "off"`，shadow 模式下执行全部操作：upsert daily vectors、upsert changepoints、upsert associations（均写入 DB）、发布 `idiographic.updated` 事件、写入 summary cache
- Expected: shadow 模式计算但不写入 DB、不发布事件。Actual: shadow 与 live 行为完全一致，所有 DB 写入和事件均执行
- Evidence: 第 192 行 `if mode == "off":` 是唯一分支，之后无 shadow/live 区分

**2. SRL Phase Tracker shadow 模式 = live 模式 (数据污染)** `backend/app/services/srl_phase_tracker_service.py:118`
- `handle_transition_event()` 仅检查 `mode == "off"`，shadow 模式下执行完整状态转换：获取分布式锁、转换状态、持久化到 DB、记录 metrics
- Expected: shadow 模式下仅计算不持久化。Actual: shadow 与 live 完全一致
- Evidence: 第 118-119 行 `await self.kill_switch.get_mode() == "off"` 是唯一退出条件

**3. Social Signal Bridge 完全没有 kill switch** `backend/app/services/social_signal_bridge.py`
- 该服务处理 accountability struggle 检测、伙伴通知推送、社交信号聚合，但无任何 kill switch 集成
- grep 确认：文件中无 `kill_switch`、`read_mode`、`KillSwitchBinding` 任何引用
- 这意味着该服务永远以完全能力运行，无法在出问题时安全降级

**4. State Aggregator 没有 kill switch** `backend/app/state_aggregator/service.py`
- 核心状态聚合服务从 15+ 子系统计算 UserStateV1，但没有任何 kill switch 保护
- grep 确认：state_aggregator 目录中无 kill_switch 相关代码
- 如果任何子系统产出异常数据，无法通过 kill switch 降级聚合器

**5. Aurora privacy.py 没有 kill switch** `backend/app/aurora/privacy.py`
- PII 脱敏（redact_pii、sha256_token、laplace_noise）始终运行，无 off/shadow/live 控制
- grep 确认：文件中无 kill_switch 相关代码
- 这虽然对安全性是好事（不应关闭 PII 脱敏），但 shadow 模式无法用于验证脱敏效果而不影响日志

## Major Issues 🟡

**6. shadow 语义不一致——三种不同解读并存**
- **Shadow = Live**: Idiographic Association（全量 DB 写入）、SRL Phase Tracker（全量处理）
- **Shadow = Off**: Scene Consolidation（`mode != "live"` 返回空，shadow 与 off 等效）`backend/app/services/scene_consolidation_service.py:273`
- **Shadow = True Tri-State**: Policy Scheduler（计算+记录但不执行 action）`backend/app/services/policy_scheduler_service.py:224`、Push Service（评估但不发送）`backend/app/services/push_service.py:148`
- 无统一的 shadow 行为规范，每个服务开发者自行解读

**7. 仅 8 个 drill 脚本覆盖 20+ kill switch 服务**
- 存在 drill 脚本的阶段：Stage 33, 34, 35, 37, 38, 39, 40
- 缺少 drill 脚本的阶段：Stage 18, 19, 21, 23, 24, 25, 26, 27, 28, 29, 30, 31
- Stage 18（Push）和 Stage 23（Bayesian）是关键用户触达路径，却无 drill 验证

**8. Admin API 仅覆盖 3 个阶段** `backend/app/api/v1/memory_admin.py`
- 仅 Stage 18, 19, 21 有 `/admin/memory/stage{N}/killswitch` 端点
- 其余 17+ 阶段需要直接操作 Redis 或修改配置文件
- 运维在紧急情况下无法快速切换大部分 kill switch

**9. Kill switch 设置未写入 .env.example**
- ~45 个 `AURORA_*_MODE` 设置在 `settings.py` 中定义，但不出现在 `.env.example` 中
- 运维无法通过查阅文档发现可用的 kill switch 参数
- Evidence: `.env.example` 文件中无 `AURORA_.*_MODE` 条目

## Minor Issues 🟢

**10. Drill 脚本仅验证模式切换，不验证行为差异** `scripts/stage33/drill_transitions.sh`
- drill 仅检查 mode 是否成功设置并记录 audit log
- 不验证服务在 shadow 模式下是否真的跳过了 DB 写入或事件发布
- 对于 Idiographic/SRL 这种 shadow=live 的 bug，drill 无法发现

**11. Stage 37 LLM Safety 使用布尔值而非 tri-state** `backend/app/config/settings.py`
- `AURORA_STAGE37_LLM_SAFETY_ENABLED` = True（布尔），不符合 tri-state 规范
- 无法设为 shadow 模式进行安全测试

## Working Well ✅

- **Core kill_switch.py 实现扎实**: tri-state 标准化（含别名映射如 "0"→"off"、"1"→"live"）、Redis 运行时覆盖、settings 回退、legacy bool 迁移路径全部正确 `backend/app/core/kill_switch.py`
- **Policy Scheduler (Stage 24) 正确实现 tri-state**: shadow 模式评估策略并记录 DB 但不执行 action，是理想的 shadow 行为范本 `backend/app/services/policy_scheduler_service.py:224`
- **Push Service (Stage 18) 正确实现 tri-state**: shadow 模式评估触发条件但标记 `shadowed: True` 且不发送推送 `backend/app/services/push_service.py:148`
- **Prometheus 指标正确**: `KILL_SWITCH_MODE` gauge 在 read_mode() 和 write_mode() 中均自动更新，值映射正确（0/1/2）`backend/app/core/metrics.py`
- **自动降级模式设计精良**: Stage 25/26/28/29 基于质量指标自动降级到 shadow，是安全系统的优秀实践
- **KillSwitchBinding 数据结构设计良好**: 支持 master/feature 层级、legacy bool 迁移、allowed_modes 约束

## Files Examined

- `backend/app/core/kill_switch.py` — 核心 tri-state 实现
- `backend/app/core/metrics.py` — KILL_SWITCH_MODE gauge 定义
- `backend/app/aurora/privacy.py` — PII 脱敏（无 kill switch）
- `backend/app/services/social_signal_bridge.py` — 社交信号桥（无 kill switch）
- `backend/app/services/idiographic_association_service.py` — shadow=live bug
- `backend/app/services/srl_phase_tracker_service.py` — shadow=live bug
- `backend/app/services/aurora_stage*_kill_switch_service.py` — 20+ kill switch 服务文件
- `backend/app/services/policy_scheduler_service.py` — 正确 tri-state 实现
- `backend/app/services/push_service.py` — 正确 tri-state 实现
- `backend/app/services/scene_consolidation_service.py` — shadow=off 实现
- `backend/app/config/settings.py` — ~45 个 kill switch 设置
- `backend/app/api/v1/memory_admin.py` — Admin API（仅 3 阶段）
- `backend/app/state_aggregator/service.py` — 无 kill switch
- `scripts/stage33/drill_transitions.sh` — drill 脚本范本
- `scripts/stage34-40/drill_transitions.sh` — 其他 drill 脚本
- `.env.example` — 缺少 kill switch 文档

## Confidence: High — 所有发现均有具体代码行号和 grep 验证，shadow=live bug 已通过阅读完整方法体确认
