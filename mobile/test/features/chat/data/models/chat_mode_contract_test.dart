import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/models/chat_mode.dart';

/// F-6 回归契约（wt324 实测 major）：`chat_mode=growth` 全链静默死。
///
/// 缺陷：home 两个卡点入口（today_cockpit_card._openStuckChat /
/// dashboard_screen._openBottleneckChat）发送 `'chat_mode': 'growth'`，
/// 而后端 `backend/app/orchestration/chat_modes.py` 的
/// SUPPORTED_CHAT_MODES = {standard, deep_analysis, study_plan,
/// error_diagnosis, expert_auto}（+ expert::/team:: 前缀）并无 growth；
/// `ChatMode.fromApiValue('growth')` 静默回落 standard，mode 条形同虚设。
///
/// 裁决（REPORT §F-6）：growth 非后端真实支持的 mode → 调用侧改用语义
/// 最近的既有 mode（卡点突破=诊断并分析瓶颈 → deep_analysis），删死字符串；
/// `orElse` 静默回落保留（与后端 normalize_chat_mode 的兼容回落契约一致）。
void main() {
  group('ChatMode 契约（F-6）', () {
    test('mobile 枚举与后端 SUPPORTED_CHAT_MODES 逐值对齐', () {
      const backendSupported = {
        'standard',
        'deep_analysis',
        'study_plan',
        'error_diagnosis',
        'expert_auto',
      };
      final mobileValues = chatModeValues.map((m) => m.apiValue).toSet();
      expect(mobileValues, equals(backendSupported));
    });

    test('home 卡点入口不再发送死字符串 growth', () {
      // 守卫面：home 层源码不得再出现 chat_mode: 'growth' 字面量。
      // （widget 级验证需渲染 cockpit vm，超出本契约测试范围；此处钉死
      // 死字符串回归——任何路径再写 growth 即红。）
      final sources = [
        File('test/features/../../lib/features/home/presentation/widgets/today_cockpit_card.dart'),
        File('test/features/../../lib/features/home/presentation/screens/dashboard_screen.dart'),
      ];
      for (final source in sources) {
        expect(
          source.existsSync(),
          isTrue,
          reason: '源文件缺失: ${source.path}',
        );
        final forbidden = RegExp(r"'chat_mode':\s*'growth'");
        expect(
          forbidden.hasMatch(source.readAsStringSync()),
          isFalse,
          reason: '${source.path} 仍发送后端不支持的 chat_mode=growth',
        );
      }
    });

    test('卡点入口使用的 deep_analysis 可被 fromApiValue 精确解析', () {
      final mode = ChatMode.fromApiValue('deep_analysis');
      expect(mode.apiValue, equals('deep_analysis'));
      expect(mode.isMultiAgent, isTrue);
    });

    test('未知值静默回落 standard 是与后端一致的兼容契约（文档化）', () {
      // 后端 normalize_chat_mode 对未知值回落 standard；mobile orElse 同。
      // 此测试固化该双向契约，防止一侧单方面改为抛错。
      final mode = ChatMode.fromApiValue('growth');
      expect(mode.apiValue, equals('standard'));
    });
  });
}
