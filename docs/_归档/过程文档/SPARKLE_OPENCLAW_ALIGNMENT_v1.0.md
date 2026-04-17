# Sparkle × OpenClaw 集成对齐文档 v1.0

> **日期**: 2026-03-28 | **状态**: 全量验收通过 | **回归**: 37 passed

---

## 1. 做了什么

Sparkle 原本擅长规划和认知分析，但执行环节始终依赖用户手动完成。本次集成在 Sparkle 与 OpenClaw（自托管 AI 执行网关）之间建立了一条**完整的执行闭环链路**：

```
用户需求 → 任务拆解 → 路由判定 → 委派执行 → 信任评估 → 结果摄取 → 画像回流 → 优化未来规划
```

所有代码均为**增量添加**，现有生产流程零影响。通过 `OPENCLAW_ENABLED=false`（默认）开关控制，关闭时系统行为与集成前完全一致。

---

## 2. 架构总览

```
┌──────────────────────────────────────────────────────────────────────┐
│  Flutter Mobile                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ TaskExecutionScreen                                             │ │
│  │  ├─ "交给 AI 执行" 按钮 → 选择模板 → handoff                     │ │
│  │  ├─ 执行状态卡 (DISPATCHED / RUNNING / WAITING_APPROVAL / 终态)  │ │
│  │  ├─ 确认 / 拒绝 / 取回 按钮                                      │ │
│  │  └─ 终态自动停轮询                                               │ │
│  └─────────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│  Python Engine                                                       │
│                                                                      │
│  ExecutionRouter ──→ ExecutionService ──→ ExecutionIngestor         │
│       │                    │                      │                  │
│       │                    ├─ TemplateService      ├─ TrustEngine    │
│       │                    ├─ NodeService          ├─ ResultParser   │
│       │                    ├─ QualityService       ├─ LearningService│
│       │                    └─ OpenClawClient        └─ ProfileWrite  │
│       │                           │                                   │
│       │                    ┌──────┴──────┐                            │
│       │                    │  transport   │                            │
│       │                    ├─────────────┤                            │
│       │                    │ responses_  │                            │
│       │                    │   http      │ POST /v1/responses        │
│       │                    ├─────────────┤                            │
│       │                    │ gateway_ws  │ WebSocket RPC              │
│       │                    │             │ agent → agent.wait →       │
│       │                    │             │ exec.approval.resolve      │
│       │                    └─────────────┘                            │
│       │                                                               │
│  ┌────┴──────────────────────┐                                       │
│  │ Trust Level 写入权限       │                                       │
│  ├───────────────────────────┤                                       │
│  │ RAW       → 仅存储        │                                       │
│  │ VALIDATED → 更新任务+计划  │                                       │
│  │ TRUSTED   → 写入画像+行为  │                                       │
│  └───────────────────────────┘                                       │
├──────────────────────────────────────────────────────────────────────┤
│  API Layer                                                           │
│  /executions/          → 用户安全接口 (需 get_current_user)          │
│  /admin/executions/    → 管理接口 (需 get_current_active_superuser)   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. 分阶段交付清单

### Phase 0 — 数据层、路由与信任引擎

| 文件 | 行数 | 职责 |
|------|------|------|
| `models/execution_intent.py` | 167 | ExecutionIntent 模型，11 种状态枚举，ExecutionMode(HUMAN/AGENT/HYBRID)，TrustLevel(RAW/VALIDATED/TRUSTED) |
| `models/execution_record.py` | 93 | ExecutionRecord 模型，1:1 关联 Intent，存储原始响应/解析输出/信任分级/质量分 |
| `core/execution_router.py` | 142 | 基于规则的路由：功能开关→任务类型排除→关键词拦截→副作用检测→AGENT/HYBRID/HUMAN |
| `core/execution_trust.py` | 219 | TrustEngine：空结果拒绝→内容安全→schema 验证→成功标准→质量打分→信任分级→自动晋升 |
| `alembic/.../oc001a...py` | 126 | 建表 migration：execution_intents + execution_records，tasks +execution_mode 列 |
| `alembic/.../oc002b...py` | 54 | 活跃执行防重唯一索引：(user_id, task_id) WHERE status IN (active) AND deleted_at IS NULL |

**新增配置** (settings.py，7→14 项)：
```python
OPENCLAW_ENABLED: bool = False          # 总开关
OPENCLAW_GATEWAY_URL: str = ""          # 网关地址
OPENCLAW_AUTH_TOKEN: str = ""           # 认证令牌
OPENCLAW_DEFAULT_AGENT_ID: str = ""     # 默认 agent
OPENCLAW_TRANSPORT: str = "responses_http"  # responses_http | gateway_ws
OPENCLAW_DEFAULT_TIMEOUT_SECONDS: int = 300
OPENCLAW_MAX_CONCURRENT_RUNS: int = 3
OPENCLAW_TRUST_AUTO_PROMOTE_MIN_HISTORY: int = 5
OPENCLAW_TRUST_AUTO_PROMOTE_SUCCESS_RATE: float = 0.85
# Gateway WS 专用
OPENCLAW_WS_URL: str = ""
OPENCLAW_WS_PROTOCOL_VERSION: int = 3
OPENCLAW_WS_WAIT_TIMEOUT_MS: int = 30000
OPENCLAW_WS_ALLOW_INSECURE_AUTH: bool = False
OPENCLAW_WS_DEVICE_TOKEN: str = ""
OPENCLAW_WS_CLIENT_ID: str = "sparkle-backend"
```

**新增事件** (event_types.py)：
```
EXECUTION_DELEGATED / STATUS_CHANGED / WAITING_APPROVAL / APPROVAL_DECISION
RESULT_INGESTED / HANDED_BACK / TEMPLATE_SELECTED / NODE_SELECTED / QUALITY_RECORDED
```

### Phase 1 — 适配层与执行服务

| 文件 | 行数 | 职责 |
|------|------|------|
| `adapters/openclaw/config.py` | 44 | OpenClawConfig dataclass，from_settings() 读取全部配置 |
| `adapters/openclaw/client.py` | 177 | 传输门面：HTTP 模式走 httpx POST /v1/responses，WS 模式委托 gateway_ws_client |
| `adapters/openclaw/intent_translator.py` | 131 | Intent → 请求体翻译：HTTP 用 model+input，WS 用 agentId+sessionKey+message |
| `adapters/openclaw/result_parser.py` | 121 | 响应解析：提取文本/工具调用/artifact，4 种信号检测审批需求 |
| `services/execution_service.py` | 1066 | 核心编排：classify → create_intent → dispatch → handoff，含模板/节点/质量策略集成 |

### Phase 2 — 摄取层与审批流

| 文件 | 行数 | 职责 |
|------|------|------|
| `services/execution_ingestor.py` | 723 | 唯一摄取入口。ingest→确认→拒绝三条路径，HYBRID 本地审批门，schema 前置校验 |
| `adapters/openclaw/gateway_ws_client.py` | 522 | Gateway WS 协议实现：connect.challenge→connect→agent→agent.wait→exec.approval.resolve |

**Gateway WS 生命周期**：
```
connect.challenge → connect (auth+scopes)
    → agent (提交执行) → 接收 runId
        → 事件流 (assistant/tool/lifecycle/exec.approval.requested)
            → agent.wait (等待完成)
                → 返回 build_result()
```

### Phase 3 — 画像反馈闭环

| 文件 | 行数 | 职责 |
|------|------|------|
| `services/execution_learning_service.py` | 400 | 三条学习信号：信任积累→Delegation Trust Building，退回→Delegation Aversion，时长→Execution Time Learning |

**闭环链路**：
```
TRUSTED + 成功 → 创建认知片段 → 计算 streak → 更新 BehaviorPattern → 写入推断偏好 → 触发 AdaptiveReplanner
退回/拒绝    → 创建认知片段 → 计算退回率 → 更新 Delegation Aversion → 下调委派偏好 → 触发 AdaptiveReplanner
时长偏差     → 取最近 5 次执行的中位比率 → 更新 ai_duration_multiplier → 触发 AdaptiveReplanner
```

**已修改的既有文件** (仅增量)：
- `services/profile_context_service.py` — PATTERN_POLICY_MAP 增加 delegation_aversion / delegation_trust_building / execution_time_learning 三项策略映射
- `orchestration/adaptive_replanner.py` — _map_pattern() 增加 Delegation Aversion→关闭自动委派，Delegation Trust→开启自动委派，Execution Time Learning→时长倍率校准

### Phase 4 — 模板、节点、质量闭环

| 文件 | 行数 | 职责 |
|------|------|------|
| `services/execution_template_service.py` | 349 | 5 个内置模板：web_research_brief / document_digest / shell_diagnostics / browser_form_prepare / cross_device_capture |
| `services/execution_node_service.py` | 152 | 节点发现与选择：list_nodes→select_node→build_policy_patch，优先精确匹配→命令匹配→环境匹配→平台匹配 |
| `services/execution_quality_service.py` | 320 | A/B 实验集成：balanced_control / evidence_strict / speed_optimized 三变体，每次终态记录 6 项指标 |
| `api/v1/executions.py` | 365 | 用户侧 REST API：classify、handoff、状态查询、确认/拒绝/取消/取回、模板推荐 |
| `api/v1/executions_admin.py` | 73 | 管理侧 API：health、nodes、quality/summary，需 superuser 权限 |

**5 个内置模板**：

| template_id | 模式 | 环境 | 节点需求 | 场景 |
|-------------|------|------|----------|------|
| web_research_brief | AGENT | BROWSER | 无 | 网页调研简报 |
| document_digest | AGENT | DOCUMENT | 无 | 文档摘要整理 |
| shell_diagnostics | AGENT | SHELL | system.run | 终端诊断执行 |
| browser_form_prepare | HYBRID | BROWSER | 无 | 浏览器表单协作（AI 准备草稿→用户确认→提交） |
| cross_device_capture | HYBRID | DOCUMENT | camera.capture | 跨设备节点协作 |

**安全边界** (Phase 4 修复后)：
- 用户路由 `/executions/`：仅安全操作，无节点直调
- 管理路由 `/admin/executions/`：health / nodes / quality/summary，需 superuser
- `invoke_node`：**不暴露在任何 API 上**，预留给未来带审计链路的管理员接口
- HYBRID intent：即使 OpenClaw 未返回 approval 信号，也强制 `WAITING_APPROVAL`

---

## 4. Intent 状态机

```
                    ┌──────────┐
                    │  DRAFT   │
                    └────┬─────┘
                         │ create_intent
                    ┌────▼─────┐
          ┌────────│   READY   │
          │        └────┬──────┘
          │             │ dispatch
          │        ┌────▼──────┐
          │        │ DISPATCHED │
          │        └────┬──────┘
          │             │
          │        ┌────▼──────┐
          │        │  RUNNING   │◄──────────────────┐
          │        └──┬───┬──┬──┘                    │
          │           │   │  │                       │
          │    ┌──────┘   │  └───────┐               │
          │    ▼          ▼          ▼               │
          │ ┌────────┐ ┌────────┐ ┌───────────────┐ │
          │ │SUCCEEDED│ │ FAILED │ │WAITING_APPROVAL│ │
          │ └─────────┘ └────────┘ └───────┬───────┘ │
          │                                     │     │
          │                              confirm│     │ resolve_approval
          │                                     ▼     │
          │                              ┌──────────┐ │
          │                              │ (继续运行)│─┘
          │                              └──────────┘
          │
          │  cancel / handback
          ▼
    ┌───────────┐
    │  CANCELED │   HANDED_BACK   TIMED_OUT   PARTIAL
    └───────────┘

    终态集合 = { SUCCEEDED, FAILED, CANCELED, HANDED_BACK, TIMED_OUT, PARTIAL }
    终态不可 handback / cancel
```

---

## 5. 信任引擎不变量

这是整个集成的核心安全约束，**不可违反**：

```
OpenClaw 结果 → ResultParser.parse() → TrustEngine.evaluate()
                                         │
                                         ├─ RAW       → 仅存储 ExecutionRecord，不写任务/画像
                                         ├─ VALIDATED → 可更新 Task.status + PlanExecutionRecord
                                         └─ TRUSTED   → 可写行为信号 + 推断偏好 + 触发 AdaptiveReplanner
```

**绕过防护**：
1. `ExecutionIngestor` 是唯一的摄取入口，所有三条路径 (ingest/confirm/reject) 都经过 TrustEngine
2. `ExecutionRecord.trust_level` 在写入后由 Ingestor 根据评估结果设定，服务层不覆盖
3. 用户确认 (`user_confirmed=True`) 会强制提升为 TRUSTED，但这是设计意图，不是绕过
4. 信任评估包含内容安全检查（敏感模式+注入检测）和 schema 验证

---

## 6. 学习信号回流

```
┌─────────────────────────────────────────────────────┐
│                   ExecutionIngestor                  │
│                                                      │
│  ingest()                                            │
│    └─ TRUSTED + 成功                                 │
│         └─ handle_trusted_execution()                │
│              ├─ 认知片段 (behavior_auto)             │
│              ├─ Delegation Trust Building 模式       │
│              ├─ Execution Time Learning 模式         │
│              ├─ update_inferred_preference()         │
│              └─ AdaptiveReplanner.on_pattern()       │
│                                                      │
│  reject_result()                                     │
│    └─ handle_handed_back()                           │
│         ├─ 认知片段 (delegation_takeback)            │
│         ├─ Delegation Aversion 模式                  │
│         ├─ update_inferred_preference() (下调)       │
│         └─ AdaptiveReplanner.on_pattern()            │
│                                                      │
│  cancel()                                            │
│    └─ record_outcome("canceled") → 质量指标          │
└─────────────────────────────────────────────────────┘

               │
               ▼
┌─────────────────────────────────────────────────────┐
│  ProfileContextService                               │
│    PATTERN_POLICY_MAP:                               │
│      delegation_aversion →                           │
│        execution.delegate.require_confirmation       │
│        task.execution.recommend_human_first          │
│      delegation_trust_building →                     │
│        execution.delegate.suggest_when_safe          │
│      execution_time_learning →                       │
│        task.execution.adjust_ai_duration             │
│                                                      │
│  AdaptiveReplanner                                   │
│    _map_pattern():                                   │
│      Delegation Aversion → auto_delegate=false       │
│                          → require_human_confirm=true│
│      Delegation Trust  → auto_delegate=true          │
│      Execution Time   → ai_duration_multiplier=calcd │
└─────────────────────────────────────────────────────┘
```

---

## 7. API 接口清单

### 用户侧 `/api/v1/executions/`

| 方法 | 路径 | 鉴权 | 用途 |
|------|------|------|------|
| GET | `/health` | — | 网关可达性检查 |
| POST | `/tasks/{id}/classify` | user | 预判任务执行模式 |
| POST | `/tasks/{id}/handoff` | user | 创建 intent + 分发执行 |
| GET | `/tasks/{id}/templates` | user | 推荐执行模板列表 |
| GET | `/tasks/{id}/intents` | user | 查询任务执行历史 |
| GET | `/{intent_id}` | user | 查询单个执行状态 |
| GET | `/{intent_id}/record` | user | 查询执行结果记录 |
| POST | `/{intent_id}/cancel` | user | 取消执行 |
| POST | `/{intent_id}/handback` | user | 取回任务（终态守卫） |
| POST | `/records/{id}/confirm` | user | 确认采用 AI 结果 |
| POST | `/records/{id}/reject` | user | 拒绝 AI 结果 |

### 管理侧 `/api/v1/admin/executions/`

| 方法 | 路径 | 鉴权 | 用途 |
|------|------|------|------|
| GET | `/health` | superuser | 系统健康+节点数+能力矩阵 |
| GET | `/nodes` | superuser | 列出可用节点 |
| GET | `/quality/summary` | superuser | A/B 实验汇总 |

### 不暴露的接口

| 路径 | 原因 |
|------|------|
| `POST /nodes/{id}/invoke` | 绕过 Ingestor 主链，预留给带审计的未来管理员接口 |

---

## 8. 数据库变更

### 新增表

**execution_intents**

| 列 | 类型 | 说明 |
|----|------|------|
| id | GUID PK | |
| user_id | GUID FK→users | |
| task_id | GUID FK→tasks | |
| plan_id | GUID FK→plans, nullable | |
| execution_mode | VARCHAR(20) | HUMAN / AGENT / HYBRID |
| executor | VARCHAR(20) | MANUAL / OPENCLAW |
| target_env | VARCHAR(20) | BROWSER / SHELL / API / DOCUMENT / HUMAN |
| goal | TEXT | 执行目标 |
| instructions | JSONB | 指令列表 |
| policy | JSONB | 执行策略 |
| success_criteria | JSONB | 成功标准 |
| result_contract | JSONB | 结果契约 |
| status | VARCHAR(25) | 11 种状态 |
| trust_level | VARCHAR(15) | RAW / VALIDATED / TRUSTED |
| external_run_id | VARCHAR(255), nullable | OpenClaw run ID |
| idempotency_key | VARCHAR(255) | 幂等键 |
| timeout_seconds | INTEGER | 超时 |
| dispatched_at | DATETIME, nullable | |
| completed_at | DATETIME, nullable | |
| error_category | VARCHAR(50), nullable | |
| error_message | TEXT, nullable | |
| created_at / updated_at / deleted_at | DATETIME | 软删除 |

**execution_records**

| 列 | 类型 | 说明 |
|----|------|------|
| id | GUID PK | |
| execution_intent_id | GUID FK→intents, UNIQUE | 1:1 |
| user_id / task_id | GUID FK | |
| executor_type | VARCHAR(20) | |
| external_run_id | VARCHAR(255), nullable | |
| raw_response | JSONB | 原始 OpenClaw 响应 |
| parsed_output | JSONB | 解析后结构化输出 |
| artifacts | JSONB | artifact 列表 |
| trust_level | VARCHAR(15) | |
| quality_score | FLOAT, nullable | |
| validation_passed / validation_total | INTEGER, nullable | |
| duration_ms | INTEGER, nullable | |
| token_usage | JSONB, nullable | |
| tool_calls_count | INTEGER | |
| approval_requested | INTEGER | |
| execution_started_at / execution_completed_at | DATETIME, nullable | |
| error_category / error_message | nullable | |

### 已修改表

- **tasks** — +1 nullable 列 `execution_mode VARCHAR(20)`

### 索引

- `uq_execution_intents_active_task` — UNIQUE (user_id, task_id) WHERE deleted_at IS NULL AND status IN (active statuses)

---

## 9. Mobile 端交付

| 文件 | 说明 |
|------|------|
| `models/execution_intent_model.dart` | ExecutionIntentModel + ExecutionIntentStatus 枚举 |
| `models/execution_record_model.dart` | ExecutionRecordModel |
| `models/execution_template_model.dart` | ExecutionTemplateModel |
| `repositories/task_repository.dart` | +handoff / execution status / confirm / reject / templates 接口 |
| `providers/task_provider.dart` | +执行状态缓存 + handoff 流程 + 模板选择 |
| `screens/task_execution_screen.dart` | "交给 AI 执行"按钮 + 模板选择 + 状态卡 + 确认/拒绝/取回按钮 + 终态停轮询 |
| `core/network/api_endpoints.dart` | +execution 端点常量 |

---

## 10. 测试覆盖

37 个测试，全部通过。

### 按文件分布

| 测试文件 | 数量 | 覆盖范围 |
|---------|------|---------|
| test_openclaw_phase0.py | 8 | 路由(关闭/学习任务/AGENT/HYBRID)、信任引擎(空结果/结构化输出/敏感内容/token误报) |
| test_openclaw_phase1.py | 4 | 翻译器构建、解析器解析、handoff+任务完成、handback+状态还原 |
| test_openclaw_phase2.py | 7 | 审批检测、WAITING_APPROVAL流、confirm→TRUSTED、reject→HANDED_BACK+任务回滚、防重唯一索引、schema校验、WS审批解析、WS取消 |
| test_openclaw_gateway_ws.py | 4 | WS执行→审批返回、WS执行→输出收集+等待完成、WS审批解析→恢复运行、WS list_nodes+invoke |
| test_openclaw_phase3.py | 4 | 信任积累→模式+偏好、退回→厌恶模式、ProfileContext合并偏好、CognitivePatternTrigger映射 |
| test_openclaw_phase4.py | 7 | 模板匹配、模板+策略+节点策略应用、HYBRID强制本地审批、质量指标记录、缺节点硬失败、终态handback守卫 |
| test_openclaw_admin_api.py | 3 | 用户路由不含quality/invoke、admin需superuser、admin summary可用 |

### 关键负向测试

- 缺节点时创建 intent 抛出 `ValueError("requires a node with ... capability")`
- 终态 intent 不可 handback：`ValueError("already terminal")`
- schema 失配结果不误判为 partial
- 用户路由 `/executions/quality/summary` 和 `/executions/nodes/{id}/invoke` 返回 404
- 非 superuser 访问 admin 路由返回 403

---

## 11. 既有文件变更汇总

所有变更均为**增量添加**，不修改既有行为：

| 文件 | 变更类型 | 变更内容 |
|------|---------|---------|
| `models/task.py` | +1 nullable 字段 | `execution_mode = Column(String(20), nullable=True)` |
| `config/settings.py` | +14 配置项 | OPENCLAW_* 系列变量，全部带默认值 |
| `core/event_types.py` | +9 事件常量 | EXECUTION_* 系列事件 |
| `api/v1/router.py` | +2 路由注册 | executions + executions_admin |
| `services/profile_context_service.py` | +3 策略映射 | PATTERN_POLICY_MAP 增加 delegation 相关条目 |
| `orchestration/adaptive_replanner.py` | +3 模式匹配 | _map_pattern() 增加 delegation aversion/trust/time learning |

---

## 12. 配置与部署

### 启用步骤

```bash
# 1. 环境变量
OPENCLAW_ENABLED=true
OPENCLAW_GATEWAY_URL=https://your-openclaw-instance.local
OPENCLAW_AUTH_TOKEN=your-token
OPENCLAW_DEFAULT_AGENT_ID=your-agent-id
OPENCLAW_TRANSPORT=gateway_ws  # 或 responses_http

# Gateway WS 模式额外配置
OPENCLAW_WS_URL=wss://your-openclaw-instance.local
OPENCLAW_WS_ALLOW_INSECURE_AUTH=true  # 仅开发环境
# 或
OPENCLAW_WS_DEVICE_TOKEN=your-paired-device-token  # 生产环境

# 2. 数据库迁移
cd backend && alembic upgrade head

# 3. 验证
curl http://localhost:8000/api/v1/admin/executions/health  # 需 admin 认证
```

### 部署约束

- Gateway WS 模式需要显式配置 `OPENCLAW_TRANSPORT=gateway_ws`
- 可信环境下可用 `OPENCLAW_WS_ALLOW_INSECURE_AUTH=true`，生产环境必须使用 `OPENCLAW_WS_DEVICE_TOKEN`
- `OPENCLAW_ENABLED=false` 时所有 execution API 返回 503 或降级为 HUMAN

---

## 13. 已知限制与后续方向

| 项目 | 当前状态 | 后续 |
|------|---------|------|
| 节点直调审计 | 不暴露，service 层能力保留 | 实现带 ExecutionIntent 审计链的 admin 接口 |
| 真实节点联调 | 代码闭环，未接线上 | 接入 OpenClaw 网关做端到端验证 |
| 模板扩展 | 5 个内置模板 | 开放用户自定义模板 |
| 质量实验 | 三变体固定分配 | 接入 experiment service 做动态流量分配和统计显著性检验 |
| 执行结果 UI 展示 | 状态卡 + 确认/拒绝 | 展示 parsed_output 富文本和 artifact 预览 |

---

## 14. 文件清单

### 后端新增 (20 个文件)

```
app/models/execution_intent.py                          167
app/models/execution_record.py                           93
app/core/execution_router.py                            142
app/core/execution_trust.py                             219
app/adapters/openclaw/__init__.py                        25
app/adapters/openclaw/config.py                          44
app/adapters/openclaw/client.py                         177
app/adapters/openclaw/intent_translator.py              131
app/adapters/openclaw/result_parser.py                  121
app/adapters/openclaw/gateway_ws_client.py              522
app/services/execution_service.py                      1066
app/services/execution_ingestor.py                      723
app/services/execution_learning_service.py              400
app/services/execution_template_service.py              349
app/services/execution_node_service.py                  152
app/services/execution_quality_service.py               320
app/api/v1/executions.py                                365
app/api/v1/executions_admin.py                           73
alembic/.../oc001a2b3c4d5_*.py                          126
alembic/.../oc002b3c4d5e6_*.py                           54
                                                     ──────
                                          合计 ~5,159 行
```

### 后端测试 (7 个文件)

```
tests/unit/test_openclaw_phase0.py                      115
tests/unit/test_openclaw_phase1.py                      239
tests/unit/test_openclaw_phase2.py                      623
tests/unit/test_openclaw_gateway_ws.py                  244
tests/unit/test_openclaw_phase3.py                      266
tests/unit/test_openclaw_phase4.py                      381
tests/unit/test_openclaw_admin_api.py                   127
                                                     ──────
                                          合计 ~1,995 行, 37 tests
```

### Mobile 新增/修改 (7 个文件)

```
lib/features/task/data/models/execution_intent_model.dart
lib/features/task/data/models/execution_record_model.dart
lib/features/task/data/models/execution_template_model.dart
lib/features/task/data/repositories/task_repository.dart       (修改)
lib/features/task/presentation/providers/task_provider.dart    (修改)
lib/features/task/presentation/screens/task_execution_screen.dart (修改)
lib/core/network/api_endpoints.dart                            (修改)
```

### 后端既有文件增量修改 (6 个文件)

```
app/models/task.py              +1 nullable 列
app/config/settings.py          +14 配置项
app/core/event_types.py         +9 事件常量
app/api/v1/router.py            +2 路由注册
app/services/profile_context_service.py  +3 策略映射
app/orchestration/adaptive_replanner.py  +3 模式匹配
```

---

**文档版本**: 1.0
**生成日期**: 2026-03-28
**验收状态**: Phase 0–4 全量通过 (37 tests)
