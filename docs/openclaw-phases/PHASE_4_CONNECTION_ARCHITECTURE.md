# Phase 4: 连接架构 — "本地到远程的平滑迁移"

> **交给Coding Agent执行的完整指令**
> **预计改动**: 4个新文件, 4个修改文件 (Flutter + Python后端)
> **依赖**: Phase 1 已完成 (需要执行UI组件)

---

## 背景

当前OpenClaw连接配置硬编码在后端环境变量中(OPENCLAW_GATEWAY_URL, OPENCLAW_AUTH_TOKEN等)。用户无法在Mobile端管理连接。本阶段目标:

1. **本地连接**: 用户在设置页配置自己的OpenClaw实例地址, 移动端直连
2. **连接管理**: 测试、状态监控、断连降级
3. **安全配对**: 设备码配对机制

暂不实现远程中继(Phase 6), 但架构设计要为其预留接口。

### 关键现有代码

- `backend/app/adapters/openclaw/config.py` — OpenClawConfig dataclass
- `backend/app/adapters/openclaw/client.py` — OpenClawClient transport
- `backend/app/api/v1/executions.py` — /health endpoint
- `mobile/lib/core/network/api_endpoints.dart` — API端点常量
- `mobile/lib/features/task/data/repositories/task_repository.dart` — 执行API调用

---

## 任务 4.1: Flutter — 创建OpenClaw连接管理服务

**创建文件**: `mobile/lib/core/services/openclaw_connection_service.dart`

### 设计规格

管理OpenClaw连接的状态、配置持久化、健康检查。

```dart
import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

enum OpenClawConnectionStatus {
  disconnected,
  connecting,
  connected,
  error,
}

class OpenClawConnectionConfig {
  final String gatewayUrl;
  final String? authToken;
  final String? deviceToken;
  final String transport; // "responses_http" | "gateway_ws"
  final DateTime? pairedAt;

  const OpenClawConnectionConfig({
    required this.gatewayUrl,
    this.authToken,
    this.deviceToken,
    this.transport = 'responses_http',
    this.pairedAt,
  });

  bool get isConfigured => gatewayUrl.isNotEmpty;
  bool get isPaired => deviceToken != null && deviceToken!.isNotEmpty;

  Map<String, dynamic> toJson() => {
    'gateway_url': gatewayUrl,
    'auth_token': authToken,
    'device_token': deviceToken,
    'transport': transport,
    'paired_at': pairedAt?.toIso8601String(),
  };

  factory OpenClawConnectionConfig.fromJson(Map<String, dynamic> json) =>
    OpenClawConnectionConfig(
      gatewayUrl: json['gateway_url'] as String? ?? '',
      authToken: json['auth_token'] as String?,
      deviceToken: json['device_token'] as String?,
      transport: json['transport'] as String? ?? 'responses_http',
      pairedAt: json['paired_at'] != null ? DateTime.tryParse(json['paired_at'] as String) : null,
    );

  static const empty = OpenClawConnectionConfig(gatewayUrl: '');
}

class OpenClawConnectionInfo {
  final OpenClawConnectionStatus status;
  final int? latencyMs;
  final int? nodeCount;
  final List<String>? capabilities;
  final String? errorMessage;
  final DateTime? lastCheckedAt;

  const OpenClawConnectionInfo({
    this.status = OpenClawConnectionStatus.disconnected,
    this.latencyMs,
    this.nodeCount,
    this.capabilities,
    this.errorMessage,
    this.lastCheckedAt,
  });
}

class OpenClawConnectionService extends ChangeNotifier {
  static const _configKey = 'openclaw_connection_config';
  static const _healthCheckIntervalSeconds = 30;

  OpenClawConnectionConfig _config = OpenClawConnectionConfig.empty;
  OpenClawConnectionInfo _info = const OpenClawConnectionInfo();
  Timer? _healthTimer;

  OpenClawConnectionConfig get config => _config;
  OpenClawConnectionInfo get info => _info;
  bool get isConnected => _info.status == OpenClawConnectionStatus.connected;

  /// Load saved config from SharedPreferences.
  Future<void> initialize() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_configKey);
    if (raw != null) {
      try {
        _config = OpenClawConnectionConfig.fromJson(
          jsonDecode(raw) as Map<String, dynamic>,
        );
        if (_config.isConfigured) {
          unawaited(checkHealth());
          _startHealthMonitor();
        }
      } catch (_) {
        // Corrupt config, ignore
      }
    }
  }

  /// Save connection config and immediately test it.
  Future<bool> configure(OpenClawConnectionConfig newConfig) async {
    _config = newConfig;

    // Persist
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_configKey, jsonEncode(newConfig.toJson()));

    // Test connection
    final ok = await checkHealth();

    if (ok) {
      _startHealthMonitor();
    }

    notifyListeners();
    return ok;
  }

  /// Test connection to the configured OpenClaw instance.
  Future<bool> checkHealth() async {
    if (!_config.isConfigured) {
      _info = const OpenClawConnectionInfo(
        status: OpenClawConnectionStatus.disconnected,
      );
      notifyListeners();
      return false;
    }

    _info = OpenClawConnectionInfo(
      status: OpenClawConnectionStatus.connecting,
      lastCheckedAt: DateTime.now(),
    );
    notifyListeners();

    try {
      final stopwatch = Stopwatch()..start();
      final uri = Uri.parse('${_config.gatewayUrl}/health');
      final headers = <String, String>{};
      if (_config.authToken != null) {
        headers['Authorization'] = 'Bearer ${_config.authToken}';
      }

      final response = await http.get(uri, headers: headers).timeout(
        const Duration(seconds: 10),
      );
      stopwatch.stop();

      if (response.statusCode == 200) {
        Map<String, dynamic>? body;
        try {
          body = jsonDecode(response.body) as Map<String, dynamic>?;
        } catch (_) {}

        _info = OpenClawConnectionInfo(
          status: OpenClawConnectionStatus.connected,
          latencyMs: stopwatch.elapsedMilliseconds,
          nodeCount: body?['node_count'] as int?,
          capabilities: (body?['capabilities'] as List?)?.cast<String>(),
          lastCheckedAt: DateTime.now(),
        );
      } else {
        _info = OpenClawConnectionInfo(
          status: OpenClawConnectionStatus.error,
          latencyMs: stopwatch.elapsedMilliseconds,
          errorMessage: 'HTTP ${response.statusCode}',
          lastCheckedAt: DateTime.now(),
        );
      }
    } catch (e) {
      _info = OpenClawConnectionInfo(
        status: OpenClawConnectionStatus.error,
        errorMessage: e.toString(),
        lastCheckedAt: DateTime.now(),
      );
    }

    notifyListeners();
    return _info.status == OpenClawConnectionStatus.connected;
  }

  /// Disconnect and clear config.
  Future<void> disconnect() async {
    _healthTimer?.cancel();
    _healthTimer = null;
    _config = OpenClawConnectionConfig.empty;
    _info = const OpenClawConnectionInfo();

    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_configKey);

    notifyListeners();
  }

  void _startHealthMonitor() {
    _healthTimer?.cancel();
    _healthTimer = Timer.periodic(
      const Duration(seconds: _healthCheckIntervalSeconds),
      (_) => checkHealth(),
    );
  }

  @override
  void dispose() {
    _healthTimer?.cancel();
    super.dispose();
  }
}
```

---

## 任务 4.2: Flutter — 创建OpenClaw设置页面

**创建文件**: `mobile/lib/features/settings/presentation/screens/openclaw_settings_screen.dart`

### 设计规格

设置页中的"AI执行引擎"子页面, 管理OpenClaw连接。

```dart
// 文件结构指引, Agent需要完整实现

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_motion_primitives.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
```

#### 页面结构

**AppBar**: 标题 "AI执行引擎", 无特殊操作

**Body** (SingleChildScrollView):

**1. 连接状态卡 (始终显示)**
- `DS.surfaceSecondary` 背景, 圆角16
- 顶部: 状态指示灯(12px圆形) + 状态文字
  - disconnected: 灰色 + "未连接"
  - connecting: 蓝色闪烁 + "连接中..."
  - connected: 绿色 + "已连接" + 延迟badge("32ms")
  - error: 红色 + "连接失败" + 错误信息
- 中间(仅connected): 节点数 + 能力列表(Wrap chips)
- 底部(仅connected): 上次检查时间 "30秒前检查"

**2. 连接配置区 (表单)**
- 网关地址输入框: `TextField`, hint "http://localhost:8080", 自动trim
  - 验证: 必须以http://或https://开头
- 认证方式选择: SegmentedButton — "令牌认证" | "设备配对"
  - 令牌模式: 显示密码输入框(obscureText: true), hint "输入认证令牌"
  - 配对模式: 显示设备令牌输入框 + "扫码配对"按钮(预留, 暂显示Snackbar "即将推出")
- 传输协议选择: SegmentedButton — "HTTP" | "WebSocket"
  - HTTP: responses_http
  - WebSocket: gateway_ws

**3. 操作按钮**
- "测试连接" — OutlinedButton, 点击后调用checkHealth(), 按钮显示loading状态
  - 成功: 播放 `SensoryFeedbackEvent.success`, 显示绿色SnackBar "连接成功"
  - 失败: 播放 `SensoryFeedbackEvent.error`, 显示红色SnackBar + 错误信息
- "保存配置" — FilledButton, DS.brandPrimary
  - 点击后调用configure(), 成功则自动测试连接
- "断开连接" — TextButton, DS.semanticError (仅当已连接时显示)
  - 弹出确认Dialog后调用disconnect()

**4. 信息区 (仅未连接时显示)**
- 标题: "什么是AI执行引擎?"
- 说明文字(DS.textSecondary, fontSize 13):
  "AI执行引擎(OpenClaw)可以自动完成网页调研、文档整理等任务。
  你可以在自己的电脑上运行OpenClaw, 然后在这里连接它。"
- "了解更多" TextButton (预留, 暂无跳转)

#### Provider

使用 `ChangeNotifierProvider` 包装 `OpenClawConnectionService`:

```dart
final openClawConnectionProvider = ChangeNotifierProvider<OpenClawConnectionService>((ref) {
  final service = OpenClawConnectionService();
  service.initialize(); // 异步初始化
  return service;
});
```

这个provider定义放在 `mobile/lib/core/services/openclaw_connection_service.dart` 文件底部, 或者放在一个独立的providers文件中, 与项目现有的provider组织方式保持一致。

---

## 任务 4.3: Flutter — 将设置页入口加入设置列表

**修改文件**: 找到设置页面的主列表文件 (通常在 `mobile/lib/features/settings/` 目录下)

### 修改目标

在设置列表中添加"AI执行引擎"入口项。

### 精确修改

在设置列表的合适位置(建议在"账号"/"通知"附近), 添加一个ListTile:

```dart
ListTile(
  leading: Icon(Icons.smart_toy_rounded, color: DS.brandPrimary),
  title: const Text('AI执行引擎'),
  subtitle: Consumer(
    builder: (context, ref, _) {
      final connection = ref.watch(openClawConnectionProvider);
      return Text(
        connection.isConnected ? '已连接' : '未连接',
        style: TextStyle(
          color: connection.isConnected ? DS.semanticSuccess : DS.textTertiary,
          fontSize: 13,
        ),
      );
    },
  ),
  trailing: const Icon(Icons.chevron_right_rounded),
  onTap: () => Navigator.push(
    context,
    MaterialPageRoute(builder: (_) => const OpenClawSettingsScreen()),
  ),
),
```

需要添加import:
```dart
import 'package:sparkle/features/settings/presentation/screens/openclaw_settings_screen.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
```

---

## 任务 4.4: 后端 — 连接配置API (用户级)

**修改文件**: `backend/app/api/v1/executions.py`

### 修改目标

允许用户通过API设置自己的OpenClaw连接(未来用于多用户场景, 每个用户连接自己的OpenClaw)。当前阶段作为server-side配置的补充。

### 精确修改

在现有endpoint列表末尾添加:

```python
@router.get("/connection/status")
async def get_connection_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get current OpenClaw connection status for the user."""
    from app.adapters.openclaw.config import OpenClawConfig
    from app.adapters.openclaw.client import OpenClawClient

    config = OpenClawConfig.from_settings()
    if not config.enabled:
        return {
            "connected": False,
            "enabled": False,
            "message": "OpenClaw integration is not enabled on this server.",
        }

    # 尝试健康检查
    try:
        client = OpenClawClient(config)
        health = await client.health_check()
        return {
            "connected": True,
            "enabled": True,
            "latency_ms": health.get("latency_ms"),
            "node_count": health.get("node_count"),
            "capabilities": health.get("capabilities", []),
            "transport": config.transport,
        }
    except Exception as e:
        return {
            "connected": False,
            "enabled": True,
            "error": str(e),
            "transport": config.transport,
        }
```

**注意**: 你需要检查 `OpenClawClient` 是否有 `health_check()` 方法。如果没有, 需要添加一个简单的健康检查方法:

在 `backend/app/adapters/openclaw/client.py` 中添加:

```python
async def health_check(self) -> dict[str, Any]:
    """Check OpenClaw gateway health."""
    import time
    start = time.monotonic()

    if self._config.transport == "responses_http":
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._config.gateway_url}/health",
                headers=self._auth_headers(),
                timeout=10.0,
            )
            resp.raise_for_status()
            latency = int((time.monotonic() - start) * 1000)
            data = resp.json()
            data["latency_ms"] = latency
            return data
    else:
        # WS mode: 简单连接测试
        # 如果gateway_ws_client有连接测试方法则使用, 否则返回基本信息
        return {
            "latency_ms": None,
            "transport": "gateway_ws",
            "status": "configured",
        }
```

---

## 任务 4.5: Flutter — 执行UI中的连接状态感知

**修改文件**: `mobile/lib/features/task/presentation/screens/task_execution_screen.dart`

### 修改目标

当OpenClaw未连接时, "交给AI执行"按钮显示为禁用状态, 并提示用户去设置连接。

### 精确修改

在 `_BottomControls` 的build方法中(Phase 1重构后的handoff按钮区域), 添加连接状态检查:

```dart
// 在build方法顶部, 读取连接状态
final connection = ref.watch(openClawConnectionProvider);
final isClawConnected = connection.isConnected;
```

修改handoff按钮的渲染逻辑:

```dart
if (canHandoff)
  Column(
    children: [
      if (!isClawConnected)
        Padding(
          padding: const EdgeInsets.only(bottom: DS.spacing8),
          child: InkWell(
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const OpenClawSettingsScreen()),
            ),
            borderRadius: BorderRadius.circular(12),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: DS.spacing12, vertical: DS.spacing8),
              decoration: BoxDecoration(
                color: DS.semanticWarning.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.link_off_rounded, size: 16, color: DS.semanticWarning),
                  const SizedBox(width: DS.spacing6),
                  Text(
                    'AI执行引擎未连接, 点击设置',
                    style: TextStyle(fontSize: 12, color: DS.semanticWarning),
                  ),
                  const SizedBox(width: DS.spacing4),
                  Icon(Icons.chevron_right_rounded, size: 14, color: DS.semanticWarning),
                ],
              ),
            ),
          ),
        ),
      SizedBox(
        width: double.infinity,
        height: 48,
        child: FilledButton.icon(
          onPressed: (!isClawConnected || isHandoffLoading) ? null : () {
            SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm);
            _handoffTask(ref, taskId);
          },
          // ... 其他属性同Phase 1
        ),
      ),
    ],
  ),
```

需要添加import:
```dart
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/features/settings/presentation/screens/openclaw_settings_screen.dart';
```

---

## 任务 4.6: Flutter — 连接状态栏全局指示

**修改文件**: `mobile/lib/core/network/api_endpoints.dart`

### 精确修改

添加连接状态查询端点:

```dart
static String get openclawConnectionStatus => '/executions/connection/status';
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

1. [ ] 设置页显示"AI执行引擎"入口, 连接状态正确显示
2. [ ] OpenClaw设置页: 输入地址→测试连接→成功显示绿色状态+延迟+节点数
3. [ ] 连接失败时: 红色状态+具体错误信息
4. [ ] 配置保存后持久化, 重启App后自动恢复连接
5. [ ] 30秒健康检查周期正常运行
6. [ ] 断开连接: 确认Dialog→清除配置→状态变为未连接
7. [ ] 任务详情页: 未连接时handoff按钮禁用+显示"未连接"提示, 点击可跳转设置
8. [ ] 已连接时handoff按钮正常可用
9. [ ] GET /executions/connection/status 返回正确状态
