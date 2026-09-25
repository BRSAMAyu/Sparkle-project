import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/core/state/surface_state.dart';

/// U-06 状态矩阵单元测试——STATE_MATRIX.md 的 1:1 代码化不变式。
void main() {
  group('SurfaceStateMatrix 结构不变式', () {
    test('全集 22 相位，与 STATE_MATRIX.md 逐行对齐', () {
      expect(SurfaceStateMatrix.allPhases.length, 22);
      expect(
        SurfaceStateMatrix.allPhases.toSet().length,
        22,
        reason: '枚举不得有重复语义项',
      );
    });

    test('失败族 ≥12 类（卡面「自动注入至少 12 类失败状态」下限）', () {
      expect(
        SurfaceStateMatrix.failurePhases.length,
        greaterThanOrEqualTo(12),
      );
      for (final phase in SurfaceStateMatrix.failurePhases) {
        expect(SurfaceStateMatrix.allPhases.contains(phase), isTrue);
      }
    });

    test('失败族每相都有可操作（非 wait）下一步——死胡同禁令', () {
      for (final phase in SurfaceStateMatrix.failurePhases) {
        expect(
          SurfaceStateMatrix.hasActionableNextStep(phase),
          isTrue,
          reason: '$phase 缺可操作下一步',
        );
      }
    });

    test('等待族含 loading/longRunning/reconnecting/executing', () {
      expect(
        SurfaceStateMatrix.waitPhases.toSet(),
        containsAll(<SurfacePhase>[
          SurfacePhase.loading,
          SurfacePhase.longRunning,
          SurfacePhase.reconnecting,
          SurfacePhase.executing,
        ]),
      );
    });
  });

  group('既有词典类别 → 矩阵相位绑定表', () {
    test('全类别可映射（switch 穷尽，编译器背书）且语义正确', () {
      expect(
        surfacePhaseFromUiErrorCategory(UiErrorCategory.network),
        SurfacePhase.errorRecoverable,
      );
      expect(
        surfacePhaseFromUiErrorCategory(UiErrorCategory.serviceDegraded),
        SurfacePhase.modelUnavailable,
      );
      expect(
        surfacePhaseFromUiErrorCategory(UiErrorCategory.auth),
        SurfacePhase.authExpired,
      );
      expect(
        surfacePhaseFromUiErrorCategory(UiErrorCategory.notFound),
        SurfacePhase.revoked,
      );
      expect(
        surfacePhaseFromUiErrorCategory(UiErrorCategory.rateLimit),
        SurfacePhase.errorRecoverable,
      );
    });

    test('N35：offlineQueued 不是故障——落 executing，绝不落错误/未知通道', () {
      final phase =
          surfacePhaseFromUiErrorCategory(UiErrorCategory.offlineQueued);
      expect(phase, SurfacePhase.executing);
      expect(SurfaceStateMatrix.isFailure(phase), isFalse);
    });

    test('unknown 落 unknownOutcome（不造确定性）', () {
      expect(
        surfacePhaseFromUiErrorCategory(UiErrorCategory.unknown),
        SurfacePhase.unknownOutcome,
      );
    });

    test('任意异常 → 相位：判定走既有共享判定表（本层零新增判定）', () {
      expect(
        surfacePhaseFromError(Exception('SocketException: connection closed')),
        SurfacePhase.errorRecoverable,
      );
      expect(
        surfacePhaseFromError(Exception('401 Unauthorized')),
        SurfacePhase.authExpired,
      );
      expect(
        surfacePhaseFromError(TimeoutException('', const Duration(seconds: 1))),
        SurfacePhase.errorRecoverable,
      );
      expect(surfacePhaseFromError(null), SurfacePhase.unknownOutcome);
    });

    test('TypedUiError 自报类别优先（词典既有形制不回退）', () {
      final err = _TypedAuthError();
      expect(surfacePhaseFromError(err), SurfacePhase.authExpired);
    });
  });

  group('AsyncValue 接缝适配', () {
    test('loading → loading 相位', () {
      final state = surfaceStateFromAsync<int>(const AsyncLoading<int>());
      expect(state.phase, SurfacePhase.loading);
    });

    test('error → 词典判定相位', () {
      final state = surfaceStateFromAsync<int>(
        AsyncError(Exception('401'), StackTrace.current),
      );
      expect(state.phase, SurfacePhase.authExpired);
    });

    test('data → success（业务空态由调用方声明）', () {
      final state = surfaceStateFromAsync<int>(const AsyncData(1));
      expect(state.phase, SurfacePhase.success);
    });
  });

  group('SurfaceState 值语义', () {
    test('等值与 copyWith', () {
      const a = SurfaceState(SurfacePhase.offline, message: 'x');
      const b = SurfaceState(SurfacePhase.offline, message: 'x');
      expect(a, b);
      expect(a.hashCode, b.hashCode);
      final c = a.copyWith(detail: 'd');
      expect(c.phase, SurfacePhase.offline);
      expect(c.detail, 'd');
      expect(c.message, 'x');
    });
  });
}

class _TypedAuthError implements TypedUiError {
  @override
  UiErrorCategory get uiErrorCategory => UiErrorCategory.auth;
}
