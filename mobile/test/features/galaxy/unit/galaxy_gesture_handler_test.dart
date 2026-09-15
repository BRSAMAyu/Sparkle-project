
import 'package:flutter/gestures.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_spatial_index.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_gesture_handler.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('GalaxyGestureHandler', () {
    testWidgets('dispatches tap only after the double tap window closes', (
      tester,
    ) async {
      final commands = <GalaxyGestureCommand>[];
      final handler = _handler(commands);

      handler.handlePointerDown(
        const PointerDownEvent(
          pointer: 1,
          position: Offset(20, 20),
        ),
      );
      handler.handlePointerUp(
        const PointerUpEvent(
          pointer: 1,
          timeStamp: Duration(milliseconds: 80),
          position: Offset(20, 20),
        ),
      );

      expect(commands, isEmpty);
      await tester.pump(const Duration(milliseconds: 320));
      expect(commands.single, isA<TapCommand>());
      handler.dispose();
    });

    testWidgets('dispatches double tap without leaking the first single tap', (
      tester,
    ) async {
      final commands = <GalaxyGestureCommand>[];
      final handler = _handler(commands);

      handler.handlePointerDown(
        const PointerDownEvent(
          pointer: 1,
          position: Offset(30, 30),
        ),
      );
      handler.handlePointerUp(
        const PointerUpEvent(
          pointer: 1,
          timeStamp: Duration(milliseconds: 70),
          position: Offset(30, 30),
        ),
      );
      await tester.pump(const Duration(milliseconds: 160));
      handler.handlePointerDown(
        const PointerDownEvent(
          pointer: 2,
          timeStamp: Duration(milliseconds: 180),
          position: Offset(34, 32),
        ),
      );
      handler.handlePointerUp(
        const PointerUpEvent(
          pointer: 2,
          timeStamp: Duration(milliseconds: 240),
          position: Offset(34, 32),
        ),
      );

      expect(commands.single, isA<DoubleTapCommand>());
      await tester.pump(const Duration(milliseconds: 320));
      expect(commands.length, 1);
      handler.dispose();
    });

    testWidgets('promotes long press into drag after movement threshold', (
      tester,
    ) async {
      final commands = <GalaxyGestureCommand>[];
      const hit = GalaxyNodeHit(
        nodeId: 'node-1',
        worldPosition: Offset.zero,
        distance: 0,
      );
      final handler = _handler(commands, hit: hit);

      handler.handlePointerDown(
        const PointerDownEvent(
          pointer: 1,
          position: Offset(50, 50),
        ),
      );
      await tester.pump(const Duration(milliseconds: 520));
      handler.handlePointerMove(
        const PointerMoveEvent(
          pointer: 1,
          timeStamp: Duration(milliseconds: 620),
          position: Offset(68, 50),
        ),
      );

      expect(commands.first, isA<LongPressCommand>());
      expect(commands.last, isA<DragNodeCommand>());
      handler.dispose();
    });
  });
}

GalaxyGestureHandler _handler(
  List<GalaxyGestureCommand> commands, {
  GalaxyNodeHit? hit,
}) =>
    GalaxyGestureHandler(
      screenToWorld: (point) => point,
      hitTestNode: (_) => hit,
      onCommand: commands.add,
      longPressDragWindow: const Duration(seconds: 1),
    );
