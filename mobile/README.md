# Sparkle Mobile - Flutter 客户端

> ✨ 星火 AI 学习助手 - 点燃你的学习潜力

## 项目概述

Sparkle 是一款 AI 驱动的学习助手应用，帮助用户通过智能任务管理、个性化学习计划和 AI 微导师来提升学习效率。

## 技术栈

- **Framework**: Flutter 3.x
- **语言**: Dart 3.x
- **状态管理**: Riverpod 2.4.9 (StateNotifier, Provider)
- **网络请求**: Dio 5.4.0 (HTTP Client + 拦截器)
- **路由**: GoRouter 13.0.0 (声明式路由 + 认证保护)
- **本地存储**: SharedPreferences (配置), Hive (缓存)
- **代码生成**:
  - build_runner (代码生成工具)
  - json_serializable (JSON 序列化)
  - riverpod_generator (Provider 生成)
- **UI 组件**:
  - Material Design 3
  - 自定义主题系统
  - 响应式布局
- **工具库**:
  - flutter_svg (SVG 图标)
  - intl (国际化/日期格式)
  - uuid (唯一标识符)
  - fl_chart (图表统计)
  - graphview (知识图谱可视化)

## 快速开始

### 1. 安装依赖

```bash
cd mobile
flutter pub get
```

### 2. 生成代码

运行代码生成以创建 JSON 序列化代码：

```bash
# 使用脚本（推荐）
./scripts/generate.sh

# 或手动运行
flutter packages pub run build_runner build --delete-conflicting-outputs
```

### 3. 配置后端地址

编辑 [lib/core/network/api_endpoints.dart](lib/core/network/api_endpoints.dart)：

```dart
class ApiEndpoints {
  // 修改为你的后端地址
  static const String baseUrl = 'http://localhost:8000/api/v1';
  // ...
}
```

### 4. 运行应用

```bash
# 开发模式
flutter run

# 生产模式
flutter run --release
```

## 项目结构

```
lib/
├── app/                    # 应用配置
│   ├── app.dart           # 应用根组件（ProviderScope + MaterialApp）
│   ├── routes.dart        # 路由配置（GoRouter + 认证守卫）
│   └── theme.dart         # 主题配置（亮色/暗色）
├── core/                  # 核心功能
│   ├── constants/         # 常量定义
│   │   ├── api_constants.dart
│   │   └── app_constants.dart
│   ├── errors/           # 错误处理
│   │   └── exceptions.dart
│   ├── network/          # 网络层
│   │   ├── api_client.dart        # Dio 客户端封装
│   │   ├── api_interceptor.dart   # 认证拦截器
│   │   ├── idempotency_interceptor.dart  # 幂等性拦截器
│   │   └── api_endpoints.dart     # API 端点定义
│   └── utils/            # 工具函数
│       ├── date_formatter.dart
│       └── validators.dart
├── data/                 # 数据层
│   ├── models/           # 数据模型（带 JSON 序列化）
│   │   ├── user_model.dart
│   │   ├── task_model.dart
│   │   ├── plan_model.dart
│   │   ├── chat_message_model.dart
│   │   ├── knowledge_node_model.dart
│   │   ├── push_settings_model.dart
│   │   ├── statistics_model.dart
│   │   └── api_response_model.dart
│   └── repositories/     # 数据仓库（API 调用）
│       ├── auth_repository.dart
│       ├── task_repository.dart
│       ├── plan_repository.dart
│       ├── chat_repository.dart
│       ├── knowledge_repository.dart
│       ├── push_repository.dart
│       └── statistics_repository.dart
├── presentation/         # 展示层
│   ├── providers/        # Riverpod 状态管理
│   │   ├── auth_provider.dart
│   │   ├── task_provider.dart
│   │   ├── plan_provider.dart
│   │   ├── chat_provider.dart
│   │   ├── knowledge_provider.dart
│   │   ├── push_provider.dart
│   │   └── statistics_provider.dart
│   ├── screens/          # 页面
│   │   ├── splash/       # 启动页
│   │   ├── auth/         # 登录/注册
│   │   ├── home/         # 主页
│   │   ├── task/         # 任务管理
│   │   ├── chat/         # AI 对话
│   │   ├── plan/         # 计划管理
│   │   ├── knowledge/    # 知识星图
│   │   ├── profile/      # 个人中心
│   │   └── statistics/   # 统计数据
│   └── widgets/          # 可复用组件
│       ├── common/       # 通用组件（按钮、输入框、卡片）
│       ├── task/         # 任务相关组件（任务卡片、计时器）
│       ├── chat/         # 对话组件（气泡、Action Card）
│       ├── knowledge/    # 知识图谱组件
│       └── push/         # 推送设置组件
└── main.dart            # 应用入口
```

## 核心功能

### ✅ 已实现

#### 基础架构
- [x] 用户认证（登录/注册/游客模式）
- [x] JWT Token 自动刷新
- [x] 全局导航系统（GoRouter）
- [x] 路由保护和认证拦截
- [x] 统一的网络请求封装（Dio + 拦截器）
- [x] 完整的数据模型定义（JSON 序列化）
- [x] 亮色/暗色主题支持
- [x] 幂等性请求处理

#### 核心功能
- [x] **任务管理系统**
  - 任务 CRUD 操作
  - 任务状态管理（待办/进行中/已完成/已放弃）
  - 任务类型分类（学习/训练/纠错/反思/社交/规划）
  - 任务执行计时器（番茄钟）
- [x] **AI 对话系统**
  - 与 AI 微导师实时对话
  - 智能任务卡片生成
  - 对话历史管理
  - Action Card 动态展示
- [x] **计划管理**
  - 冲刺计划（Sprint Plan）
  - 成长计划（Growth Plan）
  - AI 辅助计划生成
- [x] **知识星图**
  - 知识图谱可视化
  - 知识点关联展示
  - 掌握度追踪
- [x] **个人中心**
  - 用户资料展示
  - 火花等级/亮度可视化
  - 推送偏好设置
  - 通知权限管理
- [x] **统计数据展示**
  - 学习时长统计
  - 任务完成率
  - 火花成长曲线
- [x] **智能推送系统**
  - 推送偏好配置
  - 通知权限引导
  - 推送历史查看

### 🚧 进行中

- [ ] 错题档案管理
- [ ] 知识星图交互优化
- [ ] 推送通知本地集成

### 📋 待开发

- [ ] 离线数据缓存
- [ ] 多语言支持（国际化）
- [ ] 数据导出功能
- [ ] 学习报告生成

## 开发指南

### 添加新的数据模型

1. 在 `lib/data/models/` 创建模型文件
2. 使用 `@JsonSerializable()` 注解
3. 运行代码生成

```dart
import 'package:json_annotation/json_annotation.dart';

part 'my_model.g.dart';

@JsonSerializable()
class MyModel {
  final String id;
  final String name;

  MyModel({required this.id, required this.name});

  factory MyModel.fromJson(Map<String, dynamic> json) =>
      _$MyModelFromJson(json);
  Map<String, dynamic> toJson() => _$MyModelToJson(this);
}
```

### 添加新的 API 端点

编辑 `lib/core/network/api_endpoints.dart`：

```dart
class ApiEndpoints {
  // 添加新端点
  static const String myNewEndpoint = '/my/endpoint';
  static String myEndpointWithId(String id) => '/my/endpoint/$id';
}
```

### 创建新的 Repository

```dart
class MyRepository {
  final ApiClient _apiClient;

  MyRepository(this._apiClient);

  Future<MyModel> getItem(String id) async {
    final response = await _apiClient.get(
      ApiEndpoints.myEndpointWithId(id),
    );
    return MyModel.fromJson(response.data);
  }
}

// Provider
final myRepositoryProvider = Provider<MyRepository>((ref) {
  return MyRepository(ref.read(apiClientProvider));
});
```

### 创建状态管理

```dart
class MyState {
  final bool isLoading;
  final List<MyModel> items;
  final String? error;

  MyState({
    this.isLoading = false,
    this.items = const [],
    this.error,
  });

  MyState copyWith({...}) { ... }
}

class MyNotifier extends StateNotifier<MyState> {
  final MyRepository _repository;

  MyNotifier(this._repository) : super(MyState());

  Future<void> loadItems() async {
    state = state.copyWith(isLoading: true);
    try {
      final items = await _repository.getItems();
      state = state.copyWith(isLoading: false, items: items);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }
}

final myProvider = StateNotifierProvider<MyNotifier, MyState>((ref) {
  return MyNotifier(ref.watch(myRepositoryProvider));
});
```

## 常用命令

```bash
# 获取依赖
flutter pub get

# 代码生成
flutter packages pub run build_runner build --delete-conflicting-outputs

# 代码生成（监听模式）
flutter packages pub run build_runner watch

# 运行应用
flutter run

# 构建 APK
flutter build apk --release

# 构建 iOS
flutter build ios --release

# 分析代码
flutter analyze

# 格式化代码
dart format .

# 运行测试
flutter test
```

## 代码规范

- 使用 `flutter_lints` 进行代码检查
- 所有文件必须包含头部注释
- 变量和函数命名使用 camelCase
- 类命名使用 PascalCase
- 常量使用 UPPER_SNAKE_CASE
- 私有成员使用 `_` 前缀

## 环境变量

创建 `.env` 文件（未来）：

```env
API_BASE_URL=http://localhost:8000/api/v1
```

## 故障排除

### build_runner 错误

```bash
# 清理构建缓存
flutter clean
flutter pub get
rm -rf .dart_tool/build

# 重新生成
flutter packages pub run build_runner build --delete-conflicting-outputs
```

### 依赖冲突

```bash
flutter pub upgrade --major-versions
```

### iOS 构建问题

```bash
cd ios
pod deintegrate
pod install
cd ..
```

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

待定

## 联系方式

- 项目链接: [https://github.com/yourusername/sparkle](https://github.com/yourusername/sparkle)
- 问题反馈: [Issues](https://github.com/yourusername/sparkle/issues)

---

Made with ❤️ and 🔥 by Sparkle Team
