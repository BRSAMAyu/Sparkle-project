# OpenClaw × Sparkle 连接指南

> **目标读者**：负责搭建或维护 OpenClaw 实例的工程师（"OpenClaw Agent"）
> **版本**：Sparkle MVP v0.3.0 / OpenClaw 集成 Phase 0–6
> **日期**：2026-03-28

---

## 一、概念速览

Sparkle 是移动端 AI 学习助手（Flutter App + Python 后端）。OpenClaw 是一个 **AI 执行网关**，负责真正跑任务——网页调研、文档整理、自动化操作等。两者的关系：

```
Sparkle App  ──[委派任务]──▶  Sparkle 后端  ──[HTTP/WS]──▶  OpenClaw 网关
                                                                    │
                                                              执行真实操作
                                                                    │
                              结果 + 状态 ◀──────────────────────────┘
```

Sparkle 后端是唯一与 OpenClaw 通信的一方。手机 App 不直接连接 OpenClaw；App 通过 Sparkle 后端感知连接状态。

---

## 二、OpenClaw 侧需要实现的接口

Sparkle 只调用两个 HTTP 端点。OpenClaw 只需要实现这两个接口即可接入。

### 2.1 健康检查

```
GET /health
```

**认证**：可选，Sparkle 会带 `Authorization: Bearer {token}`（如已配置）

**成功响应** `200 OK`：
```json
{
  "status": "ok",
  "node_count": 2,
  "connected_nodes": 2,
  "capabilities": ["web_search", "code_execution"],
  "supports_nodes": true,
  "supports_templates": true,
  "supports_quality_loop": false
}
```

> 字段均为可选；Sparkle 会做安全读取，缺字段不会出错。
> `node_count` / `connected_nodes` 任一存在即可展示节点数。

---

### 2.2 任务执行

```
POST /v1/responses
Content-Type: application/json
Authorization: Bearer {token}
```

**请求体**：
```json
{
  "model": "openclaw/main",
  "input": "## Task Goal\n帮我调研竞品 X 的定价策略\n\n## Constraints\n- 只看官网和公开资料\n\n## Expected Output\nType: report",
  "instructions": "You are executing a delegated task from Sparkle AI Learning Assistant.\nTarget environment: web\nTime limit: 300 seconds\n...",
  "stream": false,
  "user": "sparkle:main:{user_uuid}:{task_uuid}"
}
```

字段说明：

| 字段 | 说明 |
|------|------|
| `model` | 固定格式：`openclaw/{agent_id}`，或默认时为 `openclaw` |
| `input` | 任务目标 + 约束 + 期望输出（Markdown 结构化文本） |
| `instructions` | 系统级策略：执行环境、超时、允许工具、安全约束等 |
| `stream` | 始终为 `false`（Sparkle 不处理流式响应） |
| `user` | 会话键，格式固定：`sparkle:{agent_id}:{user_id}:{task_id}` |

**成功响应** `200 OK`：

```json
{
  "status": "completed",
  "output": [
    {
      "type": "message",
      "content": [
        {
          "type": "output_text",
          "text": "调研结果如下：..."
        }
      ]
    }
  ],
  "usage": {
    "input_tokens": 500,
    "output_tokens": 1200
  }
}
```

或者最简形式（Sparkle 也能处理）：
```json
{
  "status": "completed",
  "output": "调研结果如下：..."
}
```

**需要人工审批时**（可选支持）：
```json
{
  "status": "requires_action",
  "approval_required": true,
  "approval": {
    "action_description": "即将提交表单，请确认",
    "risk_level": "medium"
  },
  "output": []
}
```

> `status` 为以下任意值时 Sparkle 会识别为等待审批：
> `requires_action` / `waiting_approval` / `approval_required`
> 或者响应体中 `approval_required: true`。

**Artifacts 格式**（如有文件/图片输出）：
```json
{
  "status": "completed",
  "output": [
    {
      "type": "file",
      "file_id": "file-abc123",
      "filename": "report.pdf",
      "mime_type": "application/pdf",
      "url": "https://..."
    },
    {
      "type": "image",
      "image_url": "https://...",
      "filename": "screenshot.png"
    }
  ]
}
```

---

## 三、Sparkle 后端配置（环境变量）

在 Sparkle 后端的 `.env` 中添加以下变量：

### 最简配置（HTTP 模式）

```env
# 开启集成
OPENCLAW_ENABLED=true

# OpenClaw 网关地址（末尾不加斜杠）
OPENCLAW_GATEWAY_URL=http://192.168.1.100:8080

# 认证 Token（OpenClaw 侧颁发）
OPENCLAW_AUTH_TOKEN=your-secret-token-here

# 默认 Agent ID（OpenClaw 侧定义）
OPENCLAW_DEFAULT_AGENT_ID=main

# 传输模式：HTTP
OPENCLAW_TRANSPORT=responses_http
```

### WebSocket 模式（可选）

```env
OPENCLAW_TRANSPORT=gateway_ws

# WS 地址（留空时自动从 gateway_url 转换 http→ws）
OPENCLAW_WS_URL=ws://192.168.1.100:8080

# WS 设备令牌（OpenClaw 侧颁发）
OPENCLAW_WS_DEVICE_TOKEN=device-token-here

# 无设备令牌时允许不安全认证（开发调试用）
OPENCLAW_WS_ALLOW_INSECURE_AUTH=false

# 协议版本（默认 3，不要动）
OPENCLAW_WS_PROTOCOL_VERSION=3
```

### 调优参数（可选，按需修改）

```env
# 单次执行超时（秒），默认 5 分钟
OPENCLAW_DEFAULT_TIMEOUT_SECONDS=300

# 最大并发执行数，默认 3
OPENCLAW_MAX_CONCURRENT_RUNS=3

# 信任自动提级：最少历史次数（达到后才评估）
OPENCLAW_TRUST_AUTO_PROMOTE_MIN_HISTORY=5

# 信任自动提级：成功率阈值（达到后从 VALIDATED 晋升到 TRUSTED）
OPENCLAW_TRUST_AUTO_PROMOTE_SUCCESS_RATE=0.85
```

---

## 四、手机 App 端操作步骤

App 通过 Sparkle 后端感知 OpenClaw 状态，无法直连。但 App 里有专门的设置页做"体感测试"。

1. 打开 Sparkle App → 设置 → AI 执行引擎
2. 填入 **网关地址**（与后端 `OPENCLAW_GATEWAY_URL` 保持一致）
3. 填入 **Auth Token**（与后端 `OPENCLAW_AUTH_TOKEN` 保持一致）
4. 选择传输协议：`HTTP（responses_http）` 或 `WebSocket（gateway_ws）`
5. 点击**测试连接**

   - 绿色 = 成功，显示延迟 + 节点数 + 能力列表
   - 红色 = 失败，检查地址和 token

6. 测试通过后点**保存**，App 会开始 30 秒周期健康检查

> 注意：App 设置的连接信息仅用于 App 前端展示连接状态。**真正发任务的是 Sparkle 后端**，需确保后端 `.env` 也配好了。

---

## 五、连接验证流程

完成配置后，按以下步骤端到端验证：

### Step 1：验证 OpenClaw 健康接口

```bash
curl http://<openclaw_host>:<port>/health \
  -H "Authorization: Bearer <your-token>"
```

期望：`{"status": "ok", ...}`

### Step 2：验证 Sparkle 后端能探通 OpenClaw

```bash
curl http://localhost:<sparkle_backend_port>/api/v1/executions/connection/status
```

期望响应：
```json
{
  "openclaw_enabled": true,
  "reachable": true,
  "latency_ms": 42,
  "connected_nodes": 2,
  "capabilities": ["web_search"],
  "supports_nodes": true,
  "supports_templates": true
}
```

如果 `reachable: false`，检查：
- `OPENCLAW_GATEWAY_URL` 是否正确
- `OPENCLAW_AUTH_TOKEN` 是否与 OpenClaw 侧一致
- 网络连通性（防火墙/端口）

### Step 3：发送一次测试任务

在 Sparkle App 中创建一个简单任务，执行时选择"交给 AI 执行"。如果 OpenClaw 收到请求并返回结果，说明全链路通畅。

---

## 六、降级与恢复机制

Sparkle 内置了安全保护，了解这个机制可以避免困惑：

| 事件 | Sparkle 行为 |
|------|-------------|
| 连续 3 次执行失败 | 自动将该用户切换为人工执行模式（降级），阻止新的 AI 委派 |
| 降级持续时间 | 30 分钟后自动过期，或用户手动成功执行一次后清除 |
| 人工确认/取消/取回任务 | 立即清除降级状态 |

降级期间，App 端会在执行按钮旁显示提示。Admin 可通过以下接口查看当前降级用户数：

```bash
curl http://localhost:<port>/api/v1/admin/executions/health
# 返回：{"degraded_user_count": 1, "degradation_threshold": 3, ...}
```

---

## 七、常见问题

**Q：OpenClaw 返回什么格式都行吗？**
A：Sparkle 会尝试把 `output` 里的 `output_text` 拼接成文本，然后尝试 JSON 解析。只要 `status: completed` + 有 `output`，不管格式简单还是复杂都能处理。

**Q：如果任务耗时超过默认 5 分钟会怎样？**
A：Sparkle 抛 `OpenClawTimeout`，任务标记为 `FAILED`，用户收到失败通知。可以通过 `OPENCLAW_DEFAULT_TIMEOUT_SECONDS` 调大。

**Q：同一任务多次委派会重复执行吗？**
A：Sparkle 发送时带有 `user` 字段（包含 `task_id`）。OpenClaw 可以用这个做幂等键。Sparkle 后端侧也通过 `idempotency_key` 字段（WS 模式）防止重复。

**Q：OpenClaw 需要主动回调 Sparkle 吗？**
A：HTTP 模式下不需要，Sparkle 同步等待响应。WS 模式下通过 WebSocket 事件流推送进度。

**Q：如何支持多个节点/Agent？**
A：在 `/health` 响应里返回 `node_count > 1`，并设 `supports_nodes: true`。Sparkle 会在模板选择时允许用户指定 `preferred_node_id`，并在请求的 `instructions` 里带上。

---

## 八、安全注意事项

- `OPENCLAW_AUTH_TOKEN` 存放在 `.env` 文件，**不要提交到 Git**
- 生产环境建议通过 HTTPS/WSS 连接，不要用明文 HTTP
- OpenClaw 侧的 `ws_allow_insecure_auth` 仅用于本地开发调试，生产必须关闭
- Sparkle 的 `instructions` 字段会注入安全约束（禁止发消息、禁止购买、CAPTCHA 拦截等），OpenClaw 应遵守这些约束

---

*本文档由 Claude Code 根据 Sparkle 代码库实际实现生成，与代码保持同步。如接口有变更，以 `backend/app/adapters/openclaw/` 目录下的实现为准。*
