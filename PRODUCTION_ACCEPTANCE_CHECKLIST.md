# Sparkle（星火）生产级验收文档

> **项目定位**：大学生AI智能学习助手 - 基于认知画像的自适应学习系统
> **验收目标**：通过本验收文档所有事项 = 项目可直接部署到生产服务器
> **版本**：MVP v0.3.0
> **生成日期**：2026-01-28

---

## 📋 验收概览

本文档按**技术链路**和**业务模块**划分，支持**并行测试验收**。每个验收项包含：
- **验收标准**：明确的通过条件
- **验收方法**：测试步骤或命令
- **依赖项**：前置条件
- **负责人**：建议的责任方（后端/前端/DevOps）

### 验收流程建议

```
阶段1: 基础设施验收（必须最先完成）
    ↓
阶段2: 核心服务验收（API、数据库、中间件）
    ↓
阶段3: 业务功能验收（可并行进行）
    ↓
阶段4: 集成测试验收（跨模块）
    ↓
阶段5: 性能安全验收（非阻塞）
    ↓
阶段6: 部署上线验收（最后执行）
```

---

## 🔴 第一阶段：基础设施验收（P0 - 必须全部通过）

### 1.1 数据库系统验收

#### 1.1.1 PostgreSQL 主数据库

**验收标准**：
- [ ] PostgreSQL 16 + pgvector 扩展正常运行
- [ ] 数据库连接池配置正确（最大连接数 ≥ 50）
- [ ] 所有59个Alembic迁移成功应用
- [ ] 数据库性能参数调优（shared_buffers, work_mem等）
- [ ] 备份恢复机制可用

**验收方法**：
```bash
# 1. 检查数据库运行状态
docker exec sparkle_db pg_isready -U postgres

# 2. 验证pgvector扩展
docker exec sparkle_db psql -U postgres -d sparkle -c "SELECT extversion FROM pg_extension WHERE extname='vector';"

# 3. 检查迁移状态（应显示1个head）
cd backend && alembic heads

# 4. 验证当前版本
cd backend && alembic current

# 5. 检查关键表是否存在（示例）
docker exec sparkle_db psql -U postgres -d sparkle -c "\dt" | grep -E "(users|tasks|plans|chat_messages|knowledge_nodes)"

# 6. 检查向量索引
docker exec sparkle_db psql -U postgres -d sparkle -c "SELECT indexname FROM pg_indexes WHERE indexname LIKE '%hnsw%';"
```

**依赖项**：
- Docker环境已启动
- `.env`文件配置正确

**负责人**：后端DevOps

---

#### 1.1.2 数据库Schema验证

**验收标准**：
- [ ] Go Gateway生成的schema.sql与实际数据库一致
- [ ] 所有关键表的主键、外键、索引正确
- [ ] 向量字段配置正确（1024维）
- [ ] 触发器和约束正常工作

**验收方法**：
```bash
# 1. 执行Schema同步检查
make sync-db

# 2. 验证schema.sql文件存在且非空
ls -lh backend/gateway/internal/db/schema.sql

# 3. 检查Go代码生成完整性
ls -lh backend/gateway/internal/db/*.go | grep sqlc

# 4. 手动验证关键表结构
docker exec sparkle_db psql -U postgres -d sparkle -c "\d users"
docker exec sparkle_db psql -U postgres -d sparkle -c "\d knowledge_nodes"
docker exec sparkle_db psql -U postgres -d sparkle -c "\d tasks"
```

**依赖项**：
- 1.1.1 PostgreSQL主数据库验收通过

**负责人**：后端开发

---

### 1.2 缓存与消息队列验收

#### 1.2.1 Redis Stack

**验收标准**：
- [ ] Redis Stack服务正常运行
- [ ] RedisInsight可视化管理界面可访问
- [ ] 密码认证配置正确
- [ ] 内存使用合理（< 80%）
- [ ] 持久化配置正确（RDB/AOF）

**验收方法**：
```bash
# 1. 检查Redis运行状态
docker exec sparkle_redis redis-cli -a change-me ping

# 2. 检查Redis版本和Stack功能
docker exec sparkle_redis redis-cli -a change-me INFO server | grep redis_version

# 3. 验证内存使用
docker exec sparkle_redis redis-cli -a change-me INFO memory | grep used_memory_human

# 4. 测试基本读写
docker exec sparkle_redis redis-cli -a change-me SET test_key "test_value"
docker exec sparkle_redis redis-cli -a change-me GET test_key

# 5. 检查持久化配置
docker exec sparkle_redis redis-cli -a change-me CONFIG GET save
docker exec sparkle_redis redis-cli -a change-me CONFIG GET appendonly
```

**依赖项**：
- Docker环境已启动
- `.env`中REDIS_PASSWORD已配置

**负责人**：后端DevOps

---

#### 1.2.2 Celery任务队列

**验收标准**：
- [ ] Celery Worker正常运行
- [ ] Celery Beat定时任务调度器运行
- [ ] 任务队列定义正确（high_priority, default, low_priority）
- [ ] Flower监控界面可访问（如启用）

**验收方法**：
```bash
# 1. 启动Celery服务
make celery-up

# 2. 检查服务状态
make celery-status

# 3. 查看Worker日志（应显示ready且无错误）
make celery-logs-worker

# 4. 查看Beat日志
make celery-logs-beat

# 5. 访问Flower界面（如FLOWER_ENABLE=1）
open http://localhost:5555

# 6. 测试任务提交（需要后端API运行）
# 使用Postman或curl发送异步任务请求
```

**依赖项**：
- 1.1 PostgreSQL验收通过
- 1.2.1 Redis验收通过

**负责人**：后端开发

---

### 1.3 对象存储验收

#### 1.3.1 MinIO对象存储

**验收标准**：
- [ ] MinIO服务正常运行
- [ ] 默认bucket（sparkle-files）已创建
- [ ] 控制台可访问（http://localhost:9001）
- [ ] 文件上传下载功能正常

**验收方法**：
```bash
# 1. 检查MinIO运行状态
curl -I http://localhost:9000/minio/health/live

# 2. 验证默认bucket存在
docker exec sparkle_minio mc alias set local http://localhost:9000 minioadmin minioadmin
docker exec sparkle_minio mc ls local/

# 3. 测试文件上传
docker exec sparkle_minio sh -c 'echo "test" > /tmp/test.txt && mc cp /tmp/test.txt local/sparkle-files/'

# 4. 测试文件下载
docker exec sparkle_minio mc cp local/sparkle-files/test.txt /tmp/downloaded.txt
```

**依赖项**：
- Docker环境已启动

**负责人**：后端DevOps

---

### 1.4 可观测性系统验收（可选但推荐）

#### 1.4.1 Prometheus监控

**验收标准**：
- [ ] Prometheus服务运行
- [ ] 采集目标配置正确
- [ ] 数据存储正常

**验收方法**：
```bash
# 1. 检查Prometheus状态
curl http://localhost:9090/-/healthy

# 2. 访问Prometheus UI
open http://localhost:9090

# 3. 检查采集目标
curl http://localhost:9090/api/v1/targets | jq
```

**负责人**：DevOps

---

#### 1.4.2 Grafana可视化

**验收标准**：
- [ ] Grafana服务运行
- [ ] 数据源配置正确
- [ ] 关键仪表板已创建

**验收方法**：
```bash
# 1. 访问Grafana
open http://localhost:3000

# 2. 登录（默认admin/admin）
# 3. 验证数据源连接
# 4. 检查仪表板
```

**负责人**：DevOps

---

## 🟡 第二阶段：核心服务验收（P0 - 必须全部通过）

### 2.1 Python后端服务验收

#### 2.1.1 gRPC服务（sparkle_agent）

**验收标准**：
- [ ] gRPC服务在50051端口正常监听
- [ ] 健康检查端点响应正常
- [ ] 所有proto定义的服务已实现
- [ ] 与数据库连接正常

**验收方法**：
```bash
# 1. 启动gRPC服务
make grpc-server

# 2. 检查端口监听
lsof -i :50051

# 3. 使用grpcurl列出服务
grpcurl -plaintext localhost:50051 list

# 4. 验证agent.AgentService服务存在
grpcurl -plaintext localhost:50051 list agent.AgentService

# 5. 检查服务日志（应无ERROR）
docker logs sparkle_agent --tail 50
```

**依赖项**：
- 1.1 PostgreSQL验收通过
- 1.2 Redis验收通过

**负责人**：后端开发

---

#### 2.1.2 FastAPI服务（sparkle_api）

**验收标准**：
- [ ] FastAPI服务在8000端口运行
- [ ] API文档可访问（/docs）
- [ ] 健康检查端点响应正常
- [ ] CORS配置正确

**验收方法**：
```bash
# 1. 检查服务健康
curl http://localhost:8000/health

# 2. 访问API文档
open http://localhost:8000/docs

# 3. 测试CORS（从前端域名）
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS http://localhost:8000/api/v1/chat

# 4. 检查服务日志
docker logs sparkle_api --tail 50
```

**依赖项**：
- 1.1 PostgreSQL验收通过
- 1.2 Redis验收通过

**负责人**：后端开发

---

#### 2.1.3 Python代码质量验收

**验收标准**：
- [ ] 所有Python文件通过Ruff lint检查
- [ ] 核心模块通过MyPy类型检查
- [ ] 单元测试覆盖率 ≥ 60%
- [ ] 无关键安全漏洞

**验收方法**：
```bash
# 1. Ruff代码检查
cd backend && ruff check app --output-format=github

# 2. MyPy类型检查
cd backend && mypy app --ignore-missing-imports

# 3. 运行单元测试并生成覆盖率报告
cd backend && pytest tests/ -v --cov=app --cov-report=html --cov-report=term

# 4. 查看覆盖率报告
open backend/htmlcov/index.html

# 5. 安全检查
cd backend && pip install safety && safety check --full-report
```

**依赖项**：
- Python开发环境已配置

**负责人**：后端开发

---

### 2.2 Go Gateway服务验收

#### 2.2.1 Gateway服务运行

**验收标准**：
- [ ] Gateway服务在8080端口运行
- [ ] 健康检查端点响应正常
- [ ] WebSocket端点可连接
- [ ] 与Python gRPC服务通信正常

**验收方法**：
```bash
# 1. 启动Gateway
make gateway-dev

# 2. 检查健康状态
curl http://localhost:8080/api/v1/health

# 3. 检查CQRS健康状态
curl http://localhost:8080/api/v1/health/cqrs

# 4. 测试WebSocket连接（使用wscat或前端）
wscat -c ws://localhost:8080/ws/chat

# 5. 检查日志
docker logs sparkle_gateway --tail 50
```

**依赖项**：
- 2.1 Python后端服务验收通过

**负责人**：后端开发（Go）

---

#### 2.2.2 Go代码质量验收

**验收标准**：
- [ ] 代码通过golangci-lint检查
- [ ] 单元测试覆盖率 ≥ 50%
- [ ] 无数据竞争问题
- [ ] 构建成功且无警告

**验收方法**：
```bash
# 1. Lint检查
cd backend/gateway && golangci-lint run --timeout=5m

# 2. 运行测试并生成覆盖率
cd backend/gateway && go test -v -race -coverprofile=coverage.out ./...

# 3. 查看覆盖率
cd backend/gateway && go tool cover -func=coverage.out

# 4. 构建
cd backend/gateway && go build -o bin/gateway ./cmd/server
```

**依赖项**：
- Go开发环境已配置

**负责人**：后端开发（Go）

---

### 2.3 Proto API契约验收

#### 2.3.1 Proto文件完整性

**验收标准**：
- [ ] 所有proto文件通过buf lint检查
- [ ] 无breaking changes（相对main分支）
- [ ] 所有服务的Go/Python/Dart代码已生成
- [ ] 生成的代码无编译错误

**验收方法**：
```bash
# 1. Buf lint检查
make proto-lint
# 或直接运行
buf lint

# 2. Breaking change检查
make proto-breaking
# 或直接运行
buf breaking --against '.git#branch=main'

# 3. 生成所有代码
make proto-gen

# 4. 验证生成文件存在
ls -la backend/gateway/gen/
ls -la backend/app/gen/
ls -la mobile/lib/gen/

# 5. 验证各语言编译通过
cd backend/gateway && go build ./gen/...
cd backend && python -m py_compile app/gen/**/*_pb2.py
cd mobile && flutter pub get && flutter analyze
```

**依赖项**：
- buf或protoc已安装

**负责人**：全栈（需各语言配合）

---

## 🟢 第三阶段：业务功能验收（P1 - 可并行进行）

### 3.1 用户认证与授权模块

#### 3.1.1 用户注册登录

**验收标准**：
- [ ] 用户可以通过邮箱注册
- [ ] 注册邮箱验证流程正常
- [ ] 用户可以使用邮箱+密码登录
- [ ] JWT Token签发和验证正常
- [ ] 游客模式可正常使用

**验收方法**：
```bash
# 1. 测试注册API
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "username": "testuser"
  }'

# 2. 测试登录API
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!"
  }'

# 3. 验证JWT Token
# 从登录响应中获取token，然后测试受保护端点
curl http://localhost:8080/api/v1/users/me \
  -H "Authorization: Bearer <YOUR_TOKEN>"

# 4. 前端验收
# - 打开Flutter应用
# - 测试注册流程
# - 测试登录流程
# - 验证登录后状态持久化
```

**依赖项**：
- 2.1 Python后端验收通过
- 2.2 Go Gateway验收通过

**负责人**：全栈（后端+前端）

---

#### 3.1.2 游客模式

**验收标准**：
- [ ] 游客可以不注册直接使用核心功能
- [ ] 游客数据临时存储
- [ ] 注册后可迁移游客数据

**验收方法**：
```dart
// Flutter测试步骤
// 1. 清除应用数据
// 2. 启动应用，选择"游客模式"
// 3. 创建测试任务
// 4. 注册账号
// 5. 验证游客任务已迁移到新账号
```

**负责人**：前端开发

---

### 3.2 AI对话系统模块

#### 3.2.1 基础对话功能

**验收标准**：
- [ ] WebSocket连接稳定
- [ ] 发送消息正常
- [ ] 流式响应正常（逐字显示）
- [ ] 消息历史保存正确
- [ ] 多轮对话上下文保持

**验收方法**：
```bash
# 1. WebSocket测试脚本
cd backend && python test_websocket_client.py

# 2. 前端验收
# - 打开Flutter应用
# - 进入聊天界面
# - 发送测试消息："你好"
# - 验证收到流式响应
# - 切换到其他页面再回来，验证历史消息存在
```

**依赖项**：
- 3.1 用户认证验收通过

**负责人**：全栈

---

#### 3.2.2 AI智能体切换

**验收标准**：
- [ ] 智能体列表可正确显示
- [ ] 可以手动切换智能体
- [ ] AI自动切换智能体（Handoff）
- [ ] 智能体状态显示正确

**验收方法**：
```dart
// 前端测试步骤
// 1. 进入聊天界面
// 2. 发送数学问题："1+1等于几？"
// 3. 验证Math智能体被激活
// 4. 发送编程问题："如何用Python打印Hello World？"
// 5. 验证Code智能体被激活
// 6. 手动切换到Knowledge智能体
// 7. 验证切换成功
```

**负责人**：前端开发

---

#### 3.2.3 语音输入输出

**验收标准**：
- [ ] 语音转文字功能正常（STT）
- [ ] 支持中文语音识别
- [ ] 识别准确率 ≥ 85%
- [ ] 语音输入超时处理正确

**验收方法**：
```bash
# 1. 检查STT配置
grep STT_PROVIDER backend/.env

# 2. 测试语音识别API
# 准备一段测试音频文件
curl -X POST http://localhost:8080/api/v1/stt/transcribe \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@test_audio.wav"

# 3. 前端验收
# - 点击麦克风按钮
// - 说话5-10秒
// - 验证文字正确识别
```

**依赖项**：
- STT服务API密钥已配置（讯飞/阿里云等）

**负责人**：全栈

---

### 3.3 任务管理系统模块

#### 3.3.1 任务CRUD操作

**验收标准**：
- [ ] 可以创建6种类型任务（学习、复习、作业、考试、其他）
- [ ] 可以查看任务列表
- [ ] 可以编辑任务
- [ ] 可以删除任务
- [ ] 可以标记任务完成

**验收方法**：
```bash
# 1. 创建任务API测试
curl -X POST http://localhost:8080/api/v1/tasks \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "验收测试任务",
    "description": "这是验收测试",
    "task_type": "study",
    "due_date": "2026-02-01T18:00:00Z"
  }'

# 2. 获取任务列表
curl http://localhost:8080/api/v1/tasks \
  -H "Authorization: Bearer <TOKEN>"

# 3. 前端验收
// - 打开任务页面
// - 创建新任务
// - 编辑任务
// - 完成任务
// - 删除任务
```

**依赖项**：
- 3.1 用户认证验收通过

**负责人**：全栈

---

#### 3.3.2 专注模式（番茄钟）

**验收标准**：
- [ ] 番茄钟计时准确
- [ ] 专注期间AI激励消息正常
- [ ] 专注中断处理正确
- [ ] 专注数据记录到数据库

**验收方法**：
```dart
// 前端测试步骤
// 1. 打开专注模式
// 2. 开始25分钟专注
// 3. 验证倒计时准确
// 4. 等待AI激励消息
// 5. 中断专注
// 6. 验证专注记录已保存
```

**负责人**：前端开发

---

#### 3.3.3 任务提醒设置

**验收标准**：
- [ ] 可以设置任务提醒时间
- [ ] 提醒通知正常发送
- [ ] 提醒频率设置生效

**验收方法**：
```dart
// 前端测试步骤
// 1. 创建任务
// 2. 设置提前15分钟提醒
// 3. 保存任务
// 4. 手动触发Celery定时任务（或等待）
// 5. 验证收到通知
```

**依赖项**：
- Celery Beat运行正常

**负责人**：全栈

---

### 3.4 计划管理系统模块

#### 3.4.1 计划生成

**验收标准**：
- [ ] AI可以生成学习计划
- [ ] 计划包含多个阶段
- [ ] 每个阶段包含具体任务
- [ ] 计划可以保存

**验收方法**：
```dart
// 前端测试步骤
// 1. 进入聊天界面
// 2. 发送："帮我制定一个为期一周的高数复习计划"
// 3. 验证AI生成计划
// 4. 点击"保存计划"
// 5. 验证计划出现在计划列表
```

**依赖项**：
- 3.2 AI对话验收通过

**负责人**：全栈

---

#### 3.4.2 计划评审

**验收标准**：
- [ ] 计划评审流程正常
- [ ] 评审结果显示正确
- [ ] 可以批准、拒绝、修改计划
- [ ] 评审决策正确处理

**验收方法**：
```dart
// 前端测试步骤
// 1. 创建计划
// 2. 等待AI评审
// 3. 查看评审卡片（显示评分和问题）
// 4. 点击"批准"
// 5. 验证计划状态更新为已批准
```

**依赖项**：
- 3.4.1 计划生成验收通过

**负责人**：全栈

---

#### 3.4.3 计划执行追踪

**验收标准**：
- [ ] 计划进度实时更新
- [ ] 任务完成状态同步
- [ ] 计划完成百分比正确
- [ ] 逾期提醒正常

**验收方法**：
```dart
// 前端测试步骤
// 1. 打开计划详情
// 2. 完成计划中的第一个任务
// 3. 验证进度百分比更新
// 4. 查看计划时间线
```

**负责人**：前端开发

---

### 3.5 知识星图系统模块

#### 3.5.1 知识点展示

**验收标准**：
- [ ] 知识星图可正确渲染
- [ ] 节点（知识点）显示正确
- [ ] 边（关系）显示正确
- [ ] 交互流畅（缩放、拖拽）

**验收方法**：
```dart
// 前端测试步骤
// 1. 进入知识星图页面
// 2. 验证星图渲染（节点和边）
// 3. 双指缩放测试
// 4. 拖拽节点测试
// 5. 点击节点查看详情
```

**依赖项**：
- 用户有知识数据

**负责人**：前端开发

---

#### 3.5.2 GraphRAG检索

**验收标准**：
- [ ] 向量检索响应时间 < 200ms
- [ ] 图遍历响应时间 < 500ms
- [ ] 综合检索响应时间 < 800ms
- [ ] 检索结果相关度合理

**验收方法**：
```bash
# 1. 测试向量检索性能
cd backend && python tests/test_rag_retrieval.py

# 2. 测试图遍历性能
cd backend && python tests/test_graph_reasoning.py

# 3. 测试综合检索
cd backend && python tests/test_graph_rag.py

# 4. 前端验收
// - 在知识星图搜索框输入关键词
// - 验证搜索结果
// - 点击结果查看关联知识点
```

**依赖项**：
- 知识点数据已初始化

**负责人**：后端开发

---

#### 3.5.3 知识点掌握度

**验收标准**：
- [ ] 掌握度分数正确计算（0-100）
- [ ] 遗忘曲线算法生效
- [ ] 掌握度变化正确记录
- [ ] 可视化展示正确

**验收方法**：
```bash
# 1. 测试掌握度更新API
curl -X POST http://localhost:8080/api/v1/knowledge/update-mastery \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_point_id": "kp_001",
    "mastery_level": 75,
    "interaction_type": "review"
  }'

# 2. 查询知识点掌握度
curl http://localhost:8080/api/v1/knowledge/kp_001/mastery \
  -H "Authorization: Bearer <TOKEN>"

# 3. 前端验收
// - 查看知识点详情
// - 验证掌握度分数显示
// - 查看掌握度历史曲线
```

**负责人**：全栈

---

### 3.6 错题本系统模块

#### 3.6.1 错题记录

**验收标准**：
- [ ] 可以手动添加错题
- [ ] AI可以自动识别错题
- [ ] 错题分类正确
- [ ] 错题详情完整（题目、答案、解析）

**验收方法**：
```bash
# 1. 创建错题API测试
curl -X POST http://localhost:8080/api/v1/error-book \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "数学",
    "question": "求解方程x^2 - 5x + 6 = 0",
    "wrong_answer": "x = 2, x = 4",
    "correct_answer": "x = 2, x = 3",
    "reason": "计算错误"
  }'

# 2. 前端验收
// - 进入错题本
// - 添加错题
// - 验证错题保存
```

**负责人**：全栈

---

#### 3.6.2 错题分析与复习

**验收标准**：
- [ ] 错题统计分析正确
- [ ] 薄弱点识别准确
- [ ] 复习推荐合理
- [ ] 复习效果追踪

**验收方法**：
```dart
// 前端测试步骤
// 1. 打开错题本
// 2. 查看"错题分析"卡片
// 3. 验证薄弱点显示
// 4. 查看"推荐复习"
// 5. 开始复习，标记掌握
// 6. 验证复习记录
```

**负责人**：前端开发

---

### 3.7 社区系统模块

#### 3.7.1 好友系统

**验收标准**：
- [ ] 可以搜索用户
- [ ] 可以发送好友请求
- [ ] 可以接受/拒绝好友请求
- [ ] 好友列表显示正确

**验收方法**：
```bash
# 1. 搜索用户API测试
curl "http://localhost:8080/api/v1/community/users?search=test" \
  -H "Authorization: Bearer <TOKEN>"

# 2. 发送好友请求
curl -X POST http://localhost:8080/api/v1/community/friend-requests \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"to_user_id": "user_123"}'

# 3. 前端验收
// - 搜索用户
// - 发送好友请求
// - 接受好友请求
// - 查看好友列表
```

**负责人**：全栈

---

#### 3.7.2 学习群组

**验收标准**：
- [ ] 可以创建学习群组
- [ ] 可以加入群组
- [ ] 群组打卡功能正常
- [ ] 群组聊天功能正常

**验收方法**：
```dart
// 前端测试步骤
// 1. 创建学习群组
// 2. 邀请好友加入
// 3. 在群组中打卡
// 4. 发送群消息
```

**负责人**：全栈

---

#### 3.7.3 火堆系统（实时互动）

**验收标准**：
- [ ] 火堆会话创建正常
- [ ] 实时消息同步正常
- [ ] 火堆过期处理正确

**验收方法**：
```dart
// 前端测试步骤
// 1. 进入社区
// 2. 创建火堆
// 3. 邀请好友加入
// 4. 实时聊天测试
```

**负责人**：前端开发

---

### 3.8 商城系统模块

#### 3.8.1 光子积分系统

**验收标准**：
- [ ] 完成任务获得光子积分
- [ ] 积分计算正确
- [ ] 积分余额显示正确
- [ ] 积分历史记录完整

**验收方法**：
```bash
# 1. 查询用户积分
curl http://localhost:8080/api/v1/shop/photon-balance \
  -H "Authorization: Bearer <TOKEN>"

# 2. 查询积分历史
curl http://localhost:8080/api/v1/shop/photon-history \
  -H "Authorization: Bearer <TOKEN>"

# 3. 前端验收
// - 完成一个任务
// - 验证获得积分
// - 查看积分余额
// - 查看积分历史
```

**负责人**：全栈

---

#### 3.8.2 皮肤与称号商城

**验收标准**：
- [ ] 商品列表显示正确
- [ ] 可以购买皮肤/称号
- [ ] 购买后扣除积分
- [ ] 可以装备已购买的物品
- [ ] 装备效果生效

**验收方法**：
```dart
// 前端测试步骤
// 1. 进入商城
// 2. 浏览商品
// 3. 购买一个皮肤
// 4. 验证积分扣除
// 5. 装备皮肤
// 6. 验证UI效果改变
```

**负责人**：前端开发

---

### 3.9 通知中心模块

#### 3.9.1 通知推送

**验收标准**：
- [ ] 系统通知正确推送
- [ ] 通知类型分类正确
- [ ] 通知已读/未读状态正确
- [ ] 通知删除功能正常

**验收方法**：
```bash
# 1. 获取通知列表
curl http://localhost:8080/api/v1/notifications \
  -H "Authorization: Bearer <TOKEN>"

# 2. 标记已读
curl -X PUT http://localhost:8080/api/v1/notifications/notif_001/read \
  -H "Authorization: Bearer <TOKEN>"

# 3. 前端验收
// - 完成一个任务，触发通知
// - 查看通知中心
// - 标记已读
// - 删除通知
```

**负责人**：全栈

---

#### 3.9.2 智能推送

**验收标准**：
- [ ] 基于用户画像的个性化推送
- [ ] 推送时间合理
- [ ] 推送内容相关度高
- [ ] 可以关闭推送

**验收方法**：
```bash
# 1. 手动触发推送任务
cd backend && python -m app.jobs.notification_job

# 2. 验证用户收到通知

# 3. 前端验收
// - 进入设置
// - 配置推送偏好
// - 等待推送（或手动触发）
// - 验证推送内容相关性
```

**依赖项**：
- Celery Beat运行

**负责人**：后端开发

---

## 🔵 第四阶段：集成测试验收（P1）

### 4.1 端到端场景测试

#### 4.1.1 新用户完整旅程

**验收标准**：
- [ ] 新用户注册 → 首次登录引导 → 创建第一个任务 → 与AI对话 → 查看知识星图 → 完成任务 → 查看统计

**验收方法**：
```dart
// 完整用户旅程测试脚本
// 1. 注册新账号
// 2. 完成新手引导
// 3. 创建"学习Python基础"任务
// 4. 问AI："如何学习Python？"
// 5. 查看知识星图中Python相关知识
// 6. 标记任务完成
// 7. 查看学习统计
```

**负责人**：QA测试

---

#### 4.1.2 学习闭环验证

**验收标准**：
- [ ] AI对话 → 知识拓展 → 掌握度更新 → 复习推荐 → 完成复习 → 画像更新

**验收方法**：
```dart
// 学习闭环测试
// 1. 向AI提问："什么是线性代数的特征值？"
// 2. 查看AI回答中的知识点拓展
// 3. 在知识星图中验证"特征值"掌握度更新
// 4. 查看复习推荐中是否包含该知识点
// 5. 完成复习
// 6. 验证用户认知画像中的数学维度提升
```

**负责人**：QA测试

---

#### 4.1.3 跨模块数据一致性

**验收标准**：
- [ ] 任务完成 → 积分增加 → 统计更新 → 通知推送
- [ ] 知识点掌握度变化 → 用户画像更新 → 推荐调整
- [ ] 计划任务完成 → 进度更新 → 计划状态变化

**验收方法**：
```bash
# 数据一致性验证脚本
cd backend && python tests/integration/final_validation.py
```

**负责人**：后端开发

---

### 4.2 并发与负载测试

#### 4.2.1 WebSocket并发连接

**验收标准**：
- [ ] 支持100+并发WebSocket连接
- [ ] 消息延迟 < 500ms
- [ ] 无连接丢失

**验收方法**：
```bash
# 使用压测工具（如artillery）
cd backend && python tests/load/test_websocket_concurrent.py
```

**负责人**：后端DevOps

---

#### 4.2.2 API并发请求

**验收标准**：
- [ ] 关键API支持50+ QPS
- [ ] P95延迟 < 500ms
- [ ] 无5xx错误

**验收方法**：
```bash
# 使用Apache Bench或wrk
ab -n 1000 -c 50 http://localhost:8080/api/v1/health
```

**负责人**：后端DevOps

---

## 🟣 第五阶段：性能与安全验收（P2 - 非阻塞）

### 5.1 性能验收

#### 5.1.1 响应时间指标

**验收标准**：
- [ ] API健康检查 < 50ms
- [ ] GraphQL查询 < 200ms
- [ ] 向量检索 < 200ms
- [ ] 图遍历 < 500ms
- [ ] 综合检索 < 800ms
- [ ] WebSocket消息延迟 < 300ms

**验收方法**：
```bash
# 运行性能基准测试
cd backend && pytest tests/performance/benchmark_suite.py -v
```

**负责人**：后端开发

---

#### 5.1.2 资源使用

**验收标准**：
- [ ] 后端服务内存使用 < 2GB
- [ ] Gateway服务内存使用 < 1GB
- [ ] 数据库连接池使用率 < 80%
- [ ] Redis内存使用 < 4GB

**验收方法**：
```bash
# 检查容器资源使用
docker stats --no-stream

# 检查数据库连接
docker exec sparkle_db psql -U postgres -d sparkle -c "SELECT count(*) FROM pg_stat_activity;"
```

**负责人**：DevOps

---

### 5.2 安全验收

#### 5.2.1 认证授权

**验收标准**：
- [ ] 所有API端点都验证JWT
- [ ] 过期Token被拒绝
- [ ] 无效Token返回401
- [ ] 越权访问被拒绝

**验收方法**：
```bash
# 1. 无Token测试
curl http://localhost:8080/api/v1/users/me
# 应返回401

# 2. 过期Token测试
curl http://localhost:8080/api/v1/users/me \
  -H "Authorization: Bearer expired_token"
# 应返回401

# 3. 越权测试（User A尝试访问User B的数据）
curl http://localhost:8080/api/v1/users/user_b_id \
  -H "Authorization: Bearer user_a_token"
# 应返回403
```

**负责人**：后端开发

---

#### 5.2.2 数据加密

**验收标准**：
- [ ] 密码使用bcrypt哈希
- [ ] 敏感数据不记录到日志
- [ ] 环境变量不包含明文密钥
- [ ] HTTPS传输（生产环境）

**验收方法**：
```bash
# 1. 检查日志中的敏感信息
docker logs sparkle_api | grep -i password
# 应无明文密码

# 2. 检查.env文件
cat backend/.env | grep -v "SECRET\|KEY\|PASSWORD"
# 验证密钥已配置

# 3. 验证数据库中的密码哈希
docker exec sparkle_db psql -U postgres -d sparkle -c "SELECT password FROM users LIMIT 1;"
# 应为bcrypt哈希（$2b$开头）
```

**负责人**：DevOps

---

#### 5.2.3 输入验证

**验收标准**：
- [ ] SQL注入防护
- [ ] XSS防护
- [ ] 文件上传安全检查
- [ ] 请求大小限制

**验收方法**：
```bash
# 1. SQL注入测试
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@--", "password": "anything"}'
# 应返回400而非500

# 2. XSS测试
curl -X POST http://localhost:8080/api/v1/tasks \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"title": "<script>alert(1)</script>"}'
# 应接受输入但在转义后显示
```

**负责人**：后端开发

---

#### 5.2.4 API速率限制

**验收标准**：
- [ ] 每个用户每分钟请求数受限
- [ ] 超限返回429
- [ ] WebSocket连接频率受限

**验收方法**：
```bash
# 快速发送多个请求
for i in {1..100}; do
  curl http://localhost:8080/api/v1/health
done

# 验证后续请求返回429
```

**负责人**：后端开发

---

### 5.3 可观测性验收

#### 5.3.1 日志记录

**验收标准**：
- [ ] 所有错误有日志记录
- [ ] 日志级别配置正确
- [ ] 敏感信息不记录
- [ ] 日志格式统一（JSON）

**验收方法**：
```bash
# 1. 检查日志格式
docker logs sparkle_api --tail 10 | jq .

# 2. 检查错误日志
docker logs sparkle_api 2>&1 | grep ERROR

# 3. 验证日志不包含密码
docker logs sparkle_api 2>&1 | grep -i "password\|secret" | wc -l
# 应为0
```

**负责人**：后端开发

---

#### 5.3.2 监控指标

**验收标准**：
- [ ] Prometheus采集关键指标
- [ ] Grafana仪表板正常显示
- [ ] 告警规则已配置

**验收方法**：
```bash
# 1. 检查Prometheus目标
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'

# 2. 访问Grafana
open http://localhost:3000

# 3. 验证仪表板数据
```

**负责人**：DevOps

---

#### 5.3.3 链路追踪

**验收标准**：
- [ ] Tempo追踪正常
- [ ] 跨服务调用可追踪
- [ ] 追踪数据完整

**验收方法**：
```bash
# 1. 检查Tempo状态
curl http://localhost:4318/status

# 2. 生成测试追踪
# 发起一个API请求，然后在Tempo UI中查看
```

**负责人**：DevOps

---

## 🟤 第六阶段：部署上线验收（P0 - 最终验收）

### 6.1 构建与打包

#### 6.1.1 后端Docker镜像

**验收标准**：
- [ ] Gateway镜像构建成功
- [ ] Backend镜像构建成功
- [ ] 镜像大小合理（< 500MB）
- [ ] 镜像扫描无高危漏洞

**验收方法**：
```bash
# 1. 构建镜像
docker build -t sparkle-gateway:test ./backend/gateway
docker build -t sparkle-backend:test ./backend

# 2. 检查镜像大小
docker images sparkle-gateway:test sparkle-backend:test

# 3. 扫描漏洞
docker scan sparkle-gateway:test
docker scan sparkle-backend:test
```

**负责人**：DevOps

---

#### 6.1.2 移动端APK/IPA

**验收标准**：
- [ ] APK构建成功
- [ ] 签名配置正确
- [ ] 版本号正确
- [ ] 应用图标和名称正确

**验收方法**：
```bash
# 1. 构建APK
cd mobile && flutter build apk --release

# 2. 检查APK信息
ls -lh build/app/outputs/flutter-apk/app-release.apk

# 3. 安装测试
adb install build/app/outputs/flutter-apk/app-release.apk

# 4. 验证应用信息
aapt dump badging build/app/outputs/flutter-apk/app-release.apk | grep version
```

**负责人**：前端开发

---

### 6.2 生产环境部署

#### 6.2.1 Kubernetes部署

**验收标准**：
- [ ] 所有Pod正常运行
- [ ] Service暴露正确
- [ ] Ingress配置正确
- [ ] ConfigMap和Secret已配置

**验收方法**：
```bash
# 1. 部署到K8s
kubectl apply -k k8s/prod

# 2. 检查Pod状态
kubectl get pods -n sparkle-prod

# 3. 检查Service
kubectl get svc -n sparkle-prod

# 4. 检查日志
kubectl logs -f deployment/sparkle-gateway -n sparkle-prod
```

**依赖项**：
- Kubernetes集群已配置
- 容器镜像已推送到镜像仓库

**负责人**：DevOps

---

#### 6.2.2 蓝绿部署

**验收标准**：
- [ ] 蓝绿切换流程正常
- [ ] 健康检查通过后才切换
- [ ] 回滚机制可用
- [ ] 零停机部署

**验收方法**：
```bash
# 1. 执行蓝绿部署
./scripts/deploy-prod.sh

# 2. 监控切换过程
watch kubectl get pods -n sparkle-prod

# 3. 验证流量切换
curl http://<生产域名>/api/v1/health

# 4. 测试回滚（如需要）
kubectl undo deployment sparkle-gateway -n sparkle-prod
```

**负责人**：DevOps

---

#### 6.2.3 数据库迁移

**验收标准**：
- [ ] 生产数据库迁移成功
- [ ] 数据无丢失
- [ ] 迁移可回滚

**验收方法**：
```bash
# 1. 备份生产数据库
pg_dump -h <prod-host> -U postgres -d sparkle > backup_before_migration.sql

# 2. 执行迁移
cd backend && alembic upgrade head

# 3. 验证数据完整性
cd backend && python scripts/verify_data_integrity.py

# 4. 准备回滚脚本（如需要）
cd backend && alembic downgrade -1
```

**负责人**：后端DevOps

---

### 6.3 上线后验证

#### 6.3.1 冒烟测试

**验收标准**：
- [ ] 所有关键端点响应正常
- [ ] 响应时间在可接受范围
- [ ] 无关键错误日志

**验收方法**：
```bash
# 1. 运行冒烟测试脚本
./scripts/verify_deployment.sh https://<生产域名>

# 2. 手动验证关键功能
# - 用户注册登录
# - AI对话
# - 任务创建
# - 知识星图查看

# 3. 检查错误日志
kubectl logs -l app=sparkle-gateway -n sparkle-prod --tail 100 | grep ERROR
```

**负责人**：QA测试

---

#### 6.3.2 监控告警

**验收标准**：
- [ ] 所有监控指标正常
- [ ] 无未解决的告警
- [ ] 告警通知渠道正常

**验收方法**：
```bash
# 1. 检查Prometheus指标
curl http://<prometheus-url>/api/v1/query?query=up

# 2. 检查Grafana仪表板
# 访问生产Grafana查看关键指标

# 3. 验证告警
# 查看告警通知渠道（邮件/钉钉/企业微信）
```

**负责人**：DevOps

---

#### 6.3.3 用户验收测试（UAT）

**验收标准**：
- [ ] 核心用户完成测试
- [ ] 关键功能无Bug
- [ ] 性能满足预期
- [ ] 用户反馈总体满意

**验收方法**：
```bash
# 1. 邀请5-10名种子用户
# 2. 提供测试环境和任务清单
# 3. 收集用户反馈
# 4. 统计问题和满意度

# 示例任务清单：
# - 注册账号并完成新手引导
# - 与AI对话学习一个知识点
# - 创建学习计划并执行
# - 使用知识星图查看知识点
# - 完成一个专注会话
# - 查看学习统计报告
```

**负责人**：产品经理

---

## 📊 验收汇总表

| 模块 | 验收项数 | 通过数 | 失败数 | 通过率 | 状态 |
|------|----------|--------|--------|--------|------|
| 第一阶段：基础设施 | 7 | | | | ⏳ |
| 第二阶段：核心服务 | 7 | | | | ⏳ |
| 第三阶段：业务功能 | 30 | | | | ⏳ |
| 第四阶段：集成测试 | 3 | | | | ⏳ |
| 第五阶段：性能安全 | 8 | | | | ⏳ |
| 第六阶段：部署上线 | 6 | | | | ⏳ |
| **总计** | **61** | | | | **⏳** |

---

## ✅ 最终验收签字

### 验收组签字

- [ ] **技术负责人**：_________________  日期：____/____/____
- [ ] **产品负责人**：_________________  日期：____/____/____
- [ ] **测试负责人**：_________________  日期：____/____/____
- [ ] **运维负责人**：_________________  日期：____/____/____

### 验收结论

- [ ] **通过** - 所有P0和P1项验收通过，可以上线
- [ ] **条件通过** - 存在次要问题，但不影响核心功能，可以上线并后续修复
- [ ] **不通过** - 存在阻塞性问题，需要修复后重新验收

### 备注

_____________________________________________________________________________

_____________________________________________________________________________

_____________________________________________________________________________

---

## 📎 附录

### A. 常用验收命令速查

```bash
# 基础设施健康检查
make dev-up                    # 启动基础设施
make smoke                     # 冒烟测试
make env-check                 # 配置检查

# 数据库
make sync-db                   # 同步数据库
alembic current                # 检查迁移版本
alembic upgrade head           # 应用迁移

# 服务
make grpc-server               # 启动gRPC服务
make gateway-dev               # 启动Gateway
make celery-up                 # 启动Celery

# 测试
cd backend && pytest           # Python测试
cd backend/gateway && go test  # Go测试
cd mobile && flutter test      # Flutter测试

# Proto
make proto-gen                 # 生成proto代码
make proto-lint                # Lint检查

# 部署
./scripts/deploy-prod.sh      # 生产部署
./scripts/verify_deployment.sh # 部署验证
```

### B. 关键配置文件清单

```
环境变量：
- .env                        # 根目录环境变量（开发）
- backend/.env                # 后端环境变量
- backend/gateway/.env        # Gateway环境变量

Docker：
- docker-compose.yml          # 开发环境
- docker-compose.prod.yml     # 生产环境
- docker-compose.celery.yml   # Celery服务

K8s：
- k8s/base/                   # 基础配置
- k8s/prod/                   # 生产环境
- k8s/staging/                # 预发布环境

监控：
- monitoring/prometheus.yml   # Prometheus配置
- monitoring/grafana-*.yaml   # Grafana配置
- monitoring/loki-config.yaml # Loki配置
- monitoring/tempo.yaml       # Tempo配置
```

### C. 故障排查指南

```bash
# 数据库连接失败
docker logs sparkle_db --tail 50
docker exec sparkle_db pg_isready -U postgres

# Redis连接失败
docker logs sparkle_redis --tail 50
docker exec sparkle_redis redis-cli -a change-me ping

# gRPC服务启动失败
docker logs sparkle_agent --tail 100
grpcurl -plaintext localhost:50051 list

# Gateway启动失败
docker logs sparkle_gateway --tail 100
curl http://localhost:8080/api/v1/health

# WebSocket连接失败
# 检查Gateway日志
docker logs sparkle_gateway -f | grep WebSocket

# Celery任务不执行
make celery-status
make celery-logs-worker

# 前端构建失败
cd mobile && flutter clean
cd mobile && flutter pub get
cd mobile && flutter doctor
```

### D. 联系方式

| 角色 | 姓名 | 联系方式 | 负责范围 |
|------|------|----------|----------|
| 项目负责人 | | | 总协调 |
| 后端负责人 | | | Python/Go后端 |
| 前端负责人 | | | Flutter客户端 |
| DevOps负责人 | | | 部署运维 |
| 测试负责人 | | | 质量保证 |

---

**文档版本**：v1.0
**最后更新**：2026-01-28
**维护者**：Sparkle项目组
**审核者**：_______________
**批准者**：_______________
