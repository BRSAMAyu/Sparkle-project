# Phase 6: 可观测、报告与体验精磨 — "数据驱动的体验进化"

> **交给Coding Agent执行的完整指令**
> **预计改动**: 3个新文件, 5个修改文件 (Flutter + Python后端)
> **依赖**: Phase 1-5 已完成

---

## 背景

Phase 1-5 建立了完整的执行体验链路。本阶段解决最后三个维度:
1. **用户可见的执行报告**: 让用户知道AI执行为他节省了多少时间
2. **管理端可观测**: 确保系统健康、A/B实验有数据
3. **体验精磨**: 文案体系、无障碍、边缘case处理

### 关键现有代码

- `learning_report_screen.dart` (mobile) — 学习报告页, 需要增加执行板块
- `ExecutionQualityService` (backend) — A/B实验框架
- `ExecutionProfileService` (Phase 3创建) — 执行画像聚合
- `execution_profile_service.py` API endpoint (Phase 3创建) — /executions/profile/summary

---

## 任务 6.1: Flutter — 学习报告中增加"AI执行助手"板块

**修改文件**: `mobile/lib/features/report/presentation/screens/learning_report_screen.dart`

### 修改目标

在学习报告页中新增一个板块, 展示用户的AI执行统计。

### 精确修改

#### 1. 添加数据获取

在报告页的数据获取逻辑中(找到页面加载数据的位置, 通常在initState或provider中), 添加执行画像数据的获取:

```dart
// 添加API调用
Future<Map<String, dynamic>?> _loadExecutionProfile() async {
  try {
    final response = await apiClient.get(ApiEndpoints.executionProfileSummary);
    if (response.statusCode == 200) {
      return response.data as Map<String, dynamic>;
    }
  } catch (_) {}
  return null;
}
```

需要在 `api_endpoints.dart` 中添加(如果Phase 3未添加):
```dart
static String get executionProfileSummary => '/executions/profile/summary';
```

#### 2. 创建执行统计卡片widget

在同文件或提取为独立widget:

```dart
class _ExecutionStatsSection extends StatelessWidget {
  final Map<String, dynamic> profile;

  const _ExecutionStatsSection({required this.profile});

  @override
  Widget build(BuildContext context) {
    final totalExecutions = profile['total_executions'] as int? ?? 0;
    final successRate = profile['success_rate'] as double? ?? 0.0;
    final timeSaved = profile['estimated_time_saved_minutes'] as double? ?? 0.0;
    final byType = profile['by_type'] as Map<String, dynamic>? ?? {};

    if (totalExecutions == 0) {
      return const SizedBox.shrink(); // 没有执行记录时不显示
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 板块标题
        Padding(
          padding: const EdgeInsets.only(bottom: DS.spacing12),
          child: Row(
            children: [
              Icon(Icons.smart_toy_rounded, size: 20, color: DS.brandPrimary),
              const SizedBox(width: DS.spacing8),
              Text(
                'AI执行助手',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: DS.textPrimary,
                ),
              ),
            ],
          ),
        ),

        // 统计行 — 三个指标并排
        Row(
          children: [
            _StatCard(
              label: '总执行',
              value: '$totalExecutions',
              unit: '次',
              color: DS.info,
            ),
            const SizedBox(width: DS.spacing8),
            _StatCard(
              label: '成功率',
              value: '${(successRate * 100).round()}',
              unit: '%',
              color: DS.semanticSuccess,
            ),
            const SizedBox(width: DS.spacing8),
            _StatCard(
              label: '节省时间',
              value: timeSaved >= 60
                  ? '${(timeSaved / 60).toStringAsFixed(1)}'
                  : '${timeSaved.round()}',
              unit: timeSaved >= 60 ? '小时' : '分钟',
              color: DS.brandPrimary,
            ),
          ],
        ),

        // 按类型分布 (仅当有多种类型时显示)
        if (byType.length > 1) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            '执行类型分布',
            style: TextStyle(fontSize: 13, color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing6,
            children: byType.entries.map((entry) {
              final type = entry.key;
              final data = entry.value as Map<String, dynamic>;
              final count = data['count'] as int? ?? 0;
              return Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing10,
                  vertical: DS.spacing4,
                ),
                decoration: BoxDecoration(
                  color: DS.surfaceSecondary,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '$type: ${count}次',
                  style: TextStyle(fontSize: 12, color: DS.textSecondary),
                ),
              );
            }).toList(),
          ),
        ],
      ],
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final String unit;
  final Color color;

  const _StatCard({
    required this.label,
    required this.value,
    required this.unit,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: color.withOpacity(0.08),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: TextStyle(fontSize: 11, color: DS.textTertiary),
            ),
            const SizedBox(height: DS.spacing4),
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  value,
                  style: TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                    color: color,
                    fontFeatures: const [FontFeature.tabularFigures()],
                  ),
                ),
                const SizedBox(width: 2),
                Padding(
                  padding: const EdgeInsets.only(bottom: 3),
                  child: Text(
                    unit,
                    style: TextStyle(fontSize: 12, color: color.withOpacity(0.7)),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
```

#### 3. 在报告页布局中插入板块

找到报告页的主体内容列表(通常是一个Column或ListView), 在适当位置(建议在"学习统计"板块之后)插入:

```dart
// AI执行助手板块
if (executionProfile != null)
  Padding(
    padding: const EdgeInsets.only(top: DS.spacing20),
    child: SparkleStaggerItem(
      index: 3,  // 根据实际stagger index调整
      child: _ExecutionStatsSection(profile: executionProfile),
    ),
  ),
```

---

## 任务 6.2: 后端 — 管理端执行Dashboard数据

**修改文件**: `backend/app/api/v1/executions_admin.py`

### 修改目标

丰富admin API, 提供Dashboard所需的聚合数据。

### 精确修改

在现有endpoint(health/nodes/quality/summary)后面, 添加:

```python
@router.get("/dashboard")
async def get_execution_dashboard(
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_async_session),
    days: int = 7,
):
    """Get execution system dashboard metrics."""
    from datetime import datetime, timedelta
    from sqlalchemy import select, func, and_, case
    from app.models.execution_intent import ExecutionIntent
    from app.models.execution_record import ExecutionRecord

    since = datetime.utcnow() - timedelta(days=min(days, 90))

    # 1. 总体指标
    total_stmt = select(
        func.count().label("total"),
        func.sum(case((ExecutionIntent.status == "SUCCEEDED", 1), else_=0)).label("succeeded"),
        func.sum(case((ExecutionIntent.status == "FAILED", 1), else_=0)).label("failed"),
        func.sum(case((ExecutionIntent.status == "HANDED_BACK", 1), else_=0)).label("handed_back"),
        func.sum(case((ExecutionIntent.status == "CANCELED", 1), else_=0)).label("canceled"),
        func.sum(case((ExecutionIntent.status == "TIMED_OUT", 1), else_=0)).label("timed_out"),
    ).where(
        and_(
            ExecutionIntent.created_at >= since,
            ExecutionIntent.deleted_at.is_(None),
        )
    )
    total_result = await db.execute(total_stmt)
    total = total_result.one()

    # 2. 信任分布
    trust_stmt = select(
        ExecutionIntent.trust_level,
        func.count().label("cnt"),
    ).where(
        and_(
            ExecutionIntent.created_at >= since,
            ExecutionIntent.deleted_at.is_(None),
        )
    ).group_by(ExecutionIntent.trust_level)
    trust_result = await db.execute(trust_stmt)
    trust_dist = {row.trust_level: row.cnt for row in trust_result.all()}

    # 3. 按模板统计
    template_stmt = select(
        ExecutionIntent.policy["template_id"].astext.label("template_id"),
        func.count().label("cnt"),
        func.sum(case((ExecutionIntent.status == "SUCCEEDED", 1), else_=0)).label("succeeded"),
    ).where(
        and_(
            ExecutionIntent.created_at >= since,
            ExecutionIntent.deleted_at.is_(None),
            ExecutionIntent.policy["template_id"].isnot(None),
        )
    ).group_by("template_id")

    try:
        template_result = await db.execute(template_stmt)
        by_template = [
            {
                "template_id": row.template_id,
                "count": row.cnt,
                "success_rate": (row.succeeded or 0) / row.cnt if row.cnt > 0 else 0,
            }
            for row in template_result.all()
        ]
    except Exception:
        by_template = []

    # 4. 平均耗时
    duration_stmt = select(
        func.avg(ExecutionRecord.duration_ms).label("avg"),
        func.min(ExecutionRecord.duration_ms).label("min"),
        func.max(ExecutionRecord.duration_ms).label("max"),
    ).join(
        ExecutionIntent, ExecutionRecord.execution_intent_id == ExecutionIntent.id
    ).where(
        and_(
            ExecutionIntent.created_at >= since,
            ExecutionIntent.deleted_at.is_(None),
            ExecutionRecord.duration_ms.isnot(None),
        )
    )
    duration_result = await db.execute(duration_stmt)
    duration = duration_result.one()

    # 5. 活跃用户数
    users_stmt = select(
        func.count(func.distinct(ExecutionIntent.user_id)).label("cnt"),
    ).where(
        and_(
            ExecutionIntent.created_at >= since,
            ExecutionIntent.deleted_at.is_(None),
        )
    )
    users_result = await db.execute(users_stmt)
    active_users = users_result.scalar() or 0

    return {
        "period_days": days,
        "total_executions": total.total or 0,
        "status_distribution": {
            "succeeded": total.succeeded or 0,
            "failed": total.failed or 0,
            "handed_back": total.handed_back or 0,
            "canceled": total.canceled or 0,
            "timed_out": total.timed_out or 0,
        },
        "success_rate": (total.succeeded or 0) / total.total if total.total else 0,
        "trust_distribution": trust_dist,
        "by_template": by_template,
        "duration_ms": {
            "avg": duration.avg,
            "min": duration.min,
            "max": duration.max,
        },
        "active_users": active_users,
    }
```

---

## 任务 6.3: 后端 — 执行异常自动降级

**修改文件**: `backend/app/services/execution_service.py`

### 修改目标

当连续失败时, 自动降级为HUMAN模式, 保护用户体验。

### 精确修改

#### 1. 添加降级状态跟踪

在 `ExecutionService.__init__` 中添加:

```python
# Phase 6: 降级跟踪
self._failure_counts: dict[str, int] = {}  # user_id → consecutive failures
self._degraded_users: set[str] = set()
self._degradation_threshold = 3  # 连续3次失败触发降级
self._degradation_recovery_threshold = 1  # 1次成功恢复
```

#### 2. 在dispatch结果处理后更新计数

找到 `dispatch()` 方法中处理执行结果的位置(成功/失败分支), 添加:

```python
# Phase 6: 降级跟踪
user_key = str(intent.user_id)
if intent.status in ("FAILED", "TIMED_OUT"):
    self._failure_counts[user_key] = self._failure_counts.get(user_key, 0) + 1
    if self._failure_counts[user_key] >= self._degradation_threshold:
        self._degraded_users.add(user_key)
        import logging
        logging.getLogger(__name__).warning(
            f"User {user_key} degraded to HUMAN mode after {self._failure_counts[user_key]} consecutive failures"
        )
elif intent.status == "SUCCEEDED":
    if user_key in self._failure_counts:
        self._failure_counts[user_key] = 0
    if user_key in self._degraded_users:
        self._degraded_users.discard(user_key)
        import logging
        logging.getLogger(__name__).info(f"User {user_key} recovered from degraded mode")
```

#### 3. 在classify_task中检查降级

在 `classify_task()` 方法的开头(缓存检查之后), 添加:

```python
# Phase 6: 降级检查
user_key = str(user_id)
if user_key in self._degraded_users:
    from app.core.execution_router import RoutingDecision, ExecutionMode
    return RoutingDecision(
        mode=ExecutionMode.HUMAN,
        reason="Auto-degraded due to consecutive execution failures. Manual mode recommended.",
        confidence=1.0,
    )
```

**注意**: 需要确认 `RoutingDecision` 的实际构造函数签名, 适配参数名。

---

## 任务 6.4: Flutter — 执行文案体系

**创建文件**: `mobile/lib/features/task/data/execution_copy.dart`

### 设计规格

集中管理所有执行相关的用户面文案, 确保语气与Sparkle"温暖理性"品牌一致。

```dart
/// Centralized copy for execution UI — ensures consistent "warm + rational" tone.
class ExecutionCopy {
  ExecutionCopy._();

  // ─── 状态标题 ───

  static String statusTitle(String status) => switch (status) {
    'draft' => '准备中',
    'ready' => '就绪',
    'dispatched' => '已发送给AI',
    'running' => 'AI正在执行',
    'waitingApproval' => '等待你的确认',
    'succeeded' => '执行完成',
    'partial' => '部分完成',
    'failed' => '执行遇到问题',
    'canceled' => '已取消',
    'timedOut' => '执行超时',
    'handedBack' => '已取回',
    _ => '未知状态',
  };

  // ─── 状态副标题 (更详细的说明) ───

  static String statusSubtitle(String status, {bool isFirstExecution = false}) => switch (status) {
    'dispatched' => isFirstExecution
        ? 'AI正在准备执行，第一次可能需要几秒钟'
        : 'AI正在准备执行',
    'running' => '正在自动完成任务，你可以随时取回',
    'waitingApproval' => 'AI已完成执行，请查看结果并决定是否采纳',
    'succeeded' => '结果已自动应用到你的任务中',
    'partial' => 'AI完成了部分工作，你可以在此基础上继续',
    'failed' => '别担心，你可以稍后重试或自己完成',
    'timedOut' => '执行时间过长，建议分解为更小的步骤',
    'handedBack' => '已回到你手中，可以随时再次委派',
    _ => '',
  };

  // ─── 按钮文案 ───

  static String handoffButton({String? templateName, bool hasActiveExecution = false}) {
    if (hasActiveExecution) return '查看执行状态';
    if (templateName != null) return '用"$templateName"执行';
    return '交给AI执行';
  }

  static const confirmButton = '采纳结果';
  static const rejectButton = '退回修改';
  static const cancelButton = '取消执行';
  static const handbackButton = '取回任务';
  static const retryButton = '重新执行';

  // ─── 提示文案 ───

  static const noTemplateMatch = '这个任务更适合你亲自完成';
  static const noTemplateMatchDetail = '当前没有匹配的执行模板，但你总是可以自己高效地完成它';

  static const connectionOffline = 'AI执行引擎离线';
  static const connectionOfflineDetail = '点击设置连接';

  static const degradedMode = 'AI执行暂时不可用';
  static const degradedModeDetail = '由于多次执行未成功，系统建议你手动完成当前任务';

  // ─── 拒绝理由预设 ───

  static const rejectReasons = [
    '结果不够准确',
    '信息不完整',
    '有安全顾虑',
    '我想自己完成',
  ];

  static const rejectSheetTitle = '退回原因';
  static const rejectSheetSubtitle = '帮助AI下次做得更好';
  static const rejectConfirmButton = '确认退回';

  // ─── 执行建议 (聊天流内) ───

  static const suggestionTitle = '我可以帮你自动完成这个任务';
  static const suggestionHybridNote = '执行完成后需要你确认结果';
  static const suggestionAccept = '交给AI';
  static const suggestionDismiss = '我自己来';

  // ─── 报告板块 ───

  static const reportSectionTitle = 'AI执行助手';
  static const reportTotalLabel = '总执行';
  static const reportSuccessLabel = '成功率';
  static const reportTimeSavedLabel = '节省时间';

  // ─── 模板描述 (补充, 如果后端未提供中文描述) ───

  static String templateDescription(String templateId) => switch (templateId) {
    'web_research_brief' => '自动搜索和整理网页信息',
    'document_digest' => '自动提取和总结文档要点',
    'shell_diagnostics' => '自动执行诊断命令',
    'browser_form_prepare' => 'AI准备表单草稿, 你确认后提交',
    'cross_device_capture' => '协调多设备完成信息采集',
    _ => '',
  };

  // ─── 信任等级 ───

  static String trustLabel(String level) => switch (level) {
    'RAW' || 'raw' => '待验证',
    'VALIDATED' || 'validated' => '已验证',
    'TRUSTED' || 'trusted' => '已信任',
    _ => '未知',
  };
}
```

### 集成到现有代码

在Phase 1创建的所有widget中, 将硬编码的中文字符串替换为 `ExecutionCopy.xxx` 调用:

- `execution_status_indicator.dart` → 使用 `ExecutionCopy.statusTitle()`
- `execution_approval_card.dart` → 使用 `ExecutionCopy.confirmButton`, `ExecutionCopy.rejectButton`
- `execution_template_card.dart` → 使用 `ExecutionCopy.templateDescription()`
- `execution_suggestion_card.dart` (Phase 2) → 使用 `ExecutionCopy.suggestionTitle` 等
- `task_execution_screen.dart` 的 `_RejectReasonSheet` → 使用 `ExecutionCopy.rejectReasons` 等
- `_BottomControls` 中的 `_executionStatusTitle`, `_executionStatusSubtitle` → 委托给 `ExecutionCopy`

---

## 任务 6.5: Flutter — 无障碍完善

**修改文件**: Phase 1-5 创建的所有执行相关widget

### 修改清单

逐一在以下组件添加 `Semantics` 标签:

#### execution_status_indicator.dart
```dart
Semantics(
  label: '执行状态: ${ExecutionCopy.statusTitle(status.name)}',
  child: // ... existing widget
)
```

#### execution_approval_card.dart
```dart
// 确认按钮
Semantics(
  button: true,
  label: '采纳AI执行结果',
  child: // ... confirm button
)

// 拒绝按钮
Semantics(
  button: true,
  label: '退回AI执行结果',
  child: // ... reject button
)
```

#### execution_template_card.dart
```dart
Semantics(
  selected: isSelected,
  label: '执行模板: ${template.name}, 匹配度${(template.matchScore * 100).round()}%, ${template.modeLabel}模式',
  child: // ... card
)
```

#### execution_suggestion_card.dart
```dart
Semantics(
  label: 'AI建议: ${ExecutionCopy.suggestionTitle}',
  child: // ... card
)
```

#### 动画降级

确认所有widget中使用 `SparkleAttentionPulse`、旋转动画等的地方, 都检查了 `MediaQuery.of(context).disableAnimations`:

```dart
final reduceMotion = MediaQuery.of(context).disableAnimations;

// 在使用动画时
if (reduceMotion) {
  // 简单的静态展示
} else {
  // 完整动画
}
```

---

## 任务 6.6: 后端 — 执行事件日志

**修改文件**: `backend/app/services/execution_service.py`

### 修改目标

在关键执行节点增加结构化日志, 便于排查问题和统计。

### 精确修改

在文件顶部的import区添加:
```python
import logging
import time

logger = logging.getLogger("sparkle.execution")
```

在以下位置添加结构化日志:

#### handoff_to_openclaw() — 入口
```python
logger.info(
    "execution.handoff_start",
    extra={
        "user_id": str(user_id),
        "task_id": str(task_id),
        "template_id": template_id,
        "goal_length": len(goal) if goal else 0,
    },
)
```

#### dispatch() — 发送给OpenClaw前后
```python
# 发送前
start_time = time.monotonic()
logger.info(
    "execution.dispatch_start",
    extra={
        "intent_id": str(intent.id),
        "transport": self._config.transport,
    },
)

# 发送后
elapsed_ms = int((time.monotonic() - start_time) * 1000)
logger.info(
    "execution.dispatch_complete",
    extra={
        "intent_id": str(intent.id),
        "status": intent.status,
        "elapsed_ms": elapsed_ms,
    },
)
```

#### classify_task() — 缓存命中/未命中
```python
# 缓存命中
logger.debug(
    "execution.classify_cache_hit",
    extra={"cache_key": cache_key, "task_id": str(task_id)},
)

# 缓存未命中
logger.debug(
    "execution.classify_cache_miss",
    extra={"cache_key": cache_key, "task_id": str(task_id)},
)
```

#### 降级触发/恢复
```python
# 降级
logger.warning(
    "execution.degradation_triggered",
    extra={
        "user_id": user_key,
        "consecutive_failures": self._failure_counts[user_key],
    },
)

# 恢复
logger.info(
    "execution.degradation_recovered",
    extra={"user_id": user_key},
)
```

---

## 验收标准

### Flutter验收

```bash
cd mobile && flutter analyze --no-fatal-infos
```

### 后端验收

```bash
cd backend && python -m pytest tests/ -x -q
```

### 功能验收 (人工)

1. [ ] 学习报告页: 有执行记录时显示"AI执行助手"板块, 总执行/成功率/节省时间三指标卡片
2. [ ] 学习报告页: 无执行记录时板块不显示
3. [ ] Admin GET /admin/executions/dashboard 返回完整的聚合指标
4. [ ] 连续3次执行失败后, classify返回HUMAN模式
5. [ ] 1次成功后自动恢复
6. [ ] 所有执行相关文案统一使用ExecutionCopy, 无硬编码散落
7. [ ] VoiceOver/TalkBack能正确读出: 状态指示器、审批按钮、模板卡片、建议卡
8. [ ] reduceMotion开启时, 所有动画降级为简单opacity过渡
9. [ ] 后端日志中包含结构化的execution.*事件

### 全链路端到端验证

完成所有Phase后, 验证以下完整用户旅程:

**旅程1: 首次委派**
1. 用户在设置中配置OpenClaw连接 → 显示"已连接"
2. 进入任务详情 → 看到模板推荐卡片
3. 选择模板 → 点击"交给AI执行" → 状态指示器脉冲动画
4. 等待执行完成 → 状态变为waitingApproval → 强脉冲动画+warning音效
5. 查看审批卡: 格式化结果预览+质量警告(如果有)
6. 点击"采纳结果" → confetti+success音效 → 任务标记完成
7. 查看学习报告 → AI执行助手板块显示1次执行

**旅程2: 对话中委派**
1. 在聊天中输入"帮我查一下xxx"
2. AI回复后, 下方出现执行建议卡
3. 点击"交给AI" → 自动发起handoff
4. 执行完成后, 聊天流中内联显示结果
5. 结果以markdown/结构化格式展示

**旅程3: 失败恢复**
1. 执行失败 → 红色状态+shake动画+error音效
2. 显示"别担心, 你可以稍后重试或自己完成"
3. 连续3次失败 → handoff按钮禁用+显示"AI执行暂时不可用"
4. 手动完成一个任务 → 或等待一次成功 → 恢复正常

**旅程4: 离线/断连**
1. 断开OpenClaw → handoff按钮禁用+显示"AI执行引擎离线, 点击设置"
2. 点击跳转到设置页 → 重新连接 → 回到任务页 → 按钮恢复
