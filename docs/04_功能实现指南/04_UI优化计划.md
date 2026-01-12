# Sparkle Flutter UI 优化完整实施计划

> **项目**: Sparkle (星火) - AI学习助手应用
> **目标**: 2025年2月2日前完成MVP，参加大学软件创新竞赛
> **文档版本**: v1.0
> **最后更新**: 2025年12月16日

---

## 📋 目录

- [项目背景](#项目背景)
- [设计愿景](#设计愿景)
- [已完成工作](#已完成工作)
- [实施计划](#实施计划)
  - [阶段一：设计系统基础建设](#阶段一设计系统基础建设)
  - [阶段二：基础组件库实现](#阶段二基础组件库实现)
  - [阶段三：核心页面优化](#阶段三核心页面优化)
  - [阶段四：动画和交互增强](#阶段四动画和交互增强)
  - [阶段五：细节打磨](#阶段五细节打磨)
- [时间估算](#时间估算)
- [团队分工建议](#团队分工建议)
- [关键文件清单](#关键文件清单)

---

## 项目背景

### 应用简介

Sparkle (星火) 是一个AI驱动的学习助手应用，专为大学生设计，通过"AI时间导师"概念帮助用户完成学习循环：对话 → 任务卡片 → 执行 → 反馈 → 冲刺计划。

### 技术栈

- **后端**: FastAPI + PostgreSQL/SQLite + SQLAlchemy 2.0
- **移动端**: Flutter 3.x + Riverpod + Dio
- **AI**: 通义千问 / DeepSeek (OpenAI兼容API)

### 优化需求确认

基于用户反馈，本次优化的具体目标：

- ✅ **优化目标**: 平衡功能完善和视觉美观
- ✅ **重点模块**: Dashboard主页、任务管理流程、AI聊天界面、个人资料统计（全面优化）
- ✅ **设计风格**: **专业精致、高端质感**
- ✅ **动画效果**: **丰富动画、流畅的微交互**

---

## 设计愿景

打造一个**专业精致**的学习助手应用，体现高端质感：

### 核心设计原则

| 维度 | 设计理念 | 实现方式 |
|------|---------|---------|
| **细腻渐变** | 柔和的颜色过渡和层次感 | 主色渐变、卡片渐变、按钮渐变 |
| **精致阴影** | 多层次、低透明度的阴影系统 | 5级elevation，细腻阴影叠加 |
| **流畅动画** | 弹性过渡、页面转场、微交互反馈 | 250ms标准时长，弹性曲线 |
| **信息层次** | 清晰的视觉分层和呼吸感布局 | 8pt网格系统，合理间距 |
| **细节打磨** | 毛玻璃效果、卡片高光、圆环进度、庆祝动画 | 自定义绘制，Lottie动画 |

### 视觉语言关键词

```
专业 · 精致 · 高端 · 流畅 · 温暖 · 活力 · 渐变 · 细腻
```

---

## 已完成工作

### ✅ 阶段一：设计系统基础建设（已完成）

**完成时间**: 2025年12月16日
**工作量**: 8小时
**状态**: ✅ 100%完成

#### 1. Design Tokens系统

**新建文件**: `mobile/lib/core/design/design_tokens.dart`

创建了完整的设计token系统，包括：

- **颜色系统**
  - 主色渐变: `#FF6B35 → #FF8C5A`
  - 辅助色渐变: `#1A237E → #3949AB`
  - 语义色: Success/Warning/Error/Info（含渐变）
  - 中性色阶: 9级灰度 (neutral50-neutral900)
  - 半透明层: overlay10-overlay60
  - 卡片渐变: Primary/Secondary/Neutral

- **间距系统** (8pt网格)
  ```dart
  spacing4, spacing8, spacing12, spacing16, spacing20,
  spacing24, spacing32, spacing40, spacing48, spacing64
  ```

- **圆角系统**
  ```dart
  radius4, radius8, radius12, radius16, radius20,
  radius24, radius32, radiusFull (圆形)
  ```

- **阴影系统** (5级elevation)
  - `shadowSm`: 轻微阴影 (2px offset, 4px blur)
  - `shadowMd`: 中等阴影 (4px offset, 8px blur, 双层)
  - `shadowLg`: 大阴影 (8px offset, 16px blur, 双层)
  - `shadowXl`: 超大阴影 (12px offset, 24px blur)
  - `shadow2xl`: 超大阴影 (16px offset, 32px blur)
  - `shadowPrimary`: 主色阴影（用于强调）
  - `shadowInner`: 内阴影效果

- **动画系统**
  - 时长: Fast(150ms), Normal(250ms), Slow(350ms), Slower(500ms)
  - 曲线: EaseIn, EaseOut, EaseInOut, Spring, Bounce

- **排版系统**
  - 字重: Light(300) - Extrabold(800)
  - 字号: 12px - 60px (11级)
  - 行高: Tight(1.2), Normal(1.5), Relaxed(1.75)

- **图标尺寸**: 16px - 64px (7级)
- **Z-Index层级**: 定义了9级堆叠顺序
- **透明度**: Disabled(0.5), Subtle(0.7), Medium(0.8), Full(1.0)

**代码量**: 350+ 行

#### 2. 主题配置升级

**修改文件**: `mobile/lib/app/theme.dart`

- ✅ 集成了Design Tokens
- ✅ 创建了`AppThemeExtension`用于存储渐变色和自定义阴影
- ✅ 完善了Light/Dark双主题，包含：
  - 完整的ColorScheme配置
  - 精致的CardTheme（零elevation，自定义阴影）
  - 统一的按钮主题（Elevated/Text/Outlined）
  - 优化的输入框主题（带focus状态）
  - Chip主题（圆角、间距）
  - BottomNavigationBar主题
  - AppBar主题（透明背景）
  - 完整的TextTheme（11级字体定义）

- ✅ 添加了主题辅助扩展方法：
  ```dart
  extension ThemeExtensionHelper on ThemeData {
    AppThemeExtension? get appExtension => extension<AppThemeExtension>();
  }
  ```

**代码量**: 520行（从93行扩展到520行）

#### 3. 依赖包添加

**修改文件**: `mobile/pubspec.yaml`

新增6个UI增强库：

| 依赖包 | 版本 | 用途 |
|-------|------|------|
| `flutter_markdown` | ^0.6.18 | Markdown渲染（聊天气泡） |
| `lottie` | ^3.0.0 | Lottie动画（成功庆祝） |
| `animations` | ^2.0.11 | 页面转场动画 |
| `fl_chart` | ^0.66.0 | 统计图表（个人资料页） |
| `shimmer` | ^3.0.0 | 骨架屏效果（加载状态） |
| `confetti` | ^0.7.0 | 粒子庆祝动画（任务完成） |

✅ 已执行 `flutter pub get`，所有依赖安装成功

---

## 实施计划

### 阶段二：基础组件库实现

**时间**: 第1-2周
**优先级**: P0（必须完成）
**预计工作量**: 16小时

#### 2.1 CustomButton组件

**修改文件**: `mobile/lib/presentation/widgets/common/custom_button.dart`

**设计要求**:

实现4种按钮变体：

1. **PrimaryButton**
   - 渐变背景（primaryGradient）
   - 白色文字
   - 精致阴影（shadowMd）
   - 按压时scale 0.98

2. **SecondaryButton**
   - 透明背景
   - 主色边框（1.5px）
   - 主色文字
   - 按压缩放动画

3. **TextButton**
   - 无边框
   - 主色文字
   - 轻微padding

4. **IconButton**
   - 圆形/方形可选
   - 支持渐变背景
   - 图标尺寸可配

**状态支持**:

- ✨ **Loading态**: 内嵌CircularProgressIndicator，禁用点击
- 🚫 **Disabled态**: 灰度滤镜 + 50%透明度
- 🎯 **Pressed态**: 弹性动画（SpringSimulation）
- 🌊 **Ripple效果**: 优化的InkWell涟漪

**API设计**:

```dart
CustomButton.primary(
  text: '开始任务',
  onPressed: () {},
  isLoading: false,
  icon: Icons.play_arrow,
  size: ButtonSize.medium, // small, medium, large
)

CustomButton.secondary(
  text: '取消',
  onPressed: () {},
)

CustomButton.text(
  text: '跳过',
  onPressed: () {},
)

CustomButton.icon(
  icon: Icons.favorite,
  onPressed: () {},
  shape: ButtonShape.circle, // circle, square
  gradient: AppDesignTokens.primaryGradient,
)
```

**预计代码量**: 200行

---

#### 2.2 LoadingIndicator组件

**修改文件**: `mobile/lib/presentation/widgets/common/loading_indicator.dart`

**设计要求**:

实现4种加载状态指示器：

1. **CircularLoading**
   - 主色CircularProgressIndicator
   - 可配置尺寸和线宽
   - 支持自定义文字

2. **SkeletonLoader** (使用shimmer)
   - TaskCardSkeleton: 任务卡片骨架
   - ChatBubbleSkeleton: 聊天气泡骨架
   - ProfileCardSkeleton: 个人资料卡骨架
   - 灰色底 + 白色渐变扫过效果
   - 动画循环时长1.5s

3. **LinearLoading**
   - 顶部线性进度条
   - 主色渐变
   - 不确定性动画

4. **FullScreenLoading**
   - 毛玻璃背景（BackdropFilter）
   - 渐变CircularProgressIndicator
   - 可选加载文字
   - 阻止背景交互

**API设计**:

```dart
// 圆形加载
LoadingIndicator.circular(
  size: 24.0,
  strokeWidth: 3.0,
  message: '加载中...',
)

// 骨架屏
LoadingIndicator.skeleton(
  type: SkeletonType.taskCard,
  count: 3,
)

// 线性进度
LoadingIndicator.linear()

// 全屏加载
LoadingIndicator.fullScreen(
  message: '正在同步数据...',
)
```

**依赖**: `shimmer: ^3.0.0`
**预计代码量**: 300行

---

#### 2.3 ErrorWidget组件

**修改文件**: `mobile/lib/presentation/widgets/common/error_widget.dart`

**设计要求**:

实现3种错误显示变体：

1. **ErrorPage** (全屏错误)
   - 大号错误图标（Icons.error_outline，64px）
   - 错误标题（titleLarge）
   - 错误详情（bodyMedium，灰色）
   - 重试按钮（PrimaryButton）
   - 可选返回按钮

2. **ErrorBanner** (顶部横幅)
   - 错误色背景（errorLight + 20%透明）
   - 错误图标 + 错误消息
   - 关闭按钮
   - 自动消失（5秒）
   - 从顶部滑入动画

3. **InlineError** (内联错误)
   - 小卡片样式
   - 错误图标 + 简短消息
   - 边框为errorLight
   - 用于表单验证错误

**API设计**:

```dart
// 全屏错误
CustomErrorWidget.page(
  title: '加载失败',
  message: '网络连接异常，请检查网络设置',
  onRetry: () {},
  showBackButton: true,
)

// 错误横幅
CustomErrorWidget.banner(
  message: '任务创建失败',
  duration: Duration(seconds: 5),
  onDismiss: () {},
)

// 内联错误
CustomErrorWidget.inline(
  message: '该字段不能为空',
)
```

**预计代码量**: 200行

---

#### 2.4 新增组件

##### FlameIndicator组件

**新建文件**: `mobile/lib/presentation/widgets/common/flame_indicator.dart`

**设计要求**:

火焰等级可视化组件：

- **外观**:
  - 渐变圆环进度条（primaryGradient）
  - 中心火焰图标（Icons.whatshot）
  - 等级数字（大字号，加粗）
  - 亮度百分比（小字号，灰色）

- **动画**:
  - 脉冲动画（运行中）
  - 进度条填充动画
  - 等级提升时的庆祝动画

- **交互**:
  - 点击显示详细统计弹窗
  - 长按显示说明提示

**API设计**:

```dart
FlameIndicator(
  level: 5,
  brightness: 0.75,
  size: 120.0,
  onTap: () {
    // 显示详细统计
  },
)
```

**实现技术**: CustomPainter绘制圆环
**预计代码量**: 250行

---

##### EmptyState组件

**新建文件**: `mobile/lib/presentation/widgets/common/empty_state.dart`

**设计要求**:

空状态展示组件：

- **场景变体**:
  - `EmptyState.noTasks`: 无任务
  - `EmptyState.noChats`: 无聊天记录
  - `EmptyState.noPlans`: 无计划
  - `EmptyState.custom`: 自定义

- **布局**:
  - 大号图标（灰色，64px）
  - 标题文字（titleLarge）
  - 描述文字（bodyMedium，灰色）
  - CTA按钮（可选）

**API设计**:

```dart
EmptyState.noTasks(
  onCreateTask: () {
    // 创建任务
  },
)

EmptyState.custom(
  icon: Icons.inbox,
  title: '暂无内容',
  description: '点击下方按钮开始创建',
  actionText: '创建',
  onAction: () {},
)
```

**预计代码量**: 150行

---

##### SuccessAnimation组件

**新建文件**: `mobile/lib/presentation/widgets/common/success_animation.dart`

**设计要求**:

成功/完成庆祝动画：

- **Lottie动画**: 勾选图标 + 粒子效果
- **Confetti效果**: 彩色纸屑从顶部落下
- **震动反馈**: HapticFeedback.mediumImpact()
- **声音效果**: 可选（未来扩展）

**使用场景**:
- 任务完成
- 计划达成
- 等级提升
- 成就解锁

**API设计**:

```dart
SuccessAnimation(
  type: AnimationType.taskComplete, // taskComplete, levelUp, achievement
  onComplete: () {
    // 动画完成回调
  },
)
```

**依赖**: `lottie: ^3.0.0`, `confetti: ^0.7.0`
**预计代码量**: 180行

---

### 阶段三：核心页面优化

**时间**: 第2-3周
**优先级**: P0-P1
**预计工作量**: 52小时

#### 3.1 Dashboard主页优化 (P0)

**修改文件**: `mobile/lib/presentation/screens/home/home_screen.dart`

**当前问题**:
- ❌ 使用ListTile占位符（第141行）
- ❌ 火焰卡片设计简单
- ❌ 缺少问候语和个性化

**优化方案**:

##### 1) FlameStatusCard重设计

```dart
// 从
Card(
  child: Row(
    children: [
      Icon(Icons.whatshot, color: Colors.orange, size: 40),
      Text('Flame Level: ${user?.flameLevel}'),
    ],
  ),
)

// 改为
Container(
  decoration: BoxDecoration(
    gradient: AppDesignTokens.primaryGradient,
    borderRadius: AppDesignTokens.borderRadius16,
    boxShadow: AppDesignTokens.shadowPrimary,
  ),
  child: FlameIndicator(
    level: user?.flameLevel ?? 0,
    brightness: user?.flameBrightness ?? 0,
    onTap: _showFlameDetails,
  ),
)
```

**特性**:
- 渐变背景（橙色到红色）
- 使用FlameIndicator组件
- 3D火焰图标 + 发光效果
- 点击查看详细统计弹窗
- 卡片高光和阴影优化

##### 2) TodayTasksSection升级

**当前代码** (第138-145行):
```dart
return SizedBox(
  width: 300,
  child: ListTile(title: Text(task.title)), // ❌ 占位符
);
```

**优化后**:
```dart
return Container(
  width: 300,
  margin: EdgeInsets.only(right: AppDesignTokens.spacing12),
  child: TaskCard(
    task: task,
    onTap: () => _navigateToTaskDetail(task.id),
  ),
);
```

**新增功能**:
- ✅ 真实TaskCard替换ListTile
- ✅ 横向滚动优化（边缘淡出效果）
- ✅ 添加"查看全部"按钮
- ✅ 空状态使用EmptyState组件

##### 3) RecommendedTasksSection升级

```dart
// 使用compact模式的TaskCard
ListView.builder(
  itemBuilder: (context, index) {
    return TaskCard(
      task: recommendedTasks[index],
      compact: true, // 紧凑模式
      onTap: () => _navigateToTaskDetail(...),
    );
  },
)
```

**新增功能**:
- 添加分类标签筛选
- 骨架屏加载状态
- Staggered动画（依次淡入）

##### 4) 整体布局优化

**新增顶部渐变背景**:
```dart
Scaffold(
  extendBodyBehindAppBar: true,
  appBar: AppBar(
    backgroundColor: Colors.transparent,
    title: _buildGreeting(), // 根据时间段变化
  ),
  body: Stack(
    children: [
      // 渐变背景
      Container(
        height: 200,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              AppDesignTokens.primaryLight.withOpacity(0.15),
              Colors.transparent,
            ],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
      ),
      // 内容
      RefreshIndicator(
        onRefresh: _refresh,
        child: ...,
      ),
    ],
  ),
)
```

**问候语逻辑**:
```dart
String _getGreeting() {
  final hour = DateTime.now().hour;
  if (hour < 12) return '早上好';
  if (hour < 18) return '下午好';
  return '晚上好';
}
```

**预计改动**: 150行代码

---

#### 3.2 TaskCard组件升级 (P0)

**修改文件**: `mobile/lib/presentation/widgets/task/task_card.dart`

**当前状态**: 273行，功能完整但UI基础

**优化内容**:

##### 视觉优化

1. **卡片渐变背景（根据任务类型）**

```dart
final gradients = {
  TaskType.learning: LinearGradient(colors: [Colors.blue.shade50, Colors.blue.shade100]),
  TaskType.training: LinearGradient(colors: [Colors.orange.shade50, Colors.orange.shade100]),
  TaskType.errorFix: LinearGradient(colors: [Colors.red.shade50, Colors.red.shade100]),
  TaskType.reflection: LinearGradient(colors: [Colors.purple.shade50, Colors.purple.shade100]),
  TaskType.social: LinearGradient(colors: [Colors.green.shade50, Colors.green.shade100]),
  TaskType.planning: LinearGradient(colors: [Colors.teal.shade50, Colors.teal.shade100]),
};

Container(
  decoration: BoxDecoration(
    gradient: gradients[task.type],
    borderRadius: AppDesignTokens.borderRadius12,
    boxShadow: AppDesignTokens.shadowMd,
  ),
  child: ...,
)
```

2. **左侧彩色条纹（类型标识）**

```dart
Row(
  children: [
    // 彩色条纹
    Container(
      width: 4,
      height: double.infinity,
      decoration: BoxDecoration(
        gradient: _getTypeGradient(task.type),
        borderRadius: BorderRadius.horizontal(
          left: Radius.circular(AppDesignTokens.radius12),
        ),
      ),
    ),
    Expanded(child: _buildContent()),
  ],
)
```

3. **Tag使用渐变Chip**

```dart
Chip(
  label: Text(task.type),
  backgroundColor: Colors.transparent,
  padding: EdgeInsets.zero,
  avatar: ShaderMask(
    shaderCallback: (bounds) => _getTypeGradient(task.type).createShader(bounds),
    child: Icon(Icons.circle, color: Colors.white),
  ),
)
```

4. **Difficulty星星使用渐变色**

```dart
Row(
  children: List.generate(5, (index) {
    return ShaderMask(
      shaderCallback: (bounds) {
        return LinearGradient(
          colors: [Colors.amber, Colors.orange],
        ).createShader(bounds);
      },
      child: Icon(
        index < task.difficulty ? Icons.star : Icons.star_border,
        color: Colors.white,
        size: 16,
      ),
    );
  }),
)
```

5. **同步覆盖层优化（模糊背景）**

```dart
// 当前（第98-120行）：半透明红色覆盖
// 优化为：模糊背景 + 弹窗样式
if (task.syncStatus == SyncStatus.failed) {
  Positioned.fill(
    child: ClipRRect(
      borderRadius: AppDesignTokens.borderRadius12,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 5, sigmaY: 5),
        child: Container(
          color: AppDesignTokens.error.withOpacity(0.9),
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.cloud_off, size: 48, color: Colors.white),
                SizedBox(height: 8),
                Text('同步失败', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    TextButton(child: Text('放弃'), onPressed: _onAbandon),
                    SizedBox(width: 8),
                    ElevatedButton(child: Text('重试'), onPressed: _onRetry),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  ),
}
```

##### 微交互

1. **卡片按压弹性动画**

```dart
class TaskCard extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return GestureDetector(
      onTapDown: (_) => _controller.forward(),
      onTapUp: (_) => _controller.reverse(),
      onTapCancel: () => _controller.reverse(),
      child: AnimatedBuilder(
        animation: _scaleAnimation,
        builder: (context, child) {
          return Transform.scale(
            scale: _scaleAnimation.value,
            child: _buildCard(),
          );
        },
      ),
    );
  }
}

// _scaleAnimation: 1.0 → 0.98
```

2. **滑动显示操作按钮（编辑、删除）**

```dart
Dismissible(
  key: Key(task.id),
  direction: DismissDirection.endToStart,
  confirmDismiss: (direction) async {
    // 滑动一定距离后显示操作按钮
    return false; // 不真正删除，只显示按钮
  },
  background: Container(
    alignment: Alignment.centerRight,
    padding: EdgeInsets.only(right: 16),
    decoration: BoxDecoration(
      gradient: AppDesignTokens.errorGradient,
      borderRadius: AppDesignTokens.borderRadius12,
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        IconButton(icon: Icon(Icons.edit), onPressed: _onEdit),
        IconButton(icon: Icon(Icons.delete), onPressed: _onDelete),
      ],
    ),
  ),
  child: _buildCard(),
)
```

3. **完成状态勾选动画**

```dart
AnimatedContainer(
  duration: AppDesignTokens.durationNormal,
  curve: Curves.easeInOut,
  decoration: BoxDecoration(
    color: task.status == TaskStatus.completed
      ? AppDesignTokens.success.withOpacity(0.1)
      : Colors.transparent,
  ),
  child: Stack(
    children: [
      _buildContent(),
      if (task.status == TaskStatus.completed)
        Positioned(
          top: 8,
          right: 8,
          child: AnimatedScale(
            scale: _checkScale,
            duration: AppDesignTokens.durationSlow,
            curve: Curves.elasticOut,
            child: Icon(
              Icons.check_circle,
              color: AppDesignTokens.success,
              size: 32,
            ),
          ),
        ),
    ],
  ),
)
```

**预计改动**: +150行代码（总计420行）

---

#### 3.3 任务列表和详情页 (P0)

##### TaskListScreen优化

**修改文件**: `mobile/lib/presentation/screens/task/task_list_screen.dart`

**改进清单**:

1. **连接导航到TaskDetailScreen**

```dart
// 当前：TODO注释
// 优化：
TaskCard(
  task: tasks[index],
  onTap: () {
    context.push('/tasks/${tasks[index].id}');
  },
)
```

2. **FilterChips渐变选中状态**

```dart
ChoiceChip(
  label: Text(filter.name),
  selected: currentFilter == filter,
  selectedColor: Colors.transparent,
  avatar: selected ? ShaderMask(
    shaderCallback: (bounds) => AppDesignTokens.primaryGradient.createShader(bounds),
    child: Icon(filter.icon, color: Colors.white),
  ) : Icon(filter.icon),
  // ...
)
```

3. **添加搜索栏（动画展开/收起）**

```dart
AnimatedContainer(
  duration: AppDesignTokens.durationNormal,
  height: _isSearching ? 56 : 0,
  child: TextField(
    decoration: InputDecoration(
      prefixIcon: Icon(Icons.search),
      hintText: '搜索任务...',
      suffixIcon: IconButton(
        icon: Icon(Icons.close),
        onPressed: () => setState(() => _isSearching = false),
      ),
    ),
  ),
)
```

4. **列表项滑动删除/完成手势**

```dart
ListView.builder(
  itemBuilder: (context, index) {
    return Dismissible(
      key: Key(tasks[index].id),
      direction: DismissDirection.horizontal,
      confirmDismiss: (direction) async {
        if (direction == DismissDirection.startToEnd) {
          // 向右滑：标记完成
          await _completeTask(tasks[index].id);
          return true;
        } else {
          // 向左滑：删除
          return await _confirmDelete(context);
        }
      },
      background: _buildSwipeBackground(isComplete: true),
      secondaryBackground: _buildSwipeBackground(isComplete: false),
      child: TaskCard(task: tasks[index]),
    );
  },
)
```

5. **Staggered动画（依次淡入）**

```dart
ListView.builder(
  itemBuilder: (context, index) {
    return AnimatedBuilder(
      animation: _listAnimation,
      builder: (context, child) {
        final delay = index * 50; // 每项延迟50ms
        final progress = Curves.easeOut.transform(
          ((_listAnimation.value * 1000) - delay).clamp(0, 1000) / 1000,
        );
        return Opacity(
          opacity: progress,
          child: Transform.translate(
            offset: Offset(0, 20 * (1 - progress)),
            child: TaskCard(task: tasks[index]),
          ),
        );
      },
    );
  },
)
```

6. **浮动创建按钮（渐变 + 阴影）**

```dart
FloatingActionButton(
  onPressed: _createTask,
  child: Container(
    decoration: BoxDecoration(
      gradient: AppDesignTokens.primaryGradient,
      shape: BoxShape.circle,
      boxShadow: AppDesignTokens.shadowPrimary,
    ),
    child: Icon(Icons.add, color: Colors.white),
  ),
)
```

**预计改动**: +100行代码

---

##### TaskDetailScreen优化

**修改文件**: `mobile/lib/presentation/screens/task/task_detail_screen.dart`

**改进清单**:

1. **Hero动画（从列表到详情）**

```dart
// TaskCard中
Hero(
  tag: 'task-${task.id}',
  child: _buildCard(),
)

// TaskDetailScreen中
Hero(
  tag: 'task-${widget.taskId}',
  child: _buildHeader(),
)
```

2. **顶部大标题 + 渐变背景**

```dart
SliverAppBar(
  expandedHeight: 200,
  flexibleSpace: FlexibleSpaceBar(
    background: Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppDesignTokens.primaryLight.withOpacity(0.8),
            Colors.transparent,
          ],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        ),
      ),
      child: SafeArea(
        child: Padding(
          padding: EdgeInsets.all(AppDesignTokens.spacing16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              Text(
                task.title,
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  color: Colors.white,
                  fontWeight: AppDesignTokens.fontWeightBold,
                ),
              ),
              SizedBox(height: 8),
              _buildStatusChips(),
            ],
          ),
        ),
      ),
    ),
  ),
)
```

3. **InfoTile卡片式设计**

```dart
// 从简单Row改为卡片
Container(
  margin: EdgeInsets.only(bottom: AppDesignTokens.spacing8),
  padding: EdgeInsets.all(AppDesignTokens.spacing12),
  decoration: BoxDecoration(
    gradient: LinearGradient(
      colors: [Colors.white, AppDesignTokens.neutral50],
    ),
    borderRadius: AppDesignTokens.borderRadius8,
    boxShadow: AppDesignTokens.shadowSm,
  ),
  child: Row(
    children: [
      Container(
        padding: EdgeInsets.all(8),
        decoration: BoxDecoration(
          gradient: AppDesignTokens.primaryGradient,
          borderRadius: AppDesignTokens.borderRadius8,
        ),
        child: Icon(icon, color: Colors.white, size: 20),
      ),
      SizedBox(width: 12),
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.labelSmall),
            Text(content, style: Theme.of(context).textTheme.bodyMedium),
          ],
        ),
      ),
    ],
  ),
)
```

4. **执行指南区Markdown渲染**

```dart
Container(
  padding: EdgeInsets.all(AppDesignTokens.spacing16),
  decoration: BoxDecoration(
    color: AppDesignTokens.neutral50,
    borderRadius: AppDesignTokens.borderRadius12,
  ),
  child: MarkdownBody(
    data: task.guide ?? '暂无指南',
    styleSheet: MarkdownStyleSheet(
      h1: Theme.of(context).textTheme.titleLarge,
      p: Theme.of(context).textTheme.bodyMedium,
      code: TextStyle(
        backgroundColor: AppDesignTokens.neutral200,
        fontFamily: 'monospace',
      ),
    ),
  ),
)
```

5. **底部操作栏渐变按钮**

```dart
Container(
  padding: EdgeInsets.all(AppDesignTokens.spacing16),
  decoration: BoxDecoration(
    color: Colors.white,
    boxShadow: [
      BoxShadow(
        color: Colors.black.withOpacity(0.1),
        blurRadius: 8,
        offset: Offset(0, -2),
      ),
    ],
  ),
  child: Row(
    children: [
      Expanded(
        child: CustomButton.secondary(
          text: '编辑',
          icon: Icons.edit,
          onPressed: _onEdit,
        ),
      ),
      SizedBox(width: 12),
      Expanded(
        child: CustomButton.primary(
          text: '开始执行',
          icon: Icons.play_arrow,
          onPressed: _onStart,
        ),
      ),
    ],
  ),
)
```

6. **精致删除确认对话框**

```dart
Future<bool?> _confirmDelete(BuildContext context) {
  return showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      shape: RoundedRectangleBorder(
        borderRadius: AppDesignTokens.borderRadius16,
      ),
      title: Row(
        children: [
          Container(
            padding: EdgeInsets.all(8),
            decoration: BoxDecoration(
              gradient: AppDesignTokens.errorGradient,
              shape: BoxShape.circle,
            ),
            child: Icon(Icons.delete_outline, color: Colors.white),
          ),
          SizedBox(width: 12),
          Text('确认删除'),
        ],
      ),
      content: Text('删除后无法恢复，确定要删除这个任务吗？'),
      actions: [
        TextButton(
          child: Text('取消'),
          onPressed: () => Navigator.pop(context, false),
        ),
        ElevatedButton(
          style: ElevatedButton.styleFrom(
            backgroundColor: AppDesignTokens.error,
          ),
          child: Text('删除'),
          onPressed: () => Navigator.pop(context, true),
        ),
      ],
    ),
  );
}
```

**依赖**: `flutter_markdown: ^0.6.18`
**预计改动**: +120行代码

---

#### 3.4 任务执行页优化 (P1)

##### TaskExecutionScreen优化

**修改文件**: `mobile/lib/presentation/screens/task/task_execution_screen.dart`

**改进清单**:

1. **TimerWidget升级（圆形进度环绕）**

```dart
// 见下一节TimerWidget升级详情
CustomPaint(
  size: Size(200, 200),
  painter: CircularTimerPainter(
    progress: _elapsed / _totalSeconds,
    gradient: AppDesignTokens.primaryGradient,
  ),
  child: Center(
    child: Text(
      _formatTime(_elapsed),
      style: Theme.of(context).textTheme.displayMedium?.copyWith(
        fontWeight: AppDesignTokens.fontWeightBold,
        fontFamily: 'monospace',
      ),
    ),
  ),
)
```

2. **渐变页面背景**

```dart
Scaffold(
  body: Container(
    decoration: BoxDecoration(
      gradient: LinearGradient(
        colors: [
          AppDesignTokens.primaryBase.withOpacity(0.05),
          AppDesignTokens.secondaryBase.withOpacity(0.05),
        ],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      ),
    ),
    child: ...,
  ),
)
```

3. **卡片式ExpansionTile**

```dart
Container(
  margin: EdgeInsets.symmetric(
    horizontal: AppDesignTokens.spacing16,
    vertical: AppDesignTokens.spacing8,
  ),
  decoration: BoxDecoration(
    color: Colors.white,
    borderRadius: AppDesignTokens.borderRadius12,
    boxShadow: AppDesignTokens.shadowMd,
  ),
  child: ExpansionTile(
    tilePadding: EdgeInsets.all(AppDesignTokens.spacing16),
    title: Row(
      children: [
        Container(
          padding: EdgeInsets.all(8),
          decoration: BoxDecoration(
            gradient: AppDesignTokens.infoGradient,
            borderRadius: AppDesignTokens.borderRadius8,
          ),
          child: Icon(Icons.description, color: Colors.white, size: 20),
        ),
        SizedBox(width: 12),
        Text('执行指南'),
      ],
    ),
    children: [
      Padding(
        padding: EdgeInsets.all(AppDesignTokens.spacing16),
        child: MarkdownBody(data: task.guide),
      ),
    ],
  ),
)
```

4. **完成时全屏庆祝动画 + 震动反馈**

```dart
Future<void> _onComplete() async {
  // 震动反馈
  HapticFeedback.mediumImpact();

  // 全屏庆祝动画
  await Navigator.push(
    context,
    PageRouteBuilder(
      opaque: false,
      pageBuilder: (context, animation, secondaryAnimation) {
        return FadeTransition(
          opacity: animation,
          child: Container(
            color: Colors.black54,
            child: Center(
              child: SuccessAnimation(
                type: AnimationType.taskComplete,
                onComplete: () {
                  Navigator.pop(context);
                  Navigator.pop(context); // 返回任务列表
                },
              ),
            ),
          ),
        );
      },
      transitionDuration: AppDesignTokens.durationNormal,
    ),
  );
}
```

**依赖**: `confetti: ^0.7.0`, `flutter/services.dart`
**预计改动**: +80行代码

---

##### TimerWidget升级

**修改文件**: `mobile/lib/presentation/widgets/task/timer_widget.dart`

**当前状态**: 105行，功能完整但UI简单

**升级内容**:

1. **圆形渐变进度环**

```dart
class CircularTimerPainter extends CustomPainter {
  final double progress;
  final Gradient gradient;

  @override
  void paint(Canvas canvas, Size size) {
    // 背景圆环
    Paint bgPaint = Paint()
      ..color = AppDesignTokens.neutral200
      ..style = PaintingStyle.stroke
      ..strokeWidth = 8
      ..strokeCap = StrokeCap.round;

    canvas.drawCircle(
      size.center(Offset.zero),
      size.width / 2 - 8,
      bgPaint,
    );

    // 进度圆环（渐变）
    Rect rect = Rect.fromCircle(
      center: size.center(Offset.zero),
      radius: size.width / 2 - 8,
    );

    Paint progressPaint = Paint()
      ..shader = gradient.createShader(rect)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 8
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(
      rect,
      -pi / 2,
      2 * pi * progress,
      false,
      progressPaint,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
```

2. **播放/暂停图标动画**

```dart
AnimatedSwitcher(
  duration: AppDesignTokens.durationFast,
  transitionBuilder: (child, animation) {
    return ScaleTransition(
      scale: animation,
      child: RotationTransition(
        turns: animation,
        child: child,
      ),
    );
  },
  child: IconButton(
    key: ValueKey(_isRunning),
    icon: Icon(
      _isRunning ? Icons.pause_circle_filled : Icons.play_circle_filled,
      size: 64,
    ),
    color: AppDesignTokens.primaryBase,
    onPressed: _toggleTimer,
  ),
)
```

3. **运行时脉冲动画**

```dart
AnimatedBuilder(
  animation: _pulseAnimation,
  builder: (context, child) {
    return Transform.scale(
      scale: _isRunning ? _pulseAnimation.value : 1.0,
      child: child,
    );
  },
  child: _buildTimerCircle(),
)

// _pulseAnimation: 1.0 → 1.05 → 1.0 (循环)
```

**预计改动**: +120行代码（总计225行）

---

#### 3.5 聊天界面优化 (P0)

##### ChatBubble组件升级

**修改文件**: `mobile/lib/presentation/widgets/chat/chat_bubble.dart`

**当前状态**: 67行，基础气泡布局

**改进清单**:

1. **集成Markdown渲染**

```dart
// 从
Text(message.content)

// 改为
MarkdownBody(
  data: message.content,
  styleSheet: MarkdownStyleSheet(
    p: TextStyle(
      color: isUser ? Colors.white : AppColors.lightText,
      fontSize: AppDesignTokens.fontSizeBase,
    ),
    code: TextStyle(
      backgroundColor: isUser
        ? Colors.white.withOpacity(0.2)
        : AppDesignTokens.neutral200,
      fontFamily: 'monospace',
      fontSize: AppDesignTokens.fontSizeSm,
    ),
    codeblockDecoration: BoxDecoration(
      color: isUser
        ? Colors.white.withOpacity(0.15)
        : AppDesignTokens.neutral100,
      borderRadius: AppDesignTokens.borderRadius8,
    ),
    blockquote: TextStyle(
      color: isUser ? Colors.white70 : AppDesignTokens.neutral600,
      fontStyle: FontStyle.italic,
    ),
  ),
  onTapLink: (text, href, title) {
    if (href != null) {
      // 打开链接
      launchUrl(Uri.parse(href));
    },
  },
)
```

2. **代码块语法高亮**

```dart
// 使用flutter_markdown的语法高亮功能
MarkdownBody(
  data: message.content,
  syntaxHighlighter: CustomSyntaxHighlighter(),
)

class CustomSyntaxHighlighter extends SyntaxHighlighter {
  @override
  TextSpan format(String source) {
    // 简单的关键字高亮
    // 可使用highlight.js或自定义实现
  }
}
```

3. **用户气泡渐变背景**

```dart
// 从
Container(
  decoration: BoxDecoration(
    color: AppColors.primary,
    borderRadius: ...,
  ),
)

// 改为
Container(
  decoration: BoxDecoration(
    gradient: AppDesignTokens.primaryGradient,
    borderRadius: ...,
    boxShadow: AppDesignTokens.shadowMd,
  ),
)
```

4. **AI气泡毛玻璃效果**

```dart
ClipRRect(
  borderRadius: ...,
  child: BackdropFilter(
    filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
    child: Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.9),
        borderRadius: ...,
        border: Border.all(
          color: Colors.white.withOpacity(0.3),
          width: 1,
        ),
        boxShadow: AppDesignTokens.shadowMd,
      ),
      child: ...,
    ),
  ),
)
```

5. **Avatar渐变边框**

```dart
Container(
  padding: EdgeInsets.all(2),
  decoration: BoxDecoration(
    gradient: isUser
      ? AppDesignTokens.primaryGradient
      : AppDesignTokens.secondaryGradient,
    shape: BoxShape.circle,
  ),
  child: Container(
    padding: EdgeInsets.all(8),
    decoration: BoxDecoration(
      color: Colors.white,
      shape: BoxShape.circle,
    ),
    child: Icon(
      isUser ? Icons.person : Icons.auto_awesome,
      color: isUser ? AppColors.primary : AppColors.secondary,
      size: 20,
    ),
  ),
)
```

6. **气泡出现动画（淡入 + 位移）**

```dart
class ChatBubble extends StatefulWidget {
  @override
  _ChatBubbleState createState() => _ChatBubbleState();
}

class _ChatBubbleState extends State<ChatBubble>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _opacity;
  late Animation<Offset> _position;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: AppDesignTokens.durationNormal,
      vsync: this,
    );

    _opacity = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOut),
    );

    _position = Tween<Offset>(
      begin: Offset(0, 0.1),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOut));

    _controller.forward();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _opacity,
      child: SlideTransition(
        position: _position,
        child: _buildBubble(),
      ),
    );
  }
}
```

**依赖**: `flutter_markdown: ^0.6.18`, `url_launcher`
**预计改动**: +150行代码（总计217行）

---

##### ActionCard组件升级

**修改文件**: `mobile/lib/presentation/widgets/chat/action_card.dart`

**当前状态**: 107行，基础卡片结构

**改进清单**:

1. **渐变左侧边框（类型标识）**

```dart
Container(
  decoration: BoxDecoration(
    color: Colors.white,
    borderRadius: AppDesignTokens.borderRadius12,
    boxShadow: AppDesignTokens.shadowMd,
    border: Border(
      left: BorderSide(
        width: 4,
        color: Colors.transparent,
      ),
    ),
  ),
  foregroundDecoration: BoxDecoration(
    gradient: LinearGradient(
      colors: _getActionGradient(action.type),
      begin: Alignment.topLeft,
      end: Alignment.bottomLeft,
    ),
    borderRadius: BorderRadius.only(
      topLeft: Radius.circular(AppDesignTokens.radius12),
      bottomLeft: Radius.circular(AppDesignTokens.radius12),
    ),
  ),
)

LinearGradient _getActionGradient(ActionType type) {
  switch (type) {
    case ActionType.createTask:
      return AppDesignTokens.primaryGradient;
    case ActionType.createPlan:
      return AppDesignTokens.secondaryGradient;
    case ActionType.updatePreference:
      return AppDesignTokens.infoGradient;
    default:
      return AppDesignTokens.primaryGradient;
  }
}
```

2. **图标脉冲动画**

```dart
class _ActionIconState extends State<_ActionIcon>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scale;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: Duration(milliseconds: 1500),
      vsync: this,
    )..repeat(reverse: true);

    _scale = Tween<double>(begin: 1.0, end: 1.2).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _scale,
      builder: (context, child) {
        return Transform.scale(
          scale: _scale.value,
          child: Container(
            padding: EdgeInsets.all(12),
            decoration: BoxDecoration(
              gradient: _getActionGradient(widget.action.type),
              shape: BoxShape.circle,
              boxShadow: AppDesignTokens.shadowSm,
            ),
            child: Icon(
              _getActionIcon(widget.action.type),
              color: Colors.white,
              size: 24,
            ),
          ),
        );
      },
    );
  }
}
```

3. **参数卡片化展示**

```dart
// 从简单的Chip列表
// 改为卡片式参数展示
Wrap(
  spacing: 8,
  runSpacing: 8,
  children: action.params.entries.map((entry) {
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: 12,
        vertical: 8,
      ),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppDesignTokens.neutral50,
            AppDesignTokens.neutral100,
          ],
        ),
        borderRadius: AppDesignTokens.borderRadius8,
        border: Border.all(
          color: AppDesignTokens.neutral300,
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '${entry.key}: ',
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: AppDesignTokens.neutral600,
            ),
          ),
          Text(
            entry.value.toString(),
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              fontWeight: AppDesignTokens.fontWeightMedium,
            ),
          ),
        ],
      ),
    );
  }).toList(),
)
```

4. **Confirm按钮渐变**

```dart
CustomButton.primary(
  text: '确认',
  icon: Icons.check,
  onPressed: () => widget.onConfirm(action),
)
```

5. **卡片微光效果（未操作时）**

```dart
class _ShimmerCard extends StatefulWidget {
  @override
  _ShimmerCardState createState() => _ShimmerCardState();
}

class _ShimmerCardState extends State<_ShimmerCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: Duration(seconds: 2),
      vsync: this,
    )..repeat();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                Colors.transparent,
                Colors.white.withOpacity(0.3),
                Colors.transparent,
              ],
              stops: [
                _controller.value - 0.3,
                _controller.value,
                _controller.value + 0.3,
              ].map((e) => e.clamp(0.0, 1.0)).toList(),
              begin: Alignment.centerLeft,
              end: Alignment.centerRight,
            ),
          ),
          child: widget.child,
        );
      },
    );
  }
}
```

**预计改动**: +130行代码（总计237行）

---

##### ChatScreen优化

**修改文件**: `mobile/lib/presentation/screens/chat/chat_screen.dart`

**改进清单**:

1. **渐变AppBar**

```dart
AppBar(
  flexibleSpace: Container(
    decoration: BoxDecoration(
      gradient: LinearGradient(
        colors: [
          AppDesignTokens.primaryBase.withOpacity(0.1),
          Colors.transparent,
        ],
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
      ),
    ),
  ),
  title: Text('AI学习助手'),
  actions: [
    IconButton(
      icon: Icon(Icons.history),
      onPressed: _showHistory,
    ),
    IconButton(
      icon: Icon(Icons.refresh),
      onPressed: _newChat,
    ),
  ],
)
```

2. **消息Staggered动画**

```dart
// 类似TaskListScreen的实现
ListView.builder(
  reverse: true,
  itemBuilder: (context, index) {
    return _buildAnimatedMessage(messages[index], index);
  },
)

Widget _buildAnimatedMessage(ChatMessage message, int index) {
  return AnimatedBuilder(
    animation: _listAnimation,
    builder: (context, child) {
      final delay = index * 30;
      final progress = Curves.easeOut.transform(
        ((_listAnimation.value * 1000) - delay).clamp(0, 1000) / 1000,
      );
      return Opacity(
        opacity: progress,
        child: Transform.translate(
          offset: Offset(0, 10 * (1 - progress)),
          child: ChatBubble(message: message),
        ),
      );
    },
  );
}
```

3. **打字指示器（三点跳动）**

```dart
class TypingIndicator extends StatefulWidget {
  @override
  _TypingIndicatorState createState() => _TypingIndicatorState();
}

class _TypingIndicatorState extends State<TypingIndicator>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: Duration(milliseconds: 1200),
      vsync: this,
    )..repeat();
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(3, (index) {
        return AnimatedBuilder(
          animation: _controller,
          builder: (context, child) {
            final delay = index * 0.2;
            final progress = ((_controller.value - delay) % 1.0).clamp(0.0, 1.0);
            final offset = sin(progress * pi) * 8;

            return Transform.translate(
              offset: Offset(0, -offset),
              child: Container(
                margin: EdgeInsets.symmetric(horizontal: 2),
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  color: AppDesignTokens.neutral500,
                  shape: BoxShape.circle,
                ),
              ),
            );
          },
        );
      }),
    );
  }
}

// 使用
if (_isTyping)
  Padding(
    padding: EdgeInsets.all(16),
    child: Row(
      children: [
        CircleAvatar(
          child: Icon(Icons.auto_awesome),
        ),
        SizedBox(width: 8),
        TypingIndicator(),
      ],
    ),
  )
```

4. **长按消息复制/分享**

```dart
GestureDetector(
  onLongPress: () {
    showModalBottomSheet(
      context: context,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(AppDesignTokens.radius16),
        ),
      ),
      builder: (context) => Container(
        padding: EdgeInsets.all(AppDesignTokens.spacing16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: Icon(Icons.copy),
              title: Text('复制'),
              onTap: () {
                Clipboard.setData(ClipboardData(text: message.content));
                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('已复制到剪贴板')),
                );
              },
            ),
            ListTile(
              leading: Icon(Icons.share),
              title: Text('分享'),
              onTap: () {
                Navigator.pop(context);
                Share.share(message.content);
              },
            ),
          ],
        ),
      ),
    );
  },
  child: ChatBubble(message: message),
)
```

5. **滚动到底部浮动按钮**

```dart
Stack(
  children: [
    ListView.builder(...),

    // 当不在底部时显示
    if (!_isAtBottom)
      Positioned(
        right: 16,
        bottom: 80,
        child: FloatingActionButton.small(
          backgroundColor: Colors.white,
          elevation: 4,
          child: Icon(Icons.arrow_downward, color: AppColors.primary),
          onPressed: () {
            _scrollController.animateTo(
              0,
              duration: AppDesignTokens.durationNormal,
              curve: Curves.easeOut,
            );
          },
        ),
      ),
  ],
)

// 监听滚动位置
_scrollController.addListener(() {
  final isAtBottom = _scrollController.offset <= 100;
  if (_isAtBottom != isAtBottom) {
    setState(() => _isAtBottom = isAtBottom);
  }
});
```

**预计改动**: +100行代码

---

##### ChatInput组件优化

**修改文件**: `mobile/lib/presentation/widgets/chat/chat_input.dart`

**当前状态**: 107行，功能完整

**改进清单**:

1. **输入框毛玻璃背景**

```dart
ClipRRect(
  borderRadius: BorderRadius.vertical(
    top: Radius.circular(AppDesignTokens.radius16),
  ),
  child: BackdropFilter(
    filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
    child: Container(
      padding: EdgeInsets.all(AppDesignTokens.spacing12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.95),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: Offset(0, -5),
          ),
        ],
      ),
      child: _buildInputRow(),
    ),
  ),
)
```

2. **发送按钮渐变 + 旋转动画**

```dart
AnimatedContainer(
  duration: AppDesignTokens.durationNormal,
  decoration: BoxDecoration(
    gradient: _canSend
      ? AppDesignTokens.primaryGradient
      : LinearGradient(colors: [AppDesignTokens.neutral300, AppDesignTokens.neutral300]),
    shape: BoxShape.circle,
    boxShadow: _canSend ? AppDesignTokens.shadowSm : null,
  ),
  child: IconButton(
    icon: AnimatedSwitcher(
      duration: AppDesignTokens.durationFast,
      transitionBuilder: (child, animation) {
        return RotationTransition(
          turns: animation,
          child: child,
        );
      },
      child: _isSending
        ? SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              valueColor: AlwaysStoppedAnimation(Colors.white),
            ),
          )
        : Icon(
            Icons.send,
            key: ValueKey(_isSending),
            color: _canSend ? Colors.white : AppDesignTokens.neutral500,
          ),
    ),
    onPressed: _canSend ? _onSend : null,
  ),
)
```

3. **输入时微动画**

```dart
AnimatedContainer(
  duration: AppDesignTokens.durationFast,
  decoration: BoxDecoration(
    color: _isFocused
      ? Colors.white
      : AppDesignTokens.neutral50,
    borderRadius: AppDesignTokens.borderRadius24,
    border: Border.all(
      color: _isFocused
        ? AppColors.primary
        : AppDesignTokens.neutral300,
      width: _isFocused ? 2 : 1,
    ),
  ),
  child: TextField(
    focusNode: _focusNode,
    decoration: InputDecoration(
      hintText: '输入消息...',
      border: InputBorder.none,
    ),
    onChanged: (text) {
      setState(() => _canSend = text.trim().isNotEmpty);
    },
  ),
)

// 监听焦点
_focusNode.addListener(() {
  setState(() => _isFocused = _focusNode.hasFocus);
});
```

**预计改动**: +60行代码（总计167行）

---

#### 3.6 个人资料页优化 (P1)

**修改文件**: `mobile/lib/presentation/screens/profile/profile_screen.dart`

**改进清单**:

##### 1) UserInfoCard重设计

```dart
Container(
  height: 200,
  decoration: BoxDecoration(
    gradient: AppDesignTokens.primaryGradient,
    borderRadius: BorderRadius.vertical(
      bottom: Radius.circular(AppDesignTokens.radius32),
    ),
  ),
  child: Stack(
    children: [
      // 波浪形状
      Positioned(
        bottom: 0,
        left: 0,
        right: 0,
        child: CustomPaint(
          size: Size(double.infinity, 50),
          painter: WavePainter(
            color: Theme.of(context).scaffoldBackgroundColor,
          ),
        ),
      ),

      // 内容
      SafeArea(
        child: Padding(
          padding: EdgeInsets.all(AppDesignTokens.spacing16),
          child: Row(
            children: [
              // 头像（渐变边框）
              Container(
                padding: EdgeInsets.all(4),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [Colors.white, Colors.white.withOpacity(0.5)],
                  ),
                  shape: BoxShape.circle,
                  boxShadow: AppDesignTokens.shadowMd,
                ),
                child: CircleAvatar(
                  radius: 40,
                  backgroundImage: user?.avatar != null
                    ? NetworkImage(user!.avatar!)
                    : null,
                  child: user?.avatar == null
                    ? Icon(Icons.person, size: 40, color: Colors.white)
                    : null,
                ),
              ),

              SizedBox(width: 16),

              // 用户信息
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      user?.nickname ?? user?.username ?? '',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: Colors.white,
                        fontWeight: AppDesignTokens.fontWeightBold,
                      ),
                    ),
                    SizedBox(height: 4),
                    Text(
                      user?.email ?? '',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.white.withOpacity(0.8),
                      ),
                    ),
                    SizedBox(height: 12),

                    // 火焰状态（小尺寸）
                    Row(
                      children: [
                        Icon(Icons.whatshot, color: Colors.white, size: 20),
                        SizedBox(width: 4),
                        Text(
                          'Lv.${user?.flameLevel ?? 0}',
                          style: TextStyle(
                            color: Colors.white,
                            fontWeight: AppDesignTokens.fontWeightBold,
                          ),
                        ),
                        SizedBox(width: 8),
                        Expanded(
                          child: LinearProgressIndicator(
                            value: user?.flameBrightness ?? 0,
                            backgroundColor: Colors.white.withOpacity(0.3),
                            valueColor: AlwaysStoppedAnimation(Colors.white),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    ],
  ),
)

// 波浪形状绘制
class WavePainter extends CustomPainter {
  final Color color;

  WavePainter({required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    Paint paint = Paint()
      ..color = color
      ..style = PaintingStyle.fill;

    Path path = Path();
    path.moveTo(0, size.height * 0.5);

    // 贝塞尔曲线创建波浪
    for (double i = 0; i < size.width; i += size.width / 4) {
      path.quadraticBezierTo(
        i + size.width / 8,
        size.height * 0.2,
        i + size.width / 4,
        size.height * 0.5,
      );
      path.quadraticBezierTo(
        i + size.width * 3 / 8,
        size.height * 0.8,
        i + size.width / 2,
        size.height * 0.5,
      );
    }

    path.lineTo(size.width, size.height);
    path.lineTo(0, size.height);
    path.close();

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
```

##### 2) 统计可视化

**新建文件**: `mobile/lib/presentation/widgets/profile/statistics_card.dart`

```dart
class StatisticsCard extends StatelessWidget {
  final String title;
  final Widget chart;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: EdgeInsets.symmetric(
        horizontal: AppDesignTokens.spacing16,
        vertical: AppDesignTokens.spacing8,
      ),
      padding: EdgeInsets.all(AppDesignTokens.spacing16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [Colors.white, AppDesignTokens.neutral50],
        ),
        borderRadius: AppDesignTokens.borderRadius16,
        boxShadow: AppDesignTokens.shadowMd,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                title,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: AppDesignTokens.fontWeightBold,
                ),
              ),
              if (subtitle != null) ...[
                SizedBox(width: 8),
                Text(
                  subtitle!,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppDesignTokens.neutral600,
                  ),
                ),
              ],
            ],
          ),
          SizedBox(height: 16),
          SizedBox(
            height: 200,
            child: chart,
          ),
        ],
      ),
    );
  }
}
```

**在ProfileScreen中使用**:

```dart
Column(
  children: [
    _buildUserInfoCard(),

    SizedBox(height: 24),

    // 本周任务完成趋势（折线图）
    StatisticsCard(
      title: '本周任务完成',
      subtitle: '共完成 ${weeklyStats.total} 个',
      chart: LineChart(
        LineChartData(
          gridData: FlGridData(show: false),
          titlesData: FlTitlesData(
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (value, meta) {
                  const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
                  return Text(days[value.toInt()]);
                },
              ),
            ),
          ),
          borderData: FlBorderData(show: false),
          lineBarsData: [
            LineChartBarData(
              spots: weeklyStats.data.asMap().entries.map((e) {
                return FlSpot(e.key.toDouble(), e.value.toDouble());
              }).toList(),
              isCurved: true,
              gradient: AppDesignTokens.primaryGradient,
              barWidth: 3,
              belowBarData: BarAreaData(
                show: true,
                gradient: LinearGradient(
                  colors: [
                    AppDesignTokens.primaryLight.withOpacity(0.3),
                    Colors.transparent,
                  ],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                ),
              ),
              dotData: FlDotData(
                show: true,
                getDotPainter: (spot, percent, barData, index) {
                  return FlDotCirclePainter(
                    radius: 4,
                    color: Colors.white,
                    strokeWidth: 2,
                    strokeColor: AppDesignTokens.primaryBase,
                  );
                },
              ),
            ),
          ],
        ),
      ),
    ),

    // 任务类型分布（饼图）
    StatisticsCard(
      title: '任务类型分布',
      subtitle: '最近30天',
      chart: PieChart(
        PieChartData(
          sections: taskTypeDistribution.entries.map((entry) {
            final colors = {
              'learning': AppDesignTokens.info,
              'training': AppDesignTokens.warning,
              'errorFix': AppDesignTokens.error,
              'reflection': Colors.purple,
              'social': AppDesignTokens.success,
              'planning': Colors.teal,
            };

            return PieChartSectionData(
              color: colors[entry.key] ?? AppDesignTokens.neutral500,
              value: entry.value.toDouble(),
              title: '${entry.value}',
              radius: 60,
              titleStyle: TextStyle(
                fontSize: AppDesignTokens.fontSizeSm,
                fontWeight: AppDesignTokens.fontWeightBold,
                color: Colors.white,
              ),
              gradient: LinearGradient(
                colors: [
                  colors[entry.key]!,
                  colors[entry.key]!.withOpacity(0.7),
                ],
              ),
            );
          }).toList(),
          sectionsSpace: 2,
          centerSpaceRadius: 40,
        ),
      ),
    ),

    // 学习时长统计（柱状图）
    StatisticsCard(
      title: '学习时长',
      subtitle: '本月累计 ${monthlyHours}小时',
      chart: BarChart(
        BarChartData(
          alignment: BarChartAlignment.spaceAround,
          maxY: 10,
          barTouchData: BarTouchData(enabled: true),
          titlesData: FlTitlesData(
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (value, meta) {
                  return Text('${value.toInt() + 1}周');
                },
              ),
            ),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (value, meta) {
                  return Text('${value.toInt()}h');
                },
              ),
            ),
          ),
          borderData: FlBorderData(show: false),
          barGroups: weeklyHours.asMap().entries.map((entry) {
            return BarChartGroupData(
              x: entry.key,
              barRods: [
                BarChartRodData(
                  toY: entry.value,
                  gradient: AppDesignTokens.primaryGradient,
                  width: 16,
                  borderRadius: BorderRadius.vertical(
                    top: Radius.circular(4),
                  ),
                ),
              ],
            );
          }).toList(),
        ),
      ),
    ),

    // 设置列表
    _buildSettingsList(),
  ],
)
```

##### 3) 数字滚动动画

```dart
class AnimatedNumber extends StatefulWidget {
  final int value;
  final Duration duration;

  @override
  _AnimatedNumberState createState() => _AnimatedNumberState();
}

class _AnimatedNumberState extends State<AnimatedNumber>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<int> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: widget.duration,
      vsync: this,
    );

    _animation = IntTween(begin: 0, end: widget.value).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOut),
    );

    _controller.forward();
  }

  @override
  void didUpdateWidget(AnimatedNumber oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.value != widget.value) {
      _animation = IntTween(
        begin: _animation.value,
        end: widget.value,
      ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOut));
      _controller.forward(from: 0);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        return Text('${_animation.value}');
      },
    );
  }
}

// 使用
AnimatedNumber(
  value: weeklyStats.total,
  duration: AppDesignTokens.durationSlow,
)
```

##### 4) 设置列表优化

```dart
Column(
  children: [
    // 分组标题
    Padding(
      padding: EdgeInsets.symmetric(
        horizontal: AppDesignTokens.spacing16,
        vertical: AppDesignTokens.spacing8,
      ),
      child: Align(
        alignment: Alignment.centerLeft,
        child: Text(
          '设置',
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
            color: AppDesignTokens.neutral600,
          ),
        ),
      ),
    ),

    // 设置项
    Container(
      margin: EdgeInsets.symmetric(horizontal: AppDesignTokens.spacing16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: AppDesignTokens.borderRadius12,
        boxShadow: AppDesignTokens.shadowSm,
      ),
      child: Column(
        children: [
          _buildSettingTile(
            icon: Icons.person_outline,
            iconGradient: AppDesignTokens.primaryGradient,
            title: '编辑资料',
            onTap: () {},
          ),
          Divider(height: 1, indent: 60),
          _buildSettingTile(
            icon: Icons.tune,
            iconGradient: AppDesignTokens.secondaryGradient,
            title: '学习偏好',
            onTap: () {},
          ),
          Divider(height: 1, indent: 60),
          _buildSettingTile(
            icon: Icons.notifications_outlined,
            iconGradient: AppDesignTokens.infoGradient,
            title: '通知设置',
            onTap: () {},
          ),
          Divider(height: 1, indent: 60),
          _buildSettingTile(
            icon: Icons.dark_mode_outlined,
            iconGradient: LinearGradient(
              colors: [AppDesignTokens.neutral700, AppDesignTokens.neutral900],
            ),
            title: '主题切换',
            trailing: AnimatedSwitcher(
              duration: AppDesignTokens.durationNormal,
              child: Switch(
                key: ValueKey(_isDarkMode),
                value: _isDarkMode,
                onChanged: (value) {
                  setState(() => _isDarkMode = value);
                  _toggleTheme();
                },
              ),
            ),
          ),
          Divider(height: 1, indent: 60),
          _buildSettingTile(
            icon: Icons.info_outline,
            iconGradient: AppDesignTokens.successGradient,
            title: '关于应用',
            onTap: () {},
          ),
        ],
      ),
    ),

    SizedBox(height: 24),

    // 登出按钮
    Container(
      margin: EdgeInsets.symmetric(horizontal: AppDesignTokens.spacing16),
      child: CustomButton.primary(
        text: '登出',
        icon: Icons.logout,
        onPressed: _logout,
        backgroundColor: AppDesignTokens.error,
      ),
    ),
  ],
)

Widget _buildSettingTile({
  required IconData icon,
  required LinearGradient iconGradient,
  required String title,
  Widget? trailing,
  VoidCallback? onTap,
}) {
  return ListTile(
    leading: Container(
      padding: EdgeInsets.all(8),
      decoration: BoxDecoration(
        gradient: iconGradient,
        borderRadius: AppDesignTokens.borderRadius8,
      ),
      child: Icon(icon, color: Colors.white, size: 20),
    ),
    title: Text(title),
    trailing: trailing ?? Icon(Icons.chevron_right),
    onTap: onTap,
  );
}
```

**依赖**: `fl_chart: ^0.66.0`
**预计改动**: +400行代码

---

### 阶段四：动画和交互增强

**时间**: 第3-4周
**优先级**: P1
**预计工作量**: 12小时

#### 4.1 页面转场动画

**修改文件**: `mobile/lib/app/routes.dart`

**实现内容**:

```dart
import 'package:animations/animations.dart';

final goRouter = GoRouter(
  routes: [
    GoRoute(
      path: '/tasks/:id',
      pageBuilder: (context, state) {
        return CustomTransitionPage(
          key: state.pageKey,
          child: TaskDetailScreen(taskId: state.pathParameters['id']!),
          transitionsBuilder: (context, animation, secondaryAnimation, child) {
            // 共享轴转场
            return SharedAxisTransition(
              animation: animation,
              secondaryAnimation: secondaryAnimation,
              transitionType: SharedAxisTransitionType.horizontal,
              child: child,
            );
          },
        );
      },
    ),

    // 聊天页面使用淡入淡出
    GoRoute(
      path: '/chat',
      pageBuilder: (context, state) {
        return CustomTransitionPage(
          key: state.pageKey,
          child: ChatScreen(),
          transitionsBuilder: (context, animation, secondaryAnimation, child) {
            return FadeThroughTransition(
              animation: animation,
              secondaryAnimation: secondaryAnimation,
              child: child,
            );
          },
        );
      },
    ),
  ],
);
```

**依赖**: `animations: ^2.0.11`

---

#### 4.2 列表动画

**新建文件**: `mobile/lib/core/animations/staggered_list_animation.dart`

```dart
class StaggeredListAnimation extends StatefulWidget {
  final Widget Function(BuildContext, int, Animation<double>) builder;
  final int itemCount;
  final Duration delay;
  final Duration duration;

  const StaggeredListAnimation({
    Key? key,
    required this.builder,
    required this.itemCount,
    this.delay = const Duration(milliseconds: 50),
    this.duration = const Duration(milliseconds: 350),
  }) : super(key: key);

  @override
  _StaggeredListAnimationState createState() => _StaggeredListAnimationState();
}

class _StaggeredListAnimationState extends State<StaggeredListAnimation>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: widget.duration,
      vsync: this,
    );
    _controller.forward();
  }

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      itemCount: widget.itemCount,
      itemBuilder: (context, index) {
        final delay = widget.delay.inMilliseconds * index;
        final animation = CurvedAnimation(
          parent: _controller,
          curve: Interval(
            delay / widget.duration.inMilliseconds,
            1.0,
            curve: Curves.easeOut,
          ),
        );

        return widget.builder(context, index, animation);
      },
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
}

// 使用示例
StaggeredListAnimation(
  itemCount: tasks.length,
  builder: (context, index, animation) {
    return FadeTransition(
      opacity: animation,
      child: SlideTransition(
        position: Tween<Offset>(
          begin: Offset(0, 0.1),
          end: Offset.zero,
        ).animate(animation),
        child: TaskCard(task: tasks[index]),
      ),
    );
  },
)
```

**预计代码量**: 100行

---

#### 4.3 手势交互

在TaskCard和ChatBubble中已实现（见阶段三）：
- ✅ 滑动删除/操作 (Dismissible)
- ✅ 长按菜单 (LongPress)
- ✅ 双击点赞（聊天气泡） - 待实现

**双击点赞实现**:

```dart
// ChatBubble中添加
GestureDetector(
  onDoubleTap: () {
    if (!isUser) {
      _showLikeAnimation();
      _onLike(message.id);
    }
  },
  child: _buildBubble(),
)

void _showLikeAnimation() {
  setState(() => _showHeart = true);
  Future.delayed(Duration(milliseconds: 800), () {
    if (mounted) {
      setState(() => _showHeart = false);
    }
  });
}

// 显示心形动画
if (_showHeart)
  Positioned.fill(
    child: Center(
      child: AnimatedScale(
        scale: _showHeart ? 1.5 : 0,
        duration: AppDesignTokens.durationSlow,
        curve: Curves.elasticOut,
        child: Icon(
          Icons.favorite,
          color: AppDesignTokens.error,
          size: 64,
        ),
      ),
    ),
  )
```

---

#### 4.4 骨架屏集成

在LoadingIndicator组件中已实现（见阶段二.2.2）

在各页面中使用：

```dart
// TaskListScreen
ref.watch(taskListProvider).when(
  data: (tasks) => ListView.builder(...),
  loading: () => LoadingIndicator.skeleton(
    type: SkeletonType.taskCard,
    count: 5,
  ),
  error: (error, stack) => CustomErrorWidget.page(...),
)

// ChatScreen
ref.watch(chatProvider).when(
  data: (messages) => ListView.builder(...),
  loading: () => LoadingIndicator.skeleton(
    type: SkeletonType.chatBubble,
    count: 3,
  ),
  error: (error, stack) => CustomErrorWidget.inline(...),
)

// ProfileScreen
ref.watch(statisticsProvider).when(
  data: (stats) => _buildStatistics(stats),
  loading: () => LoadingIndicator.skeleton(
    type: SkeletonType.profileCard,
    count: 1,
  ),
  error: (error, stack) => CustomErrorWidget.banner(...),
)
```

---

### 阶段五：细节打磨

**时间**: 第4周
**优先级**: P2
**预计工作量**: 12小时

#### 5.1 细节优化

1. **所有卡片添加微光高光**

```dart
// 在Container上添加foregroundDecoration
Container(
  decoration: BoxDecoration(...),
  foregroundDecoration: BoxDecoration(
    gradient: LinearGradient(
      colors: [
        Colors.white.withOpacity(0),
        Colors.white.withOpacity(0.1),
        Colors.white.withOpacity(0),
      ],
      stops: [0, 0.5, 1],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    ),
  ),
)
```

2. **渐变背景在dark模式下的适配**

```dart
// 在AppThemeExtension中添加darkGradients
final isDark = Theme.of(context).brightness == Brightness.dark;

Container(
  decoration: BoxDecoration(
    gradient: isDark
      ? LinearGradient(
          colors: [
            AppDesignTokens.neutral800.withOpacity(0.5),
            AppDesignTokens.neutral700.withOpacity(0.5),
          ],
        )
      : AppDesignTokens.primaryGradient,
  ),
)
```

3. **触觉反馈 (HapticFeedback)**

```dart
import 'package:flutter/services.dart';

// 按钮按下
onTapDown: (_) {
  HapticFeedback.lightImpact();
},

// 任务完成
onComplete: () {
  HapticFeedback.mediumImpact();
},

// 删除操作
onDelete: () {
  HapticFeedback.heavyImpact();
},

// 长按
onLongPress: () {
  HapticFeedback.vibrate();
},
```

4. **无障碍优化 (Semantics)**

```dart
Semantics(
  label: '任务卡片：${task.title}',
  hint: '点击查看任务详情，向右滑动标记完成，向左滑动删除',
  button: true,
  enabled: true,
  child: TaskCard(task: task),
)

Semantics(
  label: '火焰等级 ${user.flameLevel}，亮度 ${(user.flameBrightness * 100).toInt()}%',
  child: FlameIndicator(...),
)
```

---

#### 5.2 性能优化

1. **图片缓存策略**

```dart
// 使用cached_network_image
CachedNetworkImage(
  imageUrl: user.avatar,
  placeholder: (context, url) => Shimmer.fromColors(
    baseColor: AppDesignTokens.neutral200,
    highlightColor: AppDesignTokens.neutral100,
    child: Container(
      width: 80,
      height: 80,
      decoration: BoxDecoration(
        color: Colors.white,
        shape: BoxShape.circle,
      ),
    ),
  ),
  errorWidget: (context, url, error) => Icon(Icons.error),
  memCacheWidth: 200, // 限制缓存尺寸
  memCacheHeight: 200,
)
```

2. **列表懒加载**

```dart
ListView.builder(
  itemCount: tasks.length + 1,
  itemBuilder: (context, index) {
    if (index == tasks.length) {
      // 到达底部，加载更多
      if (hasMore && !isLoadingMore) {
        _loadMore();
      }
      return hasMore
        ? LoadingIndicator.circular()
        : SizedBox.shrink();
    }
    return TaskCard(task: tasks[index]);
  },
)
```

3. **动画性能优化**

```dart
// 使用AnimatedBuilder而不是setState
AnimatedBuilder(
  animation: _controller,
  builder: (context, child) {
    return Transform.rotate(
      angle: _controller.value * 2 * pi,
      child: child,
    );
  },
  child: Icon(Icons.refresh), // child不会重建
)

// 避免不必要的rebuild
const TaskCard(...) // 使用const构造

// 复杂widget使用RepaintBoundary
RepaintBoundary(
  child: ComplexChart(...),
)
```

4. **RepaintBoundary隔离**

```dart
// 独立动画区域
RepaintBoundary(
  child: AnimatedWidget(...),
)

// 图表区域
RepaintBoundary(
  child: LineChart(...),
)

// 列表项
ListView.builder(
  itemBuilder: (context, index) {
    return RepaintBoundary(
      child: TaskCard(task: tasks[index]),
    );
  },
)
```

---

#### 5.3 测试验证

1. **页面导航测试**

```dart
testWidgets('Navigate from task list to detail', (tester) async {
  await tester.pumpWidget(MyApp());

  // 点击任务卡片
  await tester.tap(find.byType(TaskCard).first);
  await tester.pumpAndSettle();

  // 验证导航到详情页
  expect(find.byType(TaskDetailScreen), findsOneWidget);
});
```

2. **动画流畅度测试**

```dart
testWidgets('Staggered animation completes smoothly', (tester) async {
  await tester.pumpWidget(TaskListScreen());

  // 等待动画完成
  await tester.pumpAndSettle(Duration(seconds: 2));

  // 验证所有项都已渲染
  expect(find.byType(TaskCard), findsNWidgets(5));
});
```

3. **真机测试清单**

- [ ] iOS设备测试（iPhone 12+）
- [ ] Android设备测试（Pixel 4+）
- [ ] 深色模式切换测试
- [ ] 滑动手势测试
- [ ] 动画帧率测试（保持60fps）
- [ ] 内存占用测试
- [ ] 网络慢速测试
- [ ] 触觉反馈测试
- [ ] 无障碍测试（VoiceOver/TalkBack）

---

## 时间估算

| 阶段 | 内容 | 工作量 | 优先级 | 周期 |
|-----|------|-------|--------|------|
| ✅ 阶段一 | 设计系统基础建设 | 8h | P0 | 第1周 |
| 阶段二 | 基础组件库实现 | 16h | P0 | 第1-2周 |
| 阶段三 | 核心页面优化 | 52h | P0-P1 | 第2-3周 |
| 阶段四 | 动画和交互增强 | 12h | P1 | 第3-4周 |
| 阶段五 | 细节打磨和测试 | 12h | P2 | 第4周 |
| **总计** | | **100h** | | **4周** |

### 团队并行工作估算

以4人团队并行工作：
- **阶段一**: 已完成（8小时，1人）
- **阶段二**: 16小时 ÷ 4人 = **4小时/人**（可并行开发6个组件）
- **阶段三**: 52小时 ÷ 4人 = **13小时/人**（可并行优化4个模块）
- **阶段四**: 12小时 ÷ 2人 = **6小时/人**（动画和交互）
- **阶段五**: 12小时 ÷ 4人 = **3小时/人**（细节和测试）

**总计**: 约**26小时/人** × 4人 = 104小时

**实际工期**: 考虑学习曲线和协作成本，预计**2-3周**完成核心功能（P0-P1）。

---

## 团队分工建议

### 方案一：按阶段分工

| 成员 | 负责阶段 | 工作内容 |
|------|---------|---------|
| 成员A | 阶段二 | 基础组件库（CustomButton, LoadingIndicator, ErrorWidget） |
| 成员B | 阶段三.1-3.4 | Dashboard + 任务流程优化 |
| 成员C | 阶段三.5 | 聊天界面优化 |
| 成员D | 阶段三.6 + 阶段四 | 个人资料 + 动画交互 |

### 方案二：按功能模块分工

| 成员 | 负责模块 | 工作内容 |
|------|---------|---------|
| 成员A | 设计系统 + 基础组件 | Design Tokens + 6个基础组件 |
| 成员B | Dashboard + 任务列表 | 主页优化 + TaskCard升级 + 列表页 |
| 成员C | 任务详情 + 执行 | TaskDetail + TaskExecution + Timer |
| 成员D | 聊天 + 个人资料 | Chat界面 + Profile + 统计图表 |

### 工作流程建议

1. **每日站会**（15分钟）
   - 同步进度
   - 讨论技术问题
   - 解决阻塞点

2. **Code Review**
   - 提交前相互review
   - 确保设计一致性
   - 统一代码风格

3. **真机测试**
   - 每完成一个模块立即测试
   - iOS和Android双平台验证
   - 记录性能数据

4. **文档更新**
   - 及时更新README
   - 记录关键决策
   - 维护组件使用文档

---

## 关键文件清单

### P0 - 必须完成（阶段一、二、三核心）

| # | 文件路径 | 状态 | 说明 |
|---|---------|------|------|
| 1 | `mobile/lib/core/design/design_tokens.dart` | ✅ 已完成 | 设计系统基石 |
| 2 | `mobile/lib/app/theme.dart` | ✅ 已完成 | 主题扩展 |
| 3 | `mobile/pubspec.yaml` | ✅ 已完成 | 依赖添加 |
| 4 | `mobile/lib/presentation/widgets/common/custom_button.dart` | ⏳ 待实现 | 全局按钮 |
| 5 | `mobile/lib/presentation/widgets/common/loading_indicator.dart` | ⏳ 待实现 | 加载状态 |
| 6 | `mobile/lib/presentation/widgets/common/error_widget.dart` | ⏳ 待实现 | 错误处理 |
| 7 | `mobile/lib/presentation/widgets/common/flame_indicator.dart` | ⏳ 待实现 | 火焰组件 |
| 8 | `mobile/lib/presentation/screens/home/home_screen.dart` | ⏳ 待优化 | Dashboard |
| 9 | `mobile/lib/presentation/widgets/task/task_card.dart` | ⏳ 待升级 | 任务卡片升级 |
| 10 | `mobile/lib/presentation/screens/task/task_list_screen.dart` | ⏳ 待优化 | 任务列表 |
| 11 | `mobile/lib/presentation/screens/task/task_detail_screen.dart` | ⏳ 待优化 | 任务详情 |
| 12 | `mobile/lib/presentation/widgets/chat/chat_bubble.dart` | ⏳ 待优化 | 聊天气泡Markdown |
| 13 | `mobile/lib/presentation/widgets/chat/action_card.dart` | ⏳ 待优化 | AI建议卡片 |
| 14 | `mobile/lib/presentation/screens/chat/chat_screen.dart` | ⏳ 待优化 | 聊天页面 |

### P1 - 重要（阶段三进阶 + 阶段四）

| # | 文件路径 | 状态 | 说明 |
|---|---------|------|------|
| 15 | `mobile/lib/presentation/screens/task/task_execution_screen.dart` | ⏳ 待优化 | 任务执行 |
| 16 | `mobile/lib/presentation/widgets/task/timer_widget.dart` | ⏳ 待升级 | 计时器 |
| 17 | `mobile/lib/presentation/screens/profile/profile_screen.dart` | ⏳ 待优化 | 个人资料 |
| 18 | `mobile/lib/presentation/widgets/profile/statistics_card.dart` | ⏳ 待创建 | 统计卡片 |
| 19 | `mobile/lib/app/routes.dart` | ⏳ 待优化 | 转场动画 |
| 20 | `mobile/lib/core/animations/staggered_list_animation.dart` | ⏳ 待创建 | 列表动画 |

### P2 - 增强（阶段五细节）

| # | 文件路径 | 状态 | 说明 |
|---|---------|------|------|
| 21 | `mobile/lib/presentation/widgets/common/empty_state.dart` | ⏳ 待创建 | 空状态 |
| 22 | `mobile/lib/presentation/widgets/common/success_animation.dart` | ⏳ 待创建 | 成功动画 |

---

## 后续步骤

### 立即开始（阶段二）

接下来应该实施**阶段二：基础组件库实现**，因为：

1. ✅ 阶段一（设计系统）已完成
2. 🎯 基础组件是所有页面的依赖
3. 📦 6个组件可并行开发
4. ⏱️ 预计16小时，4人并行只需4小时/人

**优先顺序**:
1. CustomButton（最高优先级，所有页面都需要）
2. LoadingIndicator（列表和异步操作需要）
3. FlameIndicator（Dashboard需要）
4. ErrorWidget（错误处理）
5. EmptyState（空状态展示）
6. SuccessAnimation（锦上添花）

### 中期里程碑（阶段三）

完成基础组件后，进入**核心页面优化**：
- Week 2-3: Dashboard + 任务流程 + 聊天界面
- 预计52小时，分4个子模块并行

### 最终打磨（阶段四、五）

- Week 3-4: 动画交互 + 细节打磨
- 预计24小时，全员参与

---

## 风险和注意事项

### 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 动画性能问题 | 中 | 使用RepaintBoundary，真机测试，避免过度动画 |
| 图表库兼容性 | 低 | fl_chart成熟稳定，文档完善 |
| Markdown渲染复杂度 | 中 | flutter_markdown已验证，先支持基础语法 |
| 暗色模式适配遗漏 | 中 | 每个组件都测试Light/Dark模式 |

### 项目风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 时间紧张 | 高 | 聚焦P0和P1，P2可选 |
| 团队学习曲线 | 中 | 提供详细文档，配对编程 |
| 设计一致性 | 中 | Code Review，使用Design Tokens |
| 功能回归 | 低 | 充分测试，保持向后兼容 |

### 最佳实践

1. **严格遵循Design Tokens** - 所有样式从tokens获取，禁止硬编码
2. **组件优先** - 先完成基础组件，再优化页面
3. **增量发布** - 每完成一个模块合并一次
4. **真机测试** - 不依赖模拟器，及时发现性能问题
5. **文档同步** - 代码和文档同步更新

---

## 总结

本UI优化计划将在**2-4周**内将Sparkle应用从基础UI提升到**专业精致、高端质感**的水准。通过：

- ✅ **设计系统标准化** - 完整的Design Tokens + 主题扩展
- 🎨 **组件库完善** - 6个基础组件 + 业务组件升级
- 🚀 **核心页面优化** - Dashboard/任务/聊天/个人资料全面提升
- ✨ **丰富的微交互** - 流畅动画 + 手势交互 + 细节打磨

最终打造一个**专业、精致、流畅**的学习助手应用，助力团队在2025年2月2日前完成MVP，赢得软件创新竞赛！

---

**文档维护者**: Claude Code
**技术支持**: sparkle-flutter团队
**最后更新**: 2025年12月16日

---

## 附录

### A. 依赖版本清单

```yaml
dependencies:
  flutter_riverpod: ^2.4.9
  go_router: ^13.0.0
  dio: ^5.4.0

  # UI Enhancement (新增)
  flutter_markdown: ^0.6.18
  lottie: ^3.0.0
  animations: ^2.0.11
  fl_chart: ^0.66.0
  shimmer: ^3.0.0
  confetti: ^0.7.0
```

### B. 设计资源

- **Figma设计稿**: 待补充
- **Logo和图标**: 待补充
- **Lottie动画文件**: 待补充
- **字体文件**: 待补充

### C. 参考资料

- [Material Design 3 Guidelines](https://m3.material.io/)
- [Flutter Animation Cookbook](https://docs.flutter.dev/cookbook/animation)
- [fl_chart Documentation](https://pub.dev/packages/fl_chart)
- [flutter_markdown Guide](https://pub.dev/packages/flutter_markdown)

---

**🎉 Let's build something amazing together!**
