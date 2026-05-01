# Sparkle Roadmap v3 R4 Final Acceptance Review — Codex

> 日期: 2026-04-29
> 角色: 审核者 / 验收者 / 设计者
> 范围: Claude 声明 Phase 0-6 完成、Phase 7 剩余人工/运维任务后的独立复核
> 重点: 关键架构、高技术难度路径、Aurora 与用户体验

## 结论

不能把当前状态验收为“Phase 0-6 完全生产就绪”。更准确的判断是:

- Phase 0-5: 大部分主线实现可接受, 仍需按愿景清单做体验验收。
- Phase 6: 稳定性/上线自动化框架已经有明显进展, 但存在未完成压测、成本熔断未接入生产路径、蓝绿部署口径不一致等验收阻塞。
- Phase 7: 自动化检查脚本存在, 但用户测试、生产环境、SSL/secrets、迁移、备份恢复仍是未完成的真实上线门槛。

本轮已直接修复两个低风险问题:

- `scripts/production_readiness_check.sh`: 修复 `--skip-flutter` 拼写错误、从任意工作目录运行时的路径误判、进入 `backend/` 后导致部署产物检查失败的问题。
- `backend/app/core/cost_controller.py`: Redis 不可用时预算读取/记录不再抛异常; Prometheus 估算成本仍会记录。新增 2 条单测。

## 验收证据

| 检查 | 结果 |
|---|---|
| `bash -n scripts/production_readiness_check.sh scripts/blue_green_switch.sh scripts/chaos_drill.sh scripts/deploy-prod.sh scripts/deploy_k8s.sh` | 通过 |
| `cd backend && pytest tests/unit/test_cost_controller.py -q` | 18 passed |
| `kubectl kustomize k8s/prod/blue` | 可渲染, 但提示 `commonLabels` deprecated |
| 先前 targeted suite: `routing_engine_dual_core + t34 + llm safety + spine_event_bridge` | 72 passed, 2 warnings |

## 关键发现

### R4-P0-01 — Phase 6 仍有明确未完成任务

Tracker 顶部写着 “Phase 0-6 完成”, 但 Phase 6 明细中 `T6.1.6 压力测试 100 并发` 仍是未开始。没有 k6/locust 脚本或压测报告时, 不能验收“规模化/稳定性完成”。

影响: 这不是普通文档问题, 它直接影响 Phase 7 上线前的容量信心。

处理建议: 新增压测脚本与报告产物; 验收口径改成 “Phase 6 除压测与生产演练证据外代码完成”。

### R4-P0-02 — 蓝绿部署完成声明口径不一致

Tracker 把 `scripts/blue_green_switch.sh` 作为 T6.2/T7.3.5 完成证据, 但该脚本主要维护 `/tmp/sparkle_active_slot`, 启停 idle slot 并跑固定 `localhost:8080/8000` 健康检查; 它不更新 nginx upstream、不 patch K8s service、不切 DNS/LB, 因此不能单独证明生产流量切换。

同时, `scripts/deploy-prod.sh` 确实有更接近真实 Docker Compose 蓝绿发布的逻辑: 更新 `nginx/upstream.conf`、reload nginx、冒烟、观察、失败回滚、停止旧 gateway。`scripts/deploy_k8s.sh` 也有 K8s service selector patch 流程。

影响: 不是“完全没做”, 而是验收证据引用了弱脚本, 容易误判生产发布能力。

处理建议: 选定正式生产路径。若走 Docker Compose, Tracker 应把 `deploy-prod.sh + deploy-prod.yml` 作为验收对象; 若走 K8s, 需要补 active service/namespace/secrets/ingress 的实集群演练记录。

### R4-P1-01 — RAG/Aurora 成本熔断是库级实现, 尚未接入生产主链

`backend/app/core/cost_controller.py` 实现了 `record_rag_cost()`、`record_aurora_cost()`、`is_rag_within_budget()`、`is_aurora_within_budget()` 和 `BudgetCircuitBreaker`, 但全仓搜索显示这些入口只被成本控制单测引用, 没有接入 RAG 检索、Aurora L3/L4 wake、Core Session 或运行时编排主路径。

影响: T6.4.2-T6.4.4 不能按“生产成本守卫完成”验收。当前更像“成本守卫组件完成, 生产接线待做”。

处理建议: 先对齐预算策略是 fail-open 还是降级到 L0/L1, 再接入 RAG retrieval 与 Aurora energy/session 启动路径, 并加端到端测试证明预算超限会改变用户可见行为。

### R4-P1-02 — Aurora live 开关与审查文档互相矛盾

`docs/engineering/SPARKLE_AURORA_FEATURE_STATUS_AUDIT_2026-04-29.md` 声称大量 Aurora 能力仍是 off/shadow; 但 `backend/app/config/settings.py`、`backend/.env.example`、`docker-compose.prod.yml` 中大量 Aurora 开关默认或生产配置已经是 `live`, 包括 Stage18 push policy/delivery、Stage19 working memory、Bayesian、Foresight、SRL、Traits、Idiographic 等。

影响: 这是 Aurora 这种核心创新点的发布治理风险。若缺少逐项 canary/rollback/体验验收证据, 一次性 live 会放大误判、成本、记忆污染、错误推送和用户信任风险。

处理建议: 建立 Aurora Release Manifest: 每个 live 开关必须有 owner、验收测试、SLO、回滚开关、用户可见风险、与 Spine/Outcome 的闭环证据。文档状态和真实配置必须同步。

### R4-P1-03 — 首页 Aurora 状态带的纠偏 chip 没有进入结构化反馈闭环

聊天内的 `StatusAwarenessBar` 和 Aurora Core Session 会调用 `/aurora/telemetry/chip-selected`, 但首页 `AuroraStatusBand` 的纠偏 chip 只跳转到 chat 并传 `initial_user_message: opt.label`。这会让“用户点了纠正”变成一条普通聊天入口, 而不是带 `semantic_value/is_disconfirming/is_freeform` 的结构化修正事件。

影响: 用户体验上看似可纠偏, 但 Aurora 不一定能把首页状态带的纠正稳定写回 `CorrectionFeedbackProcessor`。这触碰愿景清单里“一票否决项 3: 用户关键反馈只被记录, 不改变下一步行动”。

处理建议: 首页状态带 chip 应直接提交 telemetry, 或打开 Core Session 并携带 option id / semantic_value / target_state_key。跳转 chat 可以保留, 但不能替代反馈闭环。

### R4-P1-04 — 愿景验收清单主路径被删除, 文档工作流存在漂移

当前工作区显示 `docs/product/愿景验收清单` 被删除, 但 `docs/product/critical_files/愿景验收清单` 仍存在副本。该清单是 Phase 7 最终验收核心, 不应只以 critical_files 副本形式存在而不更新主路径。

影响: 后续多 agent 审查会引用不同来源, 导致“完成标准”漂移。

处理建议: 确认这是否是有意归档。如果不是, 应恢复主路径并在 Tracker 中固定为 Phase 7 验收源文件。

### R4-P2-01 — `production_readiness_check.sh` 是本地预检, 不是完整生产验收

本轮已修复脚本路径问题, 但它仍主要检查本地 Docker、localhost 健康、env 默认值、Prometheus/Grafana、本地测试收集和部署产物存在性。它不验证真实域名、SSL、K8s secrets、生产迁移、备份恢复、远端监控、真实用户流量或回滚演练。

影响: T7.1 自动化验证框架可以接受为“预检脚本”, 但不能替代 T7.3 的运维验收。

处理建议: Phase 7 需要独立的 production acceptance runbook, 把人工/运维项和命令证据分开记录。

## Aurora 体验验收判断

Aurora 的代码面已经远超“概念原型”: 有分层能级、状态带、纠偏、Core Session、Spine 反馈、偏好、冷却和若干学习/记忆模块。但以用户体验验收口径看, 还不能只凭实现数量宣布完全体:

- 用户可见层必须证明: 状态带展示的判断, 用户能理解、能纠正, 且纠正会改变下一步行动。
- 高能级 Aurora 必须证明: L3/L4 不会被 cooldown override、成本预算、live 默认开关绕过。
- 长期模型必须证明: 纠偏和 Outcome 先归因再写入, 不把短期压力误写成人格/长期画像。

## 推荐下一步

1. 先不要继续扩大 Phase 7 完成声明, 把 R4-P0/P1 放入 Tracker 的待复核项。
2. 对齐正式生产部署路径: Docker Compose blue-green 还是 K8s blue-green。
3. 接入成本熔断到 RAG/Aurora 主路径, 并补端到端行为测试。
4. 修复首页 Aurora 状态带纠偏闭环, 确保用户的关键纠正进入 telemetry/Core Session/StateRegister。
5. 恢复或确认愿景验收清单主路径, 然后按清单逐项打分, 不用“代码存在”代替体验验收。
