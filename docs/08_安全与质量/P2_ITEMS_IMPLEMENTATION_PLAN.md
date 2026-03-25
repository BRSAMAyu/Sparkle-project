# P2 级工程化优化实施计划

**日期**: 2025-12-28
**优先级**: P2 级工程化改进
**预计工作量**: 8-12 周
**关键依赖**: P0/P1 完成

---

## 📋 P2 优化项目清单

从审计报告中确定的 P2 级问题：

1. **设计系统并存与主题初始化不一致** (HIGH IMPACT)
2. **Flutter 依赖重复** (MEDIUM IMPACT)
3. **Gateway 缺少测试覆盖** (HIGH COMPLEXITY)
4. **Access Control 未接入** (MEDIUM IMPACT)
5. **Python 依赖定义存在双轨** (LOW COMPLEXITY)

---

## 1️⃣ 设计系统整合 (Design System Consolidation)

### 现状分析

**三套并存的设计系统**:

| 系统 | 位置 | 状态 | 使用 | 问题 |
|------|------|------|------|------|
| System A (AppThemes) | `app/theme.dart` | **ACTIVE** | app.dart | 依赖已弃用的 AppDesignTokens |
| System B (Design System 2.0) | `core/design/design_system.dart` | **INSTALLED** | 基础设施 | 未在主应用集成 |
| System C (SparkleTheme) | `core/design/sparkle_theme.dart` | **ABANDONED** | 无 | 颜色冲突，未使用 |

**关键冲突**:
- System A/B/C 的主颜色不同 (Orange 0xFFFF6B35 vs Purple 0xFF6750A4 vs Orange 0xFFE67E22)
- System A/B 都有 AppThemes 类 (命名冲突)
- System A 依赖 @Deprecated AppDesignTokens
- 两套间距系统 (AppDesignTokens vs SparkleSpacing)
- 两套排版系统 (TextTheme vs SparkleTypography)

### 整合方案

#### Phase 1: 解决命名冲突 (Week 1-2)

**目标**: 消除类名冲突，为迁移做准备

**步骤 1.1**: 重命名 System B 的 AppThemes
```dart
// OLD: class AppThemes in design_system.dart
// NEW: class SparkleAppThemes
```

**步骤 1.2**: 更新导入
```dart
// app.dart
// FROM:
// import 'core/design/design_system.dart' show AppThemes;

// TO:
import 'core/design/design_system.dart' show SparkleAppThemes;

// app.dart theme configuration:
theme: SparkleAppThemes.lightTheme,
darkTheme: SparkleAppThemes.darkTheme,
```

**步骤 1.3**: 创建 System A 弃用别名
```dart
// app/theme.dart (末尾添加)
@deprecated('Use SparkleAppThemes instead')
typedef AppThemes = SparkleAppThemes;
```

**涉及文件**:
- `mobile/lib/core/design/design_system.dart` (重命名类)
- `mobile/lib/app/app.dart` (更新导入)
- `mobile/lib/app/theme.dart` (添加弃用别名)

#### Phase 2: 整合颜色系统 (Week 2-3)

**目标**: 统一颜色定义，移除 AppDesignTokens

**步骤 2.1**: 验证 System B SparkleColors 颜色定义
```dart
// tokens_v2/color_token.dart 中应包含
class SparkleColors {
  final Color primary = const Color(0xFFFF6B35);      // Orange
  final Color secondary = const Color(0xFF5C6BC0);    // Lighter navy
  final Color tertiary = const Color(0xFFF1C40F);     // Yellow
  // ... 所有语义色彩
}
```

**步骤 2.2**: 更新 System A (AppThemes) 使用 System B 颜色
```dart
// BEFORE: 使用 AppDesignTokens.primaryBase
// AFTER: 使用 SparkleColors.primary 或 DS.brandPrimary
```

**步骤 2.3**: 从 System A 中移除 AppDesignTokens 引用
```dart
// app/theme.dart 中，将所有
// AppDesignTokens.spacing* → SparkleSpacing.* (or DS.xs, DS.sm, etc)
// AppDesignTokens.color* → SparkleColors.* (or DS.brandPrimary, etc)
```

**步骤 2.4**: 验证 SparkleColors 覆盖所有必要颜色
```dart
// 检查清单:
- ✓ 品牌色 (primary/secondary/tertiary)
- ✓ 语义色 (success/error/warning/info)
- ✓ 中性色 (50-900 灰度)
- ✓ 任务类型色 (学习/训练/修正/反思/社交/计划)
- ✓ 状态色 (在线/离线)
```

**涉及文件**:
- `mobile/lib/core/design/tokens_v2/color_token.dart` (验证完整)
- `mobile/lib/app/theme.dart` (迁移颜色引用)
- `mobile/lib/core/design/design_tokens.dart` (标记弃用)

#### Phase 3: 整合排版和间距 (Week 3-4)

**目标**: 统一文本样式和间距定义

**步骤 3.1**: 验证 System B SparkleTypography
```dart
// tokens_v2/typography_token.dart 应包含
- displayLarge, displayMedium, displaySmall
- headlineLarge, headlineMedium, headlineSmall
- titleLarge, titleMedium, titleSmall
- bodyLarge, bodyMedium, bodySmall
- labelLarge, labelMedium, labelSmall
```

**步骤 3.2**: 替换 TextTheme 引用
```dart
// BEFORE: Theme.of(context).textTheme.headlineLarge
// AFTER: context.sparkleTheme.typography.headlineLarge
// OR: DS.typography.headlineLarge (如果 DS 提供快捷方式)
```

**步骤 3.3**: 验证 SparkleSpacing 间距值
```dart
// tokens_v2/spacing_token.dart 应定义 8pt 网格
const xs = 4.0;   // 8pt 的 0.5x
const sm = 8.0;   // 8pt 的 1x
const md = 16.0;  // 8pt 的 2x
const lg = 24.0;  // 8pt 的 3x
const xl = 32.0;  // 8pt 的 4x
const xxl = 64.0; // 8pt 的 8x
```

**步骤 3.4**: 迁移间距引用
```dart
// BEFORE: AppDesignTokens.spacing16
// AFTER: SpaceToken.md 或 DS.md
```

**涉及文件**:
- `mobile/lib/core/design/tokens_v2/typography_token.dart` (验证完整)
- `mobile/lib/core/design/tokens_v2/spacing_token.dart` (验证完整)
- `mobile/lib/app/theme.dart` (迁移引用)

#### Phase 4: 集成主题持久化 (Week 4-5)

**目标**: 使用 System B 的 ThemeManager，支持主题切换和持久化

**步骤 4.1**: 更新 theme_provider.dart
```dart
// BEFORE: 自定义 Riverpod provider
// AFTER: 包装 ThemeManager

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/design/tokens_v2/theme_manager.dart';

final themeManagerProvider = StateProvider<ThemeManager>((ref) {
  return ThemeManager(); // 自动从 SharedPreferences 加载
});

final sparkleThemeDataProvider = StateProvider<SparkleThemeData>((ref) {
  final manager = ref.watch(themeManagerProvider);
  return manager.currentTheme;
});
```

**步骤 4.2**: 更新 app.dart 使用 Riverpod 主题
```dart
// BEFORE: 静态主题
// AFTER: 响应式主题

theme: context.watch(sparkleThemeDataProvider).toMaterialTheme(),
darkTheme: context.watch(sparkleThemeDataProvider).toMaterialTheme(),

onThemeChanged: (ThemeBrightness brightness) {
  ref.read(themeManagerProvider).setBrightness(brightness);
},
```

**步骤 4.3**: 启用主题预设
```dart
// 利用 System B 的品牌预设 (Sparkle/Ocean/Forest)
// 在设置页面添加主题选择器:

enum BrandPreset { sparkle, ocean, forest }

onBrandSelected: (preset) {
  ref.read(themeManagerProvider).setBrandPreset(preset);
}
```

**涉及文件**:
- `mobile/lib/presentation/providers/theme_provider.dart` (集成 ThemeManager)
- `mobile/lib/app/app.dart` (使用 Riverpod 主题)
- 设置屏幕 (添加主题选择 UI)

#### Phase 5: 清理和弃用 (Week 5-6)

**步骤 5.1**: 移除 System C (SparkleTheme)
```bash
# 删除文件
rm mobile/lib/core/design/sparkle_theme.dart

# 更新导入 (这个文件几乎不被使用)
```

**步骤 5.2**: 标记 System A 为弃用
```dart
// app/theme.dart 顶部添加
@deprecated(
  'AppThemes is deprecated. Use SparkleAppThemes instead. '
  'This will be removed in v3.0.0. '
  'See migration guide: docs/DESIGN_SYSTEM_MIGRATION.md'
)
class AppThemes {
  // ... 保持向后兼容
}
```

**步骤 5.3**: 标记 AppDesignTokens 为弃用 (准备移除)
```dart
// design_tokens.dart 顶部
@Deprecated(
  'AppDesignTokens is deprecated. Use SparkleColors, SparkleSpacing, '
  'SparkleTypography, and SparkleAnimations instead. '
  'This will be removed in v3.0.0.'
)
class AppDesignTokens {
  // ... 保持向后兼容
}
```

**步骤 5.4**: 创建迁移指南
```markdown
# 设计系统迁移指南 v2 → v3

## 颜色迁移
- OLD: AppDesignTokens.primaryBase
- NEW: DS.brandPrimary 或 context.sparkleTheme.colors.primary

## 间距迁移
- OLD: AppDesignTokens.spacing16
- NEW: DS.md 或 context.sparkleTheme.spacing.md

## 排版迁移
- OLD: Theme.of(context).textTheme.headlineLarge
- NEW: context.sparkleTheme.typography.headlineLarge
```

**涉及文件**:
- `mobile/lib/core/design/sparkle_theme.dart` (删除)
- `mobile/lib/app/theme.dart` (弃用标记)
- `mobile/lib/core/design/design_tokens.dart` (弃用标记)
- 新建: `docs/DESIGN_SYSTEM_MIGRATION.md`

### 验收标准

- [ ] SparkleAppThemes 在 app.dart 中使用
- [ ] 所有颜色引用使用 SparkleColors (或 DS 快捷方式)
- [ ] 所有间距引用使用 SparkleSpacing (或 DS 快捷方式)
- [ ] 所有排版使用 SparkleTypography
- [ ] theme_provider.dart 集成 ThemeManager
- [ ] 主题切换和持久化工作正常
- [ ] SparkleTheme.dart 已删除
- [ ] AppThemes/AppDesignTokens 标记为弃用
- [ ] 所有测试通过
- [ ] 无 lint 警告

---

## 2️⃣ Flutter 依赖整理 (Dependency Cleanup)

### 现状分析

**不使用的依赖** (5 个):
1. `retrofit` ^4.0.3 - 声明但未导入 (Dio 处理网络)
2. `lottie` ^3.0.0 - 声明但未导入
3. `flutter_timezone` ^5.0.1 - 声明但未导入 (timezone 足够)
4. `cupertino_icons` ^1.0.6 - 未导入
5. `retrofit_generator` (dev) - 配对 retrofit

**没有重复**, **没有版本冲突** ✓

### 整理计划

#### Step 1: 验证不使用的依赖 (30 min)

```bash
cd mobile

# 搜索每个包的导入
grep -r "import 'package:retrofit" lib/ test/ || echo "retrofit not imported"
grep -r "import 'package:lottie" lib/ test/ || echo "lottie not imported"
grep -r "import 'package:flutter_timezone" lib/ test/ || echo "flutter_timezone not imported"
grep -r "import 'package:cupertino_icons" lib/ test/ || echo "cupertino_icons not imported"
```

#### Step 2: 移除依赖 (30 min)

编辑 `mobile/pubspec.yaml`:

```yaml
# REMOVE from dependencies:
# - retrofit: ^4.0.3
# - lottie: ^3.0.0
# - flutter_timezone: ^5.0.1
# - cupertino_icons: ^1.0.6

# REMOVE from dev_dependencies:
# - retrofit_generator: ^8.0.4
```

或者运行:
```bash
flutter pub remove retrofit lottie flutter_timezone cupertino_icons retrofit_generator
```

#### Step 3: 更新和测试 (30 min)

```bash
flutter pub get
flutter analyze  # 检查 lint 警告
flutter test     # 运行所有测试
flutter run      # 验证应用正常运行
```

### 验收标准

- [ ] 5 个不使用的依赖已移除
- [ ] `flutter pub get` 成功
- [ ] `flutter analyze` 无错误
- [ ] 所有测试通过
- [ ] 应用正常运行
- [ ] 依赖数从 40 → 35

---

## 3️⃣ Gateway 测试覆盖 (Testing Implementation)

### 现状分析

**0 个测试文件** 在 2,418 行生产代码中
**关键组件未覆盖**:
- Chat Orchestrator (WebSocket)
- gRPC Client
- CQRS Outbox & Workers
- Authentication Middleware

### 实施方案

#### Phase 1: 基础设施设置 (Week 1-2)

**步骤 1.1**: 添加测试依赖到 go.mod

```bash
cd backend/gateway

# 添加测试框架
go get -u github.com/stretchr/testify/assert
go get -u github.com/stretchr/testify/mock
go get -u github.com/testcontainers/testcontainers-go

# 用于 WebSocket 测试
# (http/net 在标准库中已包含)
```

**步骤 1.2**: 创建测试数据和 Fixtures

```bash
mkdir -p testdata

# 创建 fixture 文件
cat > testdata/jwt_tokens.json << 'EOF'
{
  "valid_token": "eyJhbGc...",
  "expired_token": "eyJhbGc...",
  "invalid_token": "invalid"
}
EOF

cat > testdata/chat_messages.json << 'EOF'
[
  {"id": "msg1", "text": "hello", "role": "user"},
  {"id": "msg2", "text": "hi there", "role": "assistant"}
]
EOF
```

**步骤 1.3**: 创建测试助手包

```go
// internal/test/helpers.go

package test

import (
    "context"
    "github.com/gin-gonic/gin"
    "github.com/stretchr/testify/require"
    "testing"
)

// NewTestContext 创建测试 Gin 上下文
func NewTestContext(t *testing.T) *gin.Context {
    gin.SetMode(gin.TestMode)
    ctx, _ := gin.CreateTestContext(&bytes.Buffer{})
    return ctx
}

// NewTestRedis 创建测试 Redis 实例 (使用 testcontainers)
func NewTestRedis(ctx context.Context, t *testing.T) (*redis.Client, func()) {
    // ... 使用 testcontainers
}

// NewMockAgentClient 创建 mock gRPC 客户端
func NewMockAgentClient() *MockAgentClient {
    // ...
}
```

#### Phase 2: P0 测试 - 关键路径 (Week 2-4)

**2.1 Chat Orchestrator 测试** (40% 覆盖)

```go
// internal/handler/chat_orchestrator_test.go

func TestChatOrchestrator_WebSocketUpgrade(t *testing.T) {
    // 1. WebSocket 升级成功
    // 2. 无效的 Origin 拒绝
    // 3. 无效的 JWT 拒绝
}

func TestChatOrchestrator_ProcessMessage(t *testing.T) {
    // 1. 有效消息处理
    // 2. 空消息拒绝
    // 3. 恶意 HTML 消毒
    // 4. 消息持久化
}

func TestChatOrchestrator_HandleGRPCStream(t *testing.T) {
    // 1. 流完成时正确处理
    // 2. 流错误时重试
    // 3. 并发消息处理
}

func TestChatOrchestrator_ObjectPooling(t *testing.T) {
    // 1. 对象池重用
    // 2. 并发池访问
}
```

**2.2 gRPC Client 测试** (60% 覆盖)

```go
// internal/agent/client_test.go

func TestNewClient_Success(t *testing.T) {
    // 1. 明文连接
    // 2. TLS 连接
}

func TestClient_Chat_Success(t *testing.T) {
    // 1. 流式聊天成功
    // 2. 消息往返
}

func TestClient_Chat_Error(t *testing.T) {
    // 1. 连接失败
    // 2. 流错误处理
    // 3. 上下文超时
}
```

**2.3 CQRS Outbox/Publisher 测试** (50% 覆盖)

```go
// internal/cqrs/outbox/publisher_test.go

func TestPublisher_PublishEvent(t *testing.T) {
    // 1. 事件发布到 Outbox
    // 2. Redis 流推送
}

func TestPublisher_BatchProcessing(t *testing.T) {
    // 1. 批量轮询
    // 2. DLQ 创建失败事件
}

func TestPublisher_Idempotency(t *testing.T) {
    // 1. 重复事件检测
    // 2. 同样事件只处理一次
}
```

#### Phase 3: P1 测试 - 业务逻辑 (Week 4-6)

**3.1 认证中间件** (70% 覆盖)

```go
// internal/middleware/auth_test.go

func TestJWTValidation(t *testing.T) {
    // 1. 有效 JWT 接受
    // 2. 过期 JWT 拒绝
    // 3. Bearer token 和查询参数
}

func TestOriginCheck(t *testing.T) {
    // 1. 允许的 Origin 接受
    // 2. 不允许的 Origin 拒绝
    // 3. 通配符域匹配
}
```

**3.2 服务层** (60% 覆盖)

```go
// internal/service/quota_test.go
// internal/service/chat_history_test.go
// internal/service/semantic_cache_test.go

func TestQuotaService_Decrement(t *testing.T) {
    // 1. 额度扣除
    // 2. 熔断器
}

func TestChatHistory_Get(t *testing.T) {
    // 1. 命中缓存
    // 2. 缓存过期
}
```

**3.3 Workers** (50% 覆盖)

```go
// internal/worker/community_sync_test.go
// internal/worker/task_sync_test.go
// internal/worker/galaxy_sync_test.go

func TestCommunitySync_ProcessEvent(t *testing.T) {
    // 1. 事件处理
    // 2. 视图模型更新
    // 3. 数据库错误处理
}
```

#### Phase 4: 集成测试 (Week 6-7)

```go
// integration/websocket_integration_test.go

func TestWebSocketChatFlow(t *testing.T) {
    // 1. WebSocket 连接
    // 2. 发送消息
    // 3. 接收响应
    // 4. 连接关闭
}

// integration/cqrs_integration_test.go

func TestCQRSEventFlow(t *testing.T) {
    // 1. 命令 → Outbox
    // 2. Stream 推送
    // 3. Worker 处理
    // 4. Projection 更新
}

// integration/grpc_integration_test.go

func TestGRPCIntegration(t *testing.T) {
    // 需要实际 Python gRPC 服务器或 mock
}
```

#### Phase 5: CI/CD 集成 (Week 7)

```bash
# Makefile 添加
test:
	cd backend/gateway && go test -v ./... -race

test-coverage:
	cd backend/gateway && go test -v ./... -race -coverprofile=coverage.out
	go tool cover -html=coverage.out

lint:
	cd backend/gateway && golangci-lint run

ci: lint test test-coverage
```

### 覆盖目标

- **关键路径 (P0)**: 80%+
- **业务逻辑 (P1)**: 70%+
- **工具函数 (P2)**: 60%+
- **总体目标**: 75%+

### 验收标准

- [ ] 所有 P0 测试文件已创建
- [ ] P0 测试覆盖 ≥ 80%
- [ ] P1 测试覆盖 ≥ 70%
- [ ] 所有测试通过 (go test ./...)
- [ ] 竞态条件检测通过 (-race)
- [ ] CI/CD 集成完成
- [ ] 测试覆盖率报告生成

---

## 4️⃣ Access Control 集成

### 现状分析

**位置**: `backend/app/core/access_control.py`
**状态**: 代码存在但未使用
**导入位置**: `backend/app/api/v1/router.py` (已导入，未使用)
**依赖**: 取决于 idempotency 等 P1 项完成

### 实施计划

#### Phase 1: 审查和验证 (Week 1)

**步骤 1.1**: 理解当前实现

```bash
# 检查 access_control.py 的功能
grep -A 20 "def verify_token" backend/app/core/access_control.py
grep -A 20 "class AccessControl" backend/app/core/access_control.py
```

**步骤 1.2**: 识别应该使用访问控制的端点

```bash
# 在 router.py 中找出敏感端点
grep -n "@router" backend/app/api/v1/router.py | head -30
```

**步骤 1.3**: 检查 JWT 令牌内容

```python
# 令牌应包含:
# - user_id (sub claim)
# - role (可选)
# - permissions (可选)
# - scope (可选)
```

#### Phase 2: 端点保护 (Week 1-2)

**步骤 2.1**: 添加装饰器到敏感端点

```python
# backend/app/api/v1/routes/chat.py

from app.core.access_control import verify_token

@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(verify_token),  # 添加这一行
):
    # 只有认证用户可以访问
    pass
```

**步骤 2.2**: 添加基于角色的访问控制 (RBAC)

```python
# 如果系统需要不同的用户角色

@router.post("/admin/settings")
async def update_admin_settings(
    request: AdminSettingsRequest,
    current_user: User = Depends(verify_token),
    _admin = Depends(require_admin),  # 新增
):
    pass

# 在 access_control.py 中定义角色检查
async def require_admin(current_user: User) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
```

#### Phase 3: 多租户支持 (Week 2-3, 可选)

```python
# 如果系统支持多租户或团队

async def verify_resource_access(
    resource_id: str,
    current_user: User = Depends(verify_token),
):
    # 验证用户有权访问此资源
    resource = await db.get_resource(resource_id)
    if resource.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return resource
```

#### Phase 4: 测试 (Week 3-4)

```python
# backend/tests/test_access_control.py

def test_verify_token_valid():
    # 有效令牌应返回用户
    pass

def test_verify_token_invalid():
    # 无效令牌应抛出异常
    pass

def test_require_admin_success():
    # 管理员用户应通过检查
    pass

def test_require_admin_failure():
    # 非管理员用户应被拒绝
    pass

def test_resource_access():
    # 用户只能访问自己的资源
    pass
```

### 验收标准

- [ ] access_control.py 功能已验证
- [ ] 所有敏感端点已添加 verify_token
- [ ] RBAC 已实现 (如需要)
- [ ] 所有访问控制测试通过
- [ ] 文档已更新

---

## 5️⃣ Python 依赖统一 (Dependency Unification)

### 现状分析

**两套依赖管理系统**:
1. `backend/pyproject.toml` - Modern (Poetry/Pip)
2. `backend/requirements.txt` - Legacy

**问题**: 维护两套系统容易导致版本不一致

### 整合计划

#### Phase 1: 审查和选择 (30 min)

**步骤 1.1**: 比较两个文件

```bash
# 查看 pyproject.toml
cat backend/pyproject.toml | grep -A 50 "\[project\]" | grep "dependencies"

# 查看 requirements.txt
cat backend/requirements.txt | head -30
```

**步骤 1.2**: 确定哪个是来源

```bash
# 检查 pyproject.toml 的日期
grep "date" backend/pyproject.toml

# 检查 requirements.txt 的日期
ls -la backend/requirements.txt
```

#### Phase 2: 整合到单一来源 (1-2 小时)

**建议**: 使用 `pyproject.toml` (更现代)

**步骤 2.1**: 确保 pyproject.toml 完整

```toml
# backend/pyproject.toml

[project]
name = "sparkle"
version = "0.3.0"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
    "sqlalchemy>=2.0.0",
    "psycopg2-binary>=2.9.0",
    "pgvector>=0.1.0",
    "redis>=5.0.0",
    "grpcio>=1.59.0",
    "grpcio-tools>=1.59.0",
    # ... 所有其他依赖
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    # ... 所有开发依赖
]
```

**步骤 2.2**: 从 requirements.txt 提取任何遗漏的依赖

```bash
# 比较两个文件
comm -23 <(sort requirements.txt) <(grep "^\s*\"" pyproject.toml | grep -o '"[^"]*"' | tr -d '"' | sort)
```

**步骤 2.3**: 删除 requirements.txt

```bash
# 创建备份
cp backend/requirements.txt backend/requirements.txt.bak

# 删除文件
rm backend/requirements.txt
```

**步骤 2.4**: 更新 CI/CD

```yaml
# docker-compose.yml 或 CI/CD 配置
# FROM: pip install -r requirements.txt
# TO: pip install -e .[dev]  (if using pyproject.toml)
#  或 pip install -e .       (仅生产依赖)
```

#### Phase 3: 验证 (1 小时)

```bash
# 安装依赖
pip install -e backend/.[dev]

# 运行测试
pytest backend/tests/

# 检查导入
python -c "import fastapi, sqlalchemy, redis; print('All imports OK')"
```

### 验收标准

- [ ] pyproject.toml 包含所有依赖
- [ ] requirements.txt 已删除 (或存档)
- [ ] CI/CD 配置已更新
- [ ] 所有依赖安装正确
- [ ] 测试通过

---

## 📊 总体计划时间表

| 项目 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | 总计 |
|------|---------|---------|---------|---------|---------|------|
| 1. 设计系统 | 2w | 2w | 2w | 1w | 1w | **8 周** |
| 2. 依赖整理 | 1.5h | - | - | - | - | **1.5 h** |
| 3. Gateway 测试 | 2w | 2w | 2w | 1w | 1w | **8 周** |
| 4. Access Control | 1w | 1w | 1w | 1w | - | **4 周** |
| 5. Python 依赖 | 0.5h | 1h | 1h | - | - | **2.5 h** |
| **总计** | - | - | - | - | - | **~22 周** |

**并行执行推荐**:
- Week 1-2: 设计系统 Phase 1 + 依赖整理 + Python 依赖
- Week 2-4: 设计系统 Phase 2 + Gateway 测试 Phase 1
- Week 4-6: 设计系统 Phase 3 + Gateway 测试 Phase 2 + Access Control Phase 1
- Week 6-8: 设计系统 Phase 4-5 + Gateway 测试 Phase 3 + Access Control Phase 2
- Week 8-10: Gateway 测试 Phase 4-5 + Access Control Phase 3-4
- Week 10-12: 集成测试和文档

**实际时间**: 约 **10-12 周**（并行执行）

---

## 🎯 优先级建议

### 推荐执行顺序

1. **立即开始** (Week 1):
   - 依赖整理 (快, 高价值)
   - Python 依赖统一 (快, 技术债)
   - 设计系统分析 (准备阶段)

2. **第 2-4 周**:
   - 设计系统整合 (高影响, 中等复杂度)
   - Gateway 测试基础设施 (准备)

3. **第 5-8 周**:
   - Gateway 测试实现 (高复杂度, 关键)
   - Access Control 集成 (中等复杂度)

4. **第 9-12 周**:
   - 集成测试和文档
   - CI/CD 增强

---

## 📋 检查清单

### 快速开始

- [ ] 依赖整理 (2-3 天)
- [ ] Python 依赖统一 (0.5-1 天)
- [ ] 设计系统命名冲突解决 (3-5 天)

### 中期目标 (4-6 周)

- [ ] 设计系统完全整合
- [ ] Gateway 基本测试框架
- [ ] Access Control 初步集成

### 最终目标 (8-12 周)

- [ ] 所有 P2 项完成
- [ ] Gateway 测试覆盖 75%+
- [ ] 系统文档更新
- [ ] CI/CD 完全集成

---

**下一步**: 选择优先项开始实施
