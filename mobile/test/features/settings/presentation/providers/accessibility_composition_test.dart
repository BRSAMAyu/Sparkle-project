// V4-F06 · app 壳无障碍组装律（settings 模块单一权威实现面，验收③的
// 叠加律/字阶组合基础面）。
//
// 规则源：accessibility_provider.composeDisableAnimations /
// composeAccessibleNavigation / composeAppTextScaler（app.dart 委托至此，
// A-SPEC6 N31 叠加律：app 内设置是系统设置的叠加/乘数，不是替换）。
//
// 正例 I+：双源并集（任一源开即生效）+ 字阶组合（系统夹窗 × app 倍率）；
// 反例 I-（探针活性）：AND 组合与替换组合对同一输入产出不同值——
// 两种错误实现都会被本探针判负，钉死叠加律不是恒真断言。
import 'package:flutter/painting.dart' show TextScaler;
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/settings/presentation/providers/accessibility_provider.dart';

void main() {
  group('验收③ · app 壳无障碍组装律（N31 叠加律）', () {
    test('I+：disableAnimations = 系统 ∨ app 内（两源任一生效）', () {
      expect(
        composeDisableAnimations(system: false, inApp: false),
        isFalse,
        reason: '双关才是关',
      );
      expect(
        composeDisableAnimations(system: true, inApp: false),
        isTrue,
        reason: '系统减弱动效不被 app 默认关掉',
      );
      expect(
        composeDisableAnimations(system: false, inApp: true),
        isTrue,
        reason: 'app 内减弱动效在系统未开时同样生效（直读 platformDispatcher 的旧实现漏这半边）',
      );
      expect(
        composeDisableAnimations(system: true, inApp: true),
        isTrue,
      );
    });

    test('I+：accessibleNavigation 同一叠加律（系统读屏 ∨ app 内读屏优化）',
        () {
      expect(composeAccessibleNavigation(system: false, inApp: false), isFalse);
      expect(composeAccessibleNavigation(system: true, inApp: false), isTrue);
      expect(composeAccessibleNavigation(system: false, inApp: true), isTrue);
      expect(composeAccessibleNavigation(system: true, inApp: true), isTrue);
    });

    test('I+：字阶组合 = 系统夹窗 [0.85, 1.35] × app 内 fontScale', () {
      // 系统默认 × app 默认 = 1.0（不缩不小）。
      expect(
        composeAppTextScaler(
          systemScaler: TextScaler.noScaling,
          fontScale: 1.0,
        ).scale(16),
        16.0,
      );
      // 系统大字号 1.3 × app 1.2 = 1.56（乘数叠加，不是替换）。
      expect(
        composeAppTextScaler(
          systemScaler: const TextScaler.linear(1.3),
          fontScale: 1.2,
        ).scale(16),
        closeTo(16 * 1.3 * 1.2, 0.01),
      );
      // 夹窗下限：系统 0.5 被托到 0.85。
      expect(
        composeAppTextScaler(
          systemScaler: const TextScaler.linear(0.5),
          fontScale: 1.0,
        ).scale(16),
        closeTo(16 * 0.85, 0.01),
      );
      // 已注册上限：系统 200% 夹到 1.35（A-SPEC6 既定布局安全窗）。
      expect(
        composeAppTextScaler(
          systemScaler: const TextScaler.linear(2.0),
          fontScale: 1.0,
        ).scale(16),
        closeTo(16 * 1.35, 0.01),
      );
      // 上限叠加 app 内最大 1.4 → 有效 1.89（200% 全穿透需调夹窗，归规范
      // owner；limitations 已登记）。
      expect(
        composeAppTextScaler(
          systemScaler: const TextScaler.linear(2.0),
          fontScale: 1.4,
        ).scale(16),
        closeTo(16 * 1.35 * 1.4, 0.01),
      );
    });

    test('I-：AND 组合与替换组合会被同一探针判负（叠加律非恒真）', () {
      // 错误实现一（AND）：系统关 × app 开 → 误判为关（函数包装防编译期
      // 常量折叠，探针在运行时对表）。
      bool andComposition(bool system, bool inApp) => system && inApp;
      expect(
        composeDisableAnimations(system: false, inApp: true),
        isNot(andComposition(false, true)),
        reason: 'AND 组合与叠加律必须可区分（否则 I+ 无判别力）',
      );
      // 错误实现二（替换）：系统 200% 直接替换为 app 默认 1.0 → 丢大字号。
      final replacementScale =
          const TextScaler.linear(2.0).scale(16) * 1.0;
      final lawScale = composeAppTextScaler(
        systemScaler: const TextScaler.linear(2.0),
        fontScale: 1.0,
      ).scale(16);
      expect(
        lawScale,
        isNot(replacementScale),
        reason: '替换组合与夹窗组合必须可区分（否则字阶 I+ 无判别力）',
      );
    });
  });
}
