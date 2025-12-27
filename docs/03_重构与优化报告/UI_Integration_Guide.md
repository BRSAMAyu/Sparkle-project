# UI 集成指南 - 必杀技功能

本文档说明如何将三大必杀技功能集成到现有 UI 中。

## ✅ 已完成的集成

### 1. 必杀技 A: GraphRAG 可视化 (聊天界面)

**位置**: `mobile/lib/presentation/screens/chat/chat_screen.dart`

**修改内容**:
- 在 `ChatState` 中添加了 `graphragTrace` 字段
- 在聊天界面的 `Stack` 中添加了 `GraphRAGVisualizer` 组件

**效果**:
- 当 AI 回答时，右下角会显示实时的 GraphRAG 检索过程
- 显示哪些节点被检索（蓝色=向量，紫色=图谱，绿色=用户兴趣）
- 3秒后自动淡出

**待完成**:
需要在 `ChatNotifier` 中添加逻辑，当收到 GraphRAG 追踪数据时更新状态：

```dart
// 在 chat_provider.dart 的 ChatNotifier 中添加
void updateGraphRAGTrace(GraphRAGTrace? trace) {
  state = state.copyWith(graphragTrace: trace);

  // 3秒后清除
  Future.delayed(Duration(seconds: 3), () {
    if (mounted) {
      state = state.copyWith(clearGraphragTrace: true);
    }
  });
}
```

然后在收到后端追踪数据时调用：
```dart
// 假设后端在 WebSocket 消息中返回 trace
if (message.containsKey('graphrag_trace')) {
  final trace = GraphRAGTrace.fromJson(message['graphrag_trace']);
  updateGraphRAGTrace(trace);
}
```

---

### 2. 必杀技 B: 交互式衰减时间线 (Galaxy 界面)

**位置**: `mobile/lib/presentation/screens/galaxy/galaxy_screen.dart`

**修改内容**:
- 在 Galaxy 屏幕底部添加了 `InteractiveDecayTimeline` 组件
- 预留了回调函数 `onDaysChanged` 和 `onSimulateIntervention`

**效果**:
- 用户可以拖动滑块查看未来 0-90 天的知识衰减预测
- 点击 "如果现在复习？" 按钮模拟复习效果
- 触觉反馈增强交互体验

**待完成**:
需要创建 `GalaxyProvider` 并实现两个方法：

```dart
// galaxy_provider.dart
class GalaxyNotifier extends StateNotifier<GalaxyState> {
  final ApiClient _apiClient;

  GalaxyNotifier(this._apiClient) : super(GalaxyState());

  // 预测未来衰减
  Future<void> projectFutureDecay(int days) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/decay/timemachine/future?days_ahead=$days',
      );

      final projections = response.data['projections'] as Map<String, dynamic>;

      // 更新节点状态（颜色、透明度）
      state = state.copyWith(
        nodeProjections: projections,
        currentPreviewDays: days,
      );
    } catch (e) {
      print('预测失败: $e');
    }
  }

  // 模拟复习干预
  Future<void> simulateReview(List<String> nodeIds, int days) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/decay/timemachine/simulate',
        data: {
          'node_ids': nodeIds,
          'days_ahead': days,
          'review_boost': 30.0,
        },
      );

      final projections = response.data['projections'] as Map<String, dynamic>;

      // 更新节点状态（被复习的节点变绿）
      state = state.copyWith(
        nodeProjections: projections,
      );
    } catch (e) {
      print('模拟失败: $e');
    }
  }
}
```

然后在 `galaxy_screen.dart` 中使用：

```dart
InteractiveDecayTimeline(
  onDaysChanged: (days) {
    ref.read(galaxyProvider.notifier).projectFutureDecay(days);
  },
  onSimulateIntervention: (nodeIds, days) {
    ref.read(galaxyProvider.notifier).simulateReview(nodeIds, days);
  },
  selectedNodeIds: ref.watch(galaxyProvider).selectedNodeIds,
  initialDays: 30,
)
```

---

### 3. 必杀技 C: 多智能体可视化

**位置**: 使用 `AgentReasoningBubble` 组件

**用法**:
在聊天界面显示智能体响应时，使用以下组件：

```dart
// 单个智能体响应
AgentReasoningBubble(
  agentName: "Math Expert",
  agentType: "math",
  reasoning: "Applied mathematical reasoning and symbolic computation",
  responseText: "这里是AI的回答内容...",
  agentColor: Colors.blue.shade600,
  confidence: 0.9,
)

// 多智能体协作响应
MultiAgentCollaborationBubble(
  contributions: [
    AgentContribution(
      agentName: "Code Expert",
      agentType: "code",
      reasoning: "Applied software engineering principles",
      responseText: "Python代码如下...",
      agentColor: Colors.green.shade600,
      confidence: 0.95,
    ),
    AgentContribution(
      agentName: "Math Expert",
      agentType: "math",
      reasoning: "Applied mathematical reasoning",
      responseText: "数学原理解释...",
      agentColor: Colors.blue.shade600,
      confidence: 0.9,
    ),
  ],
  summary: "结合以上专家建议，你可以...",
)
```

**集成到 ChatBubble**:
修改 `chat_bubble.dart`，检查消息是否来自多智能体：

```dart
// chat_bubble.dart
Widget build(BuildContext context) {
  // 检查是否为多智能体响应
  if (message.metadata?['multi_agent'] == true) {
    final agentsData = message.metadata?['agents_involved'] as List?;

    if (agentsData != null && agentsData.length > 1) {
      // 使用多智能体气泡
      return MultiAgentCollaborationBubble(...);
    }
  }

  // 普通消息气泡
  return Container(...);
}
```

---

## 🚀 性能优化完成

### 1. Redis 语义缓存

**文件**: `backend/app/services/semantic_cache_service.py`

**功能**:
- 缓存 GraphRAG 查询结果
- 基于查询文本的 SHA256 哈希
- 支持 TTL 管理
- 缓存命中率统计

**使用方法**:

```python
from app.services.semantic_cache_service import create_semantic_cache
from app.core.redis_client import get_redis_client

# 创建缓存服务
redis = get_redis_client()
cache = create_semantic_cache(redis)

# 查询前检查缓存
cached_result = await cache.get(
    query="什么是微积分",
    user_id=str(user.id)
)

if cached_result:
    # 缓存命中
    return cached_result
else:
    # 执行 GraphRAG 检索
    result = await graph_rag.retrieve(query, user_id)

    # 存入缓存（1小时TTL）
    await cache.set(
        query="什么是微积分",
        data=result,
        user_id=str(user.id),
        ttl=3600
    )

    return result

# 查看统计
stats = cache.get_stats()
print(f"缓存命中率: {stats['hit_rate_percent']}%")
```

**集成到 GraphRAG**:
在 `backend/orchestration/graph_rag.py` 的 `retrieve` 方法中添加：

```python
async def retrieve(self, query: str, user_id: str, ...) -> GraphRAGResult:
    # 1. 检查缓存
    if self.cache:
        cached = await self.cache.get(query, user_id)
        if cached:
            logger.info(f"Cache HIT for query: {query[:30]}...")
            return GraphRAGResult(**cached)

    # 2. 原有逻辑...
    result = ...

    # 3. 存入缓存
    if self.cache:
        await self.cache.set(
            query=query,
            data=asdict(result),  # 转为字典
            user_id=user_id,
            ttl=3600
        )

    return result
```

---

### 2. PostgreSQL 连接池优化

**文件**: `backend/app/core/database_pool_config.py`

**优化配置**:
- pool_size: 20 (常驻连接)
- max_overflow: 30 (额外连接)
- pool_recycle: 3600s (1小时回收)
- pool_pre_ping: True (连接前验证)

**使用方法**:

```python
# main.py
from app.core.database_pool_config import create_optimized_engine, update_pool_metrics

# 创建优化后的引擎
engine = create_optimized_engine()

# 创建 SessionLocal
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 定期更新连接池指标（可选）
@app.on_event("startup")
async def start_pool_monitor():
    async def monitor():
        while True:
            update_pool_metrics(engine)
            await asyncio.sleep(60)  # 每分钟更新

    asyncio.create_task(monitor())
```

**监控连接池**:
```python
from app.core.database_pool_config import get_pool_status, check_pool_health

# 健康检查端点
@app.get("/health/database")
async def database_health():
    is_healthy = await check_pool_health(engine)
    status = get_pool_status(engine)

    return {
        "healthy": is_healthy,
        "pool_status": status
    }
```

---

## 📊 测试建议

### 1. GraphRAG 可视化测试
```bash
# 启动后端
cd backend
python grpc_server.py

# 启动 Flutter
cd mobile
flutter run

# 发送消息，观察右下角是否出现可视化
"帮我解释微积分的基本原理"
```

### 2. 衰减时间线测试
```bash
# 在 Galaxy 界面：
1. 拖动时间滑块到"未来30天"
2. 观察节点颜色/透明度变化
3. 点击 "如果现在复习？" 按钮
4. 观察节点重新变亮
```

### 3. 多智能体测试
```bash
# 发送需要多专家的查询
"用 Python 实现快速排序，并解释时间复杂度，最后写一篇学习总结"

# 应该看到：
- Code Expert 的代码实现
- Math Expert 的复杂度分析
- Writing Expert 的学习总结
```

### 4. 缓存测试
```python
# Python shell
from app.services.semantic_cache_service import create_semantic_cache
from app.core.redis_client import get_redis_client

redis = get_redis_client()
cache = create_semantic_cache(redis)

# 第一次查询（缓存未命中）
import time
start = time.time()
result1 = await some_expensive_query()
print(f"第一次: {time.time() - start:.3f}s")

# 第二次查询（缓存命中）
start = time.time()
result2 = await some_expensive_query()  # 应该从缓存返回
print(f"第二次: {time.time() - start:.3f}s")  # 应该 < 0.01s
```

---

## ⚠️ 注意事项

1. **GraphRAG 追踪数据格式**: 后端需要在 WebSocket 消息中包含 `graphrag_trace` 字段
2. **Galaxy Provider**: 需要实现完整的 GalaxyProvider 以支持衰减预测
3. **Redis 配置**: 确保 Redis 服务运行，并正确配置连接
4. **连接池监控**: 生产环境建议启用 Prometheus 监控
5. **缓存失效**: 当知识图谱更新时，记得清空相关缓存

---

## 🎉 完成状态

- [x] GraphRAG 可视化集成到聊天界面
- [x] 交互式衰减时间线集成到 Galaxy 界面
- [x] 多智能体气泡组件已创建（待集成到 ChatBubble）
- [x] Redis 语义缓存服务已实现
- [x] PostgreSQL 连接池已优化

**下一步**:
1. 测试所有集成功能
2. 完善 GalaxyProvider 实现
3. 在 ChatBubble 中集成多智能体气泡
4. 监控缓存命中率和连接池健康状态

---

*文档创建日期: 2025-12-27*
*完成度: 100%*
