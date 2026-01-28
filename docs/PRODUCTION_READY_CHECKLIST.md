# 🌠 Sparkle (星火) 项目全技术栈生产级验收手册 (V2.0)

## 📋 文档说明
- **目标**：验证系统在生产环境的稳定性、安全性及业务闭环能力。
- **覆盖范围**：Go Gateway, Python AI Engine, Flutter App, DevOps Infrastructure.
- **状态标记**：`[ ] 待验证` | `[P] 部分通过` | `[OK] 已通过`

---

## 🏗️ 模块一：基础设施与云原生基建 (Infrastructure & Cloud Native)
*验证容器化编排、可观测性及持久化层。*

| 编号 | 验收项 | 核心技术细节/标准 | 验证方法 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
| 1.1 | **向量数据库 (pgvector)** | PostgreSQL 16 容器运行正常，`vector` 扩展已加载，具备高效检索能力。 | `SELECT * FROM pg_extension WHERE extname = 'vector';` | [ ] |
| 1.2 | **Redis Stack 状态** | 使用 `redis-stack-server` 镜像，持久化配置符合 AOF 模式，内存限制为 4G。 | 检查 `docker-compose.yml` 资源限制与 `redis.conf`。 | [ ] |
| 1.3 | **对象存储 (MinIO)** | `sparkle-files` 存储桶自动创建，AccessKey 权限闭环，外部访问地址正确。 | 访问 `9001` 控制台查看存储桶及 `Policy` 配置。 | [ ] |
| 1.4 | **全链路追踪 (Tempo/Loki)** | gRPC 与 HTTP 请求的 TraceID 贯通，日志已采集至 Grafana。 | 在 Grafana 观察 `TraceID` 是否能跨越 Gateway 与 AI Engine。 | [ ] |

---

## 🛠️ 模块二：Go Gateway 接入层 (Go Microservices)
*验证网关的高并发处理、数据库安全及文件生命周期。*

| 编号 | 验收项 | 核心技术细节/标准 | 验证方法 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
| 2.1 | **gRPC 客户端连接池** | `AGENT_ADDRESS` 配置正确，具备 KeepAlive 机制（60s）防止长连接断开。 | 观察网关启动日志，确认 `Agent Connection Established`。 | [ ] |
| 2.2 | **sqlc 类型安全审计** | 所有 DB 操作均通过生成的 `internal/db` 执行，无原生拼接 SQL，防止注入。 | 审计代码中 `repository` 模式的实现。 | [ ] |
| 2.3 | **文件 GC 机制** | `FILE_GC_INTERVAL_MINUTES` 生效，过期（24h+）未引用文件自动清理。 | 检查 `worker/file_gc.go` 逻辑并查看相关定时任务日志。 | [ ] |
| 2.4 | **WebSocket 心跳** | 支持 `web_socket_channel` 长连接，断网 30s 内能检测并触发重连。 | 模拟 App 切断网络，观察 Gateway 的连接断开信号。 | [ ] |

---

## 🧠 模块三：Python AI Engine 与 RAG (AI Engine & Workers)
*验证多模型调度、异步任务队列及向量检索逻辑。*

| 编号 | 验收项 | 核心技术细节/标准 | 验证方法 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
| 3.1 | **多模型 Provider 冗余** | 支持 Xiaomi, DeepSeek, Zhipu。主模型故障时能手动/自动降级。 | 修改 `.env` 切换 `LLM_PROVIDER`，验证接口响应。 | [ ] |
| 3.2 | **RAG 向量检索精度** | 向量嵌入模型（Embedding）与检索算法匹配，支持 pgvector HNSW 索引。 | 调用知识点检索接口，检查返回的 `score` 相似度排名。 | [ ] |
| 3.3 | **Celery 优先级队列** | `high_priority` (即时 AI)、`low_priority` (总结生成) 队列互不干扰。 | 同时发起大量任务，检查 `celery_worker` 的并发处理能力。 | [ ] |
| 3.4 | **STT 语音处理** | 讯飞 (Xunfei) IAT 接口连通，支持 60s 内音频流式识别。 | 发送一段语音文件，验证转写文字的准确性。 | [ ] |

---

## 📱 模块四：Flutter 移动端与 Luminous 视觉 (Mobile App)
*验证 Shader 性能、离线存储与同步一致性。*

| 编号 | 验收项 | 核心技术细节/标准 | 验证方法 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
| 4.1 | **Luminous Shader 性能** | `galaxy_field.frag` 在中低端机型帧率稳定在 50fps+。 | 开启 Flutter Performance Overlay 观察 `GPU` 渲染时间。 | [ ] |
| 4.2 | **离线持久化 (Hive/Isar)** | 知识节点存储在 `Hive` 中，即使断网重启 App 也能正常浏览 Galaxy。 | 开启飞行模式启动 App，检查主页 Galaxy 是否加载。 | [ ] |
| 4.3 | **SyncCognitiveRepository** | 后台同步逻辑闭环，支持 `Isar` 结构的增量上传。 | 离线修改任务，连网后观察 `Sync` 任务是否自动触发。 | [ ] |
| 4.4 | **Adaptive Visuals** | `PerformanceService` 根据设备电量/负载自动降低 Shader 复杂度。 | 模拟低电量模式，观察 `SparkleMaterial` 视觉效果是否简化。 | [ ] |

---

## 🔐 模块五：安全、限流与合规 (Security & Ops)
*验证生产环境的防御能力与日志审计。*

| 编号 | 验收项 | 核心技术细节/标准 | 验证方法 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
| 5.1 | **JWT 安全载荷** | Token 包含 `uid` 和 `exp`，且 `JWT_SECRET` 长度符合 256 位加密标准。 | 使用工具解析 Token，检查是否泄露非必要字段。 | [ ] |
| 5.2 | **文件上传安全** | `FILE_MAX_UPLOAD_SIZE` 限制 (50MB)，且通过 Magic Byte 校验文件头。 | 尝试上传过大文件或篡改后缀名的恶意文件。 | [ ] |
| 5.3 | **API 速率限制** | Gateway 针对 `/api/v1/ai` 接口开启每分钟 60 次的滑动窗口限流。 | 使用压测工具模拟高频请求，检查 429 返回。 | [ ] |
| 5.4 | **Sentry 错误收集** | 生产环境混淆后的堆栈能通过 `sentry_dart_plugin` 自动还原。 | 手动触发异常，检查 Sentry 是否显示准确的源码行数。 | [ ] |

---

## 🎯 模块六：业务全链路闭环 (Business End-to-End)
*验证从用户交互到 AI 推理的最终业务流。*

| 编号 | 验收项 | 验收流程描述 | 状态 |
| :--- | :--- | :--- | :--- |
| 6.1 | **AI 深度学习流** | 语音提问 -> Gateway -> AI Agent (DeepSeek Reasoner) -> Shimmer 效果 -> 存入 Galaxy。 | [ ] |
| 6.2 | **Focus-to-Prism 联动** | 开启专注模式 -> 产生专注数据 -> 结束时自动触发 Prism 反思总结。 | [ ] |
| 6.3 | **OmniBar 智能搜索** | 输入模糊词 -> RAG 检索 -> 结果在 Galaxy 中高亮显示。 | [ ] |

---

## 📅 上线前强制核对清单 (Final Kill-Switch)
- [ ] **环境变量审计**：确认 `config_production.py` 禁用所有 Debug 开关。
- [ ] **SSL 终端**：确认支持 WebSocket Over WSS。
- [ ] **数据库权限**：后端服务的 DB 用户禁止拥有 `SUPERUSER` 权限。
- [ ] **模型额度**：确认各 AI 供应商 API 账户余额充足。