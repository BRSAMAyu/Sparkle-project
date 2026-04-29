# Sparkle Roadmap v3 — 工作跟踪文档

> **创建日期**: 2026-04-28
> **最后更新**: 2026-04-29
> **对应 Roadmap**: `docs/product/SPARKLE_ROADMAP_v3_2026-04-28.md`
> **用途**: 记录所有已完成、进行中、待做的工作, 支持并行推进与阶段审查

---

## 当前状态: Phase 0 生产基础设施硬化完成, Phase 1 后端核心完成, Phase 2 已有基础设施完备

---

## Phase 0: 生产基础设施硬化

### 0.1 TLS/HTTPS 终止
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T0.1.1 nginx.conf 添加 443 + SSL | ✅ 完成 | main | HTTP→HTTPS 重定向, TLSv1.2/1.3, HSTS |
| T0.1.2 docker-compose.prod.yml 挂载证书 | ✅ 完成 | main | SSL_CERT_DIR volume mount, 443 端口 |
| T0.1.3 SSL 证书生成脚本 | ✅ 完成 | main | scripts/ssl/generate_dev_certs.sh |
| T0.1.4 settings.py CORS HTTPS | ✅ 完成 | main | production 强制 PRODUCTION_URL=https, CORS 默认回填生产域名且仅允许 HTTPS |
| T0.1.5 Flutter 生产 API URL | ✅ 完成 | main | 已支持 String.fromEnvironment('API_BASE_URL'), release mode 警告 http |

### 0.2 崩溃报告 (Sentry)
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T0.2.1 backend/app/core/sentry.py | ✅ 完成 | main | FastAPI+Redis+Celery 集成 |
| T0.2.2 main.py startup init | ✅ 完成 | main | lifespan 中早期初始化 |
| T0.2.3 gRPC server sentry init | ✅ 完成 | main | grpc_server.py serve() |
| T0.2.4 .env.example Sentry DSN | ✅ 完成 | main | |
| T0.2.5 settings.py Sentry 字段 | ✅ 完成 | main | |
| T0.2.6 Flutter Sentry init | ✅ 完成 | main | main.dart 读取 SENTRY_DSN/SENTRY_ENVIRONMENT/SENTRY_RELEASE dart-define |

### 0.3 秘钥启动校验
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T0.3.1 settings.py production secret 校验 | ✅ 完成 | main | SECRET_KEY+POSTGRES+REDIS+MINIO+INTERNAL_API+LLM |
| T0.3.2 MinIO 默认值改为空 | ✅ 完成 | main | "minioadmin" → "" |
| T0.3.3 .env.example placeholder 注释 | ✅ 完成 | main | 头部警告 + REQUIRED 注释 |
| T0.3.4 check_production_secrets.py 脚本 | ✅ 完成 | main | 含引号去除, 开发跳过 |

### 0.4 基础设施安全加固
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T0.4.1 Grafana 密码必填 | ✅ 完成 | main | :? 语法, 未设则 docker compose 报错 |
| T0.4.2 JPush placeholder 移除 | ✅ 完成 | main | '' 默认 + jpushEffectiveEnabled guard |
| T0.4.3 MinIO credentials 从 env | ✅ 完成 | main | docker compose/gateway/init_minio_buckets 均要求显式 env, 不回退 minioadmin |
| T0.4.4 PRODUCTION_URL setting | ✅ 完成 | main | settings.py + .env.example |
| T0.4.5 Grafana 8 dashboard 预配置 | ✅ 完成 | main | provisioning 目录现有 8 个 dashboard JSON |

### 0.5 邮件服务配置
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T0.5.1 email 发送逻辑确认 | ✅ 完成 | main | 单测覆盖 disabled、缺 SMTP、STARTTLS 发送路径 |
| T0.5.2 SMTP 配置说明 | ✅ 完成 | main | docs/ops/smtp_configuration.md |
| T0.5.3 EMAIL_ENABLED 生产默认 | ✅ 完成 | main | 未显式设置时 dev=false, production=true |

---

## Phase 1: 核心闭环关闭

### 1.1 Breakpoint #5: Behavior-driven Push
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T1.1.1 notification_service 增强 | ✅ 完成 | main | Spine NotificationDirective 集成 |
| T1.1.2 session_end RecallOpportunity | ✅ 完成 | main | StreamChat 结束后触发召回检测 |
| T1.1.3 push_scheduler.py 新建 | ✅ 完成 | main | PushScheduler + recall queue + scheduler 集成 |
| T1.1.4 JPush 内容增强 | ⬜ 未开始 | — | |
| T1.1.5 Flutter 推送跳转 | ⬜ 未开始 | — | |
| T1.1.6 test_behavior_driven_push.py | ✅ 完成 | main | 12 tests passed |

### 1.2 Breakpoint #6: Structured CognitiveAdjustments
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T1.2.1 CognitiveAdjustment dataclass | ✅ 完成 | main | dimension/value/reason/evidence/scope/ttl/user_visible |
| T1.2.2 router 生成 structured_adjustments | ✅ 完成 | main | prompt_instruction 渲染 + routing_engine 透传 |
| T1.2.3 ux_envelope 从调整生成 | ✅ 完成 | main | ux_turn 含 user_visible structured_adjustments |
| T1.2.4 response_builder 结构化参数 | ✅ 完成 | main | response_metadata 含 structured_cognitive_adjustments |
| T1.2.5 Flutter WebSocket 传递 | ⬜ 未开始 | — | |
| T1.2.6 test_structured_cognitive_adjustments.py | ✅ 完成 | main | 7 tests passed (含 prompt_instruction + overlay 测试) |

### 1.3 Breakpoint #7: Verification Loop
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T1.3.1 outcome_tracker.py | ✅ 完成 | main | register_expected + record_actual + verify_pending |
| T1.3.2 register_expected_outcome | ✅ 完成 | main | 含 Redis 索引 + TTL 窗口 |
| T1.3.3 record_actual_outcome | ✅ 完成 | main | 触发 OutcomeRecorder 归因 |
| T1.3.4 attribution.py | ✅ 完成 | main | 已有 OutcomeRecorder._attribute (4 规则) |
| T1.3.5 learning_guard.py | ✅ 完成 | main | should_learn/retract/verdict 三层守卫 |
| T1.3.6 test_verification_loop.py | ✅ 完成 | main | 16 tests passed |

### 1.4 Outcome 回流闭环
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T1.4.1 9 类 directive outcome | ✅ 完成 | main | OutcomeRecorder 已支持 4 类归因规则 |
| T1.4.2 统一 outcome 写入 CausalTrace | ✅ 完成 | main | OutcomeTracker 链接 pending→trace→outcome |
| T1.4.3 Outcome Grafana dashboard | ⬜ 未开始 | — | |

### 1.5 Card Protocol 迁移
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T1.5.1 card_service.py 完善 | ⬜ 未开始 | — | |
| T1.5.2 planning_workflow Card 写入 | ⬜ 未开始 | — | |
| T1.5.3 TaskOccurrence 从 Card 生成 | ⬜ 未开始 | — | |
| T1.5.4 InterventionRecord 记录 | ⬜ 未开始 | — | |
| T1.5.5 Flutter Card 模型适配 | ⬜ 未开始 | — | |
| T1.5.6 双写一致性校验 | ⬜ 未开始 | — | |

---

## Phase 2-7: 简要索引 (详细任务在对应阶段展开时填写)

| Phase | 状态 | 开始日期 | 完成日期 |
|-------|------|----------|----------|
| Phase 2: Spine 深化 | ⬜ 未开始 | — | — |
| Phase 3: Aurora↔Spine | ⬜ 未开始 | — | — |
| Phase 4: 活体验打磨 | ⬜ 未开始 | — | — |
| Phase 5: P4 平台 | ⬜ 未开始 | — | — |
| Phase 6: 稳定性与规模化 | ⬜ 未开始 | — | — |
| Phase 7: 验收上线 | ⬜ 未开始 | — | — |

---

## 审查日志

| 日期 | Phase | 审查类型 | 发现问题 | 修复状态 |
|------|-------|----------|----------|----------|
| 2026-04-29 | Phase 1 | Opus Audit | outcome_recorder.py 重复方法定义, push_scheduler await sync method | ✅ 全部修复 |
| 2026-04-29 | Phase 1 | Claude Review | outcome_recorder._attribute() 死代码残留 (lines 229-246 重复 harmful/needs_confirmation 检查) | ⬜ 待修 |
| 2026-04-29 | Phase 1 | Claude Review | outcome_tracker 非原子 Redis 操作 (lpush+ltrim+expire 未用 pipeline) | ⬜ 待修 |
| 2026-04-29 | Phase 1 | Claude Review | push_scheduler UUID(user_id) 缺少 try-except, 格式异常会中断 queue 处理 | ⬜ 待修 |
| 2026-04-29 | Phase 1 | Claude Review | learning_guard.should_learn() lines 56-57 冗余分支 | ⬜ 待修 |
| 2026-04-29 | Phase 1 | Claude Review | 5 个方法缺单元测试 (build_self_correction_receipt, verify_pending, get_guard_verdict 等) | ⬜ 待补 |

---

## 提交日志

| 日期 | Commit | Phase | 范围 |
|------|--------|-------|------|
| 2026-04-29 | 276bce8b | Phase 0 | Complete production hardening — CORS HTTPS, Flutter Sentry, MinIO env, Grafana dashboards, SMTP |
| 2026-04-29 | a9ec2ac3 | Phase 1 | Breakpoints #5/#6/#7 — structured adjustments, behavior-driven push, verification loop |
| 2026-04-29 | e1812b92 | Phase 1 | Prometheus outcome metrics + Grafana outcome dashboard |
| 2026-04-29 | 93b72fd4 | Phase 1 | Audit fixes — dedup outcome_recorder, async record_sent |
