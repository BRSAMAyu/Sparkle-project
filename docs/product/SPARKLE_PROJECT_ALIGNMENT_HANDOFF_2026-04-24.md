# Sparkle 项目对齐交接文档

> **日期**: 2026-04-24
> **来源**: GLM1 独立审计员（代表 BRSAMA 首席架构师）
> **接收者**: Mo（MIMO 战略对齐）
> **用途**: 更新愿景锚定清单 v32 → v40+
> **范围**: Stage 33–40 落地事实 + Phase I Exit Gate 状态 + 已知缺陷

---

## 零、执行摘要

Phase I（Stage 33–40）已在 `integration/phase-i-exit` 分支全部落地。4 月 22–24 日间密集推进了 8 个 Stage、53 条治理规则、313 文件、+22,087/-2,481 行增量。

**Phase I Exit Gate 签字状态**： architects (Claude Opus) 已签 YES (ready with exception)。但 GLM1 独立红队审计发现多个 P0 缺陷，**建议撤回签字，修复后重新验收**。

---

## 一、Phase I 完成事实表

### Stage 33（愿景补全）— ACCEPT ✅

| WS | 内容 | 状态 |
|----|------|------|
| WS-33-01 | Social 数据进入 Router + Prompt | ✅ |
| WS-33-02 | SRL Phase 进入 Router + Prompt | ✅ |
| WS-33-03 | Working Memory 进入 Prompt（300 token budget） | ✅ |
| WS-33-04 | Journey Event 补全 | ✅ |
| Rule AS | Vision Compliance guard 落地 | ✅ |
| 86 backend tests | 全部通过 | ✅ |

**关键文件**: `routing_engine.py`, `dual_core_router.py`, `prompts.py`, `profile_context_service.py`

### Stage 34（数据流水）— ACCEPT ✅

| WS | 内容 | 状态 |
|----|------|------|
| WS-34-01 | Fill context builder memory lanes | ✅ |
| WS-34-02 | Wire journey event subscribers | ✅ |
| WS-34-03 | Recalibrate error replan bridge | ✅ |
| WS-34-04 | Archive orphan services + Rule AT | ✅ |
| WS-34-05 | Wire capsule preferences | ✅ |
| Rule AT | No Orphan Services guard | ✅ |

**注意**: WS-34-01 曾声称 "normalize 提取 bug"（F4），GLM1 独立验证证明该 bug **不存在**。F4 已标记为 FALSE，不应再作为修复项出现。

### Stage 35（Mobile 对等）— ACCEPT ✅

| WS | 内容 | 状态 |
|----|------|------|
| WS-35-01 | Render UserStateV1 profile cards | ✅ |
| WS-35-02 | Declare backend-only mobile parity fields | ✅ |
| WS-35-03 | Close metacognition router loop | ✅ |
| WS-35-04 | Add journey smoke coverage | ✅ |
| Rule AU | Mobile Parity guard，black-hole rate 0.000% | ✅ |
| Mobile tests | 6 files，含 idiographic/foresight/metacognition cards | ✅ |
| Journey smoke | 7-hop main + 3-hop error，CI 集成 | ✅ |

### Stage 36（工程硬化）— ACCEPT ✅

| WS | 内容 | 状态 |
|----|------|------|
| WS-36-01 | Base merge（tree-identity bookmark） | ✅ |
| WS-36-01.5 | Alembic heads 对齐 + 13 test drift fixes | ✅ |
| WS-36-02 | Token Bucket 量纲修复（ms×rate/s = 1000x bug） | ✅ |
| WS-36-03 | Theater IDOR 修复 | ✅ |
| WS-36-04 | OpenClaw SSRF 防护 | ✅ |
| WS-36-05 | 审计文档补入 | ✅ |
| Rule AW | Rate Limiter Sanity guard | ✅ |
| Rule Z-Theater | Theater user scope guard | ✅ |

**Token Bucket 修复**: `distributed_rate_limiter.go` 中 `elapsed_ms * rate_per_s` 缺少 ms→s 转换，导致令牌补充速率为预期的 1000 倍。已修复为 `(elapsed_ms / 1000.0) * rate_per_s`。

### Stage 37 Track A（Auth 硬化）— ACCEPT ✅

| WS | 内容 | 状态 |
|----|------|------|
| WS-37A-01 | Inventory wildcard and admin/internal routes | ✅ |
| WS-37A-02 | Per-user rate limiting | ✅ |
| WS-37A-03 | INTERNAL_API_KEY fail-closed + timing-attack resistance | ✅ |
| WS-37A-04 | Rule AX（Route Ownership） | ✅ |

**关键安全改进**: `internal_api.go` 现在空密钥直接拒绝，使用 `subtle.ConstantTimeCompare` 防时序攻击。

### Stage 37 Track B（LLM 安全层）— ACCEPT（含红队保留）

| WS | 内容 | 状态 |
|----|------|------|
| WS-37B-01 | LLM 调用点盘点（声称 47，实际 72） | ✅ |
| WS-37B-02 | LLM 安全层（663 行 `llm_security_wrapper.py`） | ✅ |
| WS-37B-03 | Rule AY（LLM Safety guard） | ✅ |

**红队保留**: 安全层存在重大绕过路径——详见 §三 P1-1。

### Stage 38（EventBus + Gateway + HNSW）— ACCEPT ✅

| WS | 内容 | 状态 |
|----|------|------|
| WS-38-03 | Expand journey event subscribers | ✅ |
| WS-38-04 | Error bridge tuning + simulation persistence | ✅ |
| WS-38-05 | Gateway FSM context alignment | ✅ |
| WS-38-06 | HNSW 索引（4 个 CONCURRENTLY 索引） | ✅ |
| WS-38-07 | Lock rules + handoff | ✅ |

**性能改进**: `document_chunks`、`knowledge_nodes`、`episodic_memories`、`scenes` 四张表的 embedding 列新增 HNSW 索引，向量相似度搜索从 O(n) 提升到 O(log n)。

### Stage 39（幂等性 + OCC + 认知闭环）— ACCEPT（含红队保留）

| WS | 内容 | 状态 |
|----|------|------|
| WS-39-01 | Atomic achievement photon grants | ✅ |
| WS-39-02 | Session completion dedup | ✅ |
| WS-39-03 | Atomic photon deductions | ✅ |
| WS-39-04 | Shop purchase idempotency | ✅ |
| WS-39-05 | OCC preference updates | ✅ |
| WS-39-06-10 | Cognitive loop wiring + handoff | ✅ |
| Rule BB | Financial Atomicity guard | ✅ |
| Rule BC | Idempotency Key guard | ✅ |

**认知闭环**: metacognition → context_builder → prompts → router → signal_collector → aggregator 完整闭环。`scaffolding_prompt_mode = live`，`cogload_route_mode = shadow`，`galaxy_inject_mode = shadow`。

**红队保留**: transfer_photons 存在竞态条件、session dedup 只覆盖 5/19+ 事件——详见 §三 P0-4/P0-5。

### Stage 40（Kill Switch 三态化 + Exit Gate）— ACCEPT（含红队保留）

| WS | 内容 | 状态 |
|----|------|------|
| WS-40-01 | Calendar kill switch（tri-state） | ✅ |
| WS-40-02 | Rule manifest 增补（53 条，23 leaf guards） | ✅ |
| WS-40-03 | Kill switch 三态核心 + Prometheus gauge | ✅ |
| WS-40-04 | Core/Phase headers（top-50 100%） | ✅ |
| WS-40-05 | Drill playbook（191 行） | ✅ |
| WS-40-06 | SGW dogfood（CONDITIONAL） | ⚠️ |
| WS-40-07 | Phase I Exit Gate + Phase II kickoff docs | ✅ |
| WS-40-08 | Rule BD 锁定 | ✅ |
| Rule AV | Kill Switch Mode Enum guard | ✅ |
| Rule BD | Phase I Exit Gate guard | ✅ |

**红队保留**: 3 个 kill switch 服务绕过核心（Stage 37 布尔、38/39 自定义 normalize）——详见 §三 P1-2。

---

## 二、F1–F15 闭合状态更新

愿景锚定清单 §十一记录的 15 个 Phase I 断点实际闭合状态：

| F# | 断点 | 声称状态 | 独立验证 | 备注 |
|----|------|---------|---------|------|
| F1 | Social→Router 断路 | ✅ Closed | ✅ 已验 | `routing_engine.py:167-205` 消费 social_signals |
| F2 | SRLPhase 全链路断 | ✅ Closed | ✅ 已验 | `routing_engine.py:208-228` 消费 srl_phase |
| F3 | WorkingMemory LLM 不可见 | ✅ Closed | ✅ 已验 | `prompts.py:2465` 渲染 WM，300 token budget |
| F4 | normalize 提取 bug | ✅ Closed | ✅ FALSE | **该 bug 不存在**，数据已作为顶级字段处理。不应列为修复项 |
| F5 | Hop 1/2 无 EventBus | ✅ Closed | ✅ 已验 | `journey_consumer_base.py` 消费者落地 |
| F6 | Calendar→Prompt 裸管道 | ✅ Closed | ✅ 已验 | Stage 40 Calendar kill switch，tri-state |
| F7 | 23 guard CI 不持续 | ✅ Closed | ✅ 已验 | manifest 53 条，CI `run_all_rule_guards.sh --jobs 4` |
| F8 | Kill Switch 无三态 | ✅ Closed | ⚠️ 部分 | 核心 16/19 已统一；**Stage 37/38/39 仍绕过核心** |
| F9 | Mobile 黑洞率 67% | ✅ Closed | ✅ 已验 | 0.000%（20 个字段，0 黑洞） |
| F10 | ErrorReplanBridge 门槛过保守 | ✅ Closed | ✅ 已验 | 新用户 ≥1 vs 老用户 ≥3 |
| F11 | 零文件 Core/Phase 声明头 | ⚠️ 延期 | ⚠️ 部分 | Top-50 100%，其余延至 Phase II |
| F12 | 21 个待决死件 | ✅ Closed | ✅ 已验 | Rule AT guard + `_deprecated/` 归档 |
| F13 | Metacognition 不入 router | ✅ Closed | ✅ 已验 | Stage 35 闭环，shadow mode by default |
| F14 | Kill Switch 零演练 | ✅ Closed | ✅ 已验 | 191 行 drill playbook + drill 脚本 |
| F15 | Push 定时批处理 | ✅ Closed | ✅ 已验 | Stage 18 确定性 push loop |

---

## 三、红队审计发现（GLM1 独立审查 2026-04-24）

以下为 GLM1 对 Phase I 集成分支进行红队式批判审查发现的缺陷。这些不是理论风险——全部有 `file:line` 级代码证据。

### P0 — 阻塞性缺陷

| ID | 问题 | 影响 | 证据 |
|----|------|------|------|
| **P0-1** | Alembic 双头（`s39b1c2d3e4` + `stage38_06`） | `alembic upgrade head` 直接崩溃，无法部署 | `alembic heads` 显示 2 heads |
| **P0-2** | 22 个测试失败（非 guard 测试） | "全绿" 仅适用于 guard 脚本，非 pytest | 4 Alembic + 2 monkeypatch + 1 缺属性 + 15 集成 |
| **P0-3** | 3 个生产文件导入即崩溃 | `next_step_service.py:10` 错用 `app.core.config`，任务完成流程生产崩溃 | `from app.core.config import settings` → 应为 `app.config` |
| **P0-4** | Photon 转账竞态条件 | 并发转账可导致余额为负（双花） | `photon_service.py:456-465` check-then-act 无锁 |
| **P0-5** | Session dedup 仅覆盖 5/19+ 事件 | `DAILY_CHECKIN`、`NODE_UNLOCKED` 等 14 种事件可重复触发成就奖励 | `achievement_engine.py:170-192` key 生成仅 5 种 |

### P1 — 高风险缺陷

| ID | 问题 | 影响 | 证据 |
|----|------|------|------|
| **P1-1** | LLM 安全层是安全剧场 | 正则消毒易绕过，白名单豁免 3 个核心文件覆盖 100% 流量，kill switch 可一键关 | `llm_safety.py:42-129`, `llm_secure_io.py:79-81` |
| **P1-2** | Kill Switch 三态声明虚假 | 3 个服务绕过核心（37=布尔，38/39=自定义），8 个 feature Redis 宕机默认 live | `settings.py:236,302-304,339-340` |
| **P1-3** | Shadow delta 不可观测 | Delta 只存 context_data（请求结束即丢弃），无日志/指标/告警 | `routing_engine.py:1209-1214` |
| **P1-4** | Guard AZ 只覆盖 6/38 EventBus 发布者 | 16% 覆盖率，32 个裸 `event_bus.publish` 未检查 | 硬编码 6 个 PUBLISH_TARGETS |
| **P1-5** | str(e) 残余泄漏 20+ 处 | 生产 500 错误泄漏内部异常信息 | `signals.py`, `capsules.py`, `tasks.py` 等 |

### P2 — 中等风险

| ID | 问题 | 证据 |
|----|------|------|
| P2-1 | OCC 仅保护 `update_inferred`，`update_explicit` 无 CAS | `preference_service.py:86-116` |
| P2-2 | Shop idempotency key 事务回滚后被消耗 | `shop_service.py:361` |
| P2-3 | 179 个测试被 skip（5 硬 skip + 16+ 条件 skip） | 多文件 |
| P2-4 | Protobuf gRPC 生成代码裸 import 崩溃 | `agent_service_pb2_grpc.py` |
| P2-5 | orchestrator.py 有 1 个重复方法（合并残留） | grep 去重检测 |

---

## 四、治理规则增长表

愿景锚定清单上次锁定在 22 条（Stage 20）。当前已增至 53 条 manifest + 若干 dev-only guard：

| 规则 | Stage | 用途 |
|------|-------|------|
| Rule AS | 33 | Vision Compliance — 附加字段必须被消费 |
| Rule AT | 34 | No Orphan Services |
| Rule AU | 35 | Mobile Parity — 黑洞率 ≤10% |
| Rule AV | 40 | Kill Switch Mode Enum |
| Rule AW | 36 | Rate Limiter Sanity — 量纲注释 + 指标 |
| Rule AX | 37A | Route Ownership — 公开/认证/内部/废弃声明 |
| Rule AY | 37B | LLM Safety — 禁止裸 vendor client |
| Rule AZ | 38 | EventBus Reliability |
| Rule BA | 38 | Gateway Contract Parity |
| Rule BB | 39 | Financial Atomicity |
| Rule BC | 39 | Idempotency Key |
| Rule BD | 40 | Phase I Exit Gate |
| Z-Theater | 36 | Theater User Scope |
| Z-EPISODIC | 34 | Episodic User Scope |

---

## 五、分支与合并状态

```
main (9011f356)                     ← 发布基线
├── 工程收尾 (80fc0879)             ← 当前工作分支，含 SGW v2 + README 重写
├── integration/phase-i-exit (e4741f2d) ← Phase I 集成，Stage 33-40 + 审计修复
│   ├── claude/stage37-track-a
│   ├── claude/stage37-track-b
│   ├── claude/stage38-impl
│   ├── claude/stage39-impl
│   └── claude/stage40-impl
├── codex/stage35-impl              ← Stage 35（stage34-head worktree）
└── codex/stage20-execution         ← Stage 36+ 的基础分支
```

**关键事实**:
- `integration/phase-i-exit` **未合并到 main**
- `工程收尾` **未合并到 main**
- 4 个 stash 条目存在但不会丢失（git 对象）

---

## 六、SGW（Simulated Gray Window）状态

SGW v2 meta-loop 已在 `工程收尾` 分支落地：
- `meta_loop.py`: 修复 evaluate_iteration 时序 bug（自比→下一轮比）
- `meta_orchestrator.py`: 扩展编排
- `test_rl_scaffolding.py`: +262 行新测试
- SGW dogfood 报告: CONDITIONAL（CLI/依赖已修，真跑需完整后端栈）
- Phase II 首项: 后端栈起动 → SGW 三模式真跑 → Go proto gen 落盘

---

## 七、产品定位更新

README 已在 `工程收尾` 分支重写，产品定位更新为：

> **Sparkle 是一个 AI 学习成长系统。**
> 短期形态：AI 学习教练。长期形态：AI 成长操作系统。
> 这不是两个产品，而是一条连续演进的曲线。

这与愿景锚定清单 §一的核心使命一致。

---

## 八、Phase II 方向（待 Mo 确认）

Phase I Exit Gate 文档列出的 Phase II 首批：

1. **P0 修复**（阻塞一切）: Alembic 合并头 + 幽灵导入 + 22 测试失败
2. **Photon 竞态修复**: transfer_photons 改为 `UPDATE WHERE balance >= amount`
3. **Kill Switch 真正统一**: Stage 37-39 接入核心三态
4. **LLM 安全层加固**: 去除白名单豁免 + 语义分析
5. **SGW 三模式真跑**: off/shadow/rl 完整测试
6. **Go proto gen 落盘**: 当前生成代码有裸 import 问题

---

## 九、Mo 更新建议

### 9.1 愿景锚定清单需要更新的章节

| 章节 | 更新内容 |
|------|---------|
| §十一 Phase I 执行 | Stage 33-40 全部 Closeout 完成，补入实际 WS 数和 Rule 数 |
| §十一 F1-F15 | F4 标记为 FALSE（bug 不存在），F8/F11 标记为部分闭合 |
| §十一 Phase I Exit Gate | 签字 YES with exception，但 GLM1 建议撤回（5 个 P0） |
| §九.x Stage 补充 | 新增 §9.22-9.29 覆盖 Stage 33-40 |
| §十一 版本记录 | 新增 v23-v32+ 条目 |
| §十一 新规则 | 补入 AS/AT/AU/AV/AW/AX/AY/AZ/BA/BB/BC/BD |

### 9.2 需要用户裁决的问题

1. **Phase I Exit Gate 是否撤回？** GLM1 建议撤回并修复 5 个 P0 后重新签字。Claude 已签 YES。用户最终裁定。
2. **LLM 安全层定位**: 当前是安全剧场。是接受（低安全姿态）还是投入加固？
3. **Shadow 模式价值**: Shadow delta 存在但不可观测。是投入可观测性还是承认 shadow = off？
4. **F4 FALSE 处置**: "normalize 提取 bug" 证明不存在。应从断点清单中移除还是标注为 "FALSE — 无需修复"？

---

## 十、文档索引（新增权威来源）

以下文档在 Phase I 期间产出，应纳入愿景锚定清单的权威来源列表：

```
docs/product/SPARKLE_AURORA_STAGE33_DISPATCH_PLAN_2026-04-22.md
docs/product/SPARKLE_AURORA_STAGE33_HANDOFF_2026-04-22.md      (隐含于 commit)
docs/product/SPARKLE_AURORA_STAGE35_HANDOFF_2026-04-22.md
docs/product/SPARKLE_AURORA_STAGE40_HANDOFF_2026-04-22.md
docs/product/SPARKLE_AURORA_PHASE_I_EXIT_GATE_2026-04-22.md
docs/product/SPARKLE_AURORA_PHASE_II_RL_OPTIMIZATION_KICKOFF_2026-04-22.md
docs/aurora/rule_as_vision_compliance.md
docs/aurora/rule_at_data_pipeline.md
docs/aurora/rule_au_mobile_parity.md
docs/aurora/rule_av_engineering_hardening.md
docs/aurora/rule_aw_rate_limiter_sanity.md
docs/aurora/rule_ax_route_ownership.md          (待确认路径)
docs/aurora/rule_ay_llm_safety.md               (待确认路径)
docs/aurora/kill_switch_drill_playbook.md
docs/aurora/stage40_sgw_dogfood_report.md
scripts/rule_guard_manifest.tsv                 (53 条规则)
```

---

*本交接文档由 GLM1 独立审计员基于 2026-04-24 代码级验证编写。所有结论均有 file:line 证据支撑。*
