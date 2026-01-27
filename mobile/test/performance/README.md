# Flutter Performance & Golden Tests

Comprehensive performance and golden (screenshot) testing for the Flutter mobile app.

## Setup

### Install Dependencies

```bash
cd mobile
flutter pub get
```

### Golden Testing Setup

Golden tests require the `golden_toolkit` package (already added to `pubspec.yaml`):

```yaml
dev_dependencies:
  golden_toolkit: ^0.15.0
```

## Running Tests

### Performance Tests

```bash
# Run all performance tests
flutter test test/performance/

# Run specific performance test
flutter test test/performance/widget_bench_test.dart

# Run with verbose output
flutter test test/performance/ -v

# Run on specific device
flutter test test/performance/ --device-id=<device-id>
```

### Golden Tests

```bash
# Run all golden tests
flutter test test/goldens/

# Update golden files (when UI changes are intentional)
flutter test test/goldens/ --update-goldens

# Run golden tests on specific device
flutter test test/goldens/ --device-id=<device-id>

# Run with golden toolkit configuration
flutter test test/goldens/ --golden-toolkit-tag=mobile
```

### Integration Tests

```bash
# Run integration tests
flutter test test/integration/

# Run driver tests
flutter drive --profile test_driver/app.dart test_driver/app_test.dart
```

## Test Categories

### 1. Performance Tests (`test/performance/`)

**Widget Build Performance**
- `widget_bench_test.dart` - Widget build and rebuild benchmarks
- Build time targets: < 16ms for 60fps
- Rebuild time targets: < 5ms

**Rendering Performance**
- Frame time measurements
- Animation smoothness tests
- Scrolling performance

**Memory Tests**
- Widget memory usage
- List memory efficiency
- Memory leak detection

**Existing Galaxy Performance Tests**
- `test/features/galaxy/performance/galaxy_performance_test.dart`
- Layout engine benchmarks
- QuadTree performance
- Viewport culling

### 2. Golden Tests (`test/goldens/`)

**Dashboard Screen**
- `dashboard_golden_test.dart`
- Light/dark themes
- Responsive layouts (mobile/tablet)
- Interactive states (omnibar focused, tasks expanded)
- Notification display

**Chat Screen**
- `chat_golden_test.dart`
- Empty state
- With messages
- Plan review card
- Typing indicator
- Code blocks
- Error messages

**Galaxy Screen**
- `galaxy_golden_test.dart` (to be created)
- Different node counts
- Light/dark themes
- Interactive states

## Performance Targets

### Widget Build Times

| Widget | Target (Build) | Target (Rebuild) | Notes |
|--------|----------------|------------------|-------|
| PlanReviewCard | < 16ms | < 5ms | 60fps maintainable |
| TaskBoardCard | < 16ms | < 5ms | 60fps maintainable |
| ChatMessage | < 10ms | < 2ms | Per message |
| GalaxyNode | < 5ms | < 1ms | Per node |

### List Performance

| List Size | Build Time | Scroll FPS | Memory |
|-----------|-----------|------------|--------|
| 100 items | < 100ms | 60 | < 1MB |
| 1000 items | < 500ms | 60 | < 5MB |
| 10000 items | < 2000ms | 60 | < 20MB |

### Animation Performance

| Animation | Target FPS | Frame Time | Notes |
|-----------|-----------|------------|-------|
| PlanReviewCard | 60 | < 16.67ms | Smooth entry |
| Chat scroll | 60 | < 16.67ms | No jank |
| Galaxy layout | 60 | < 16.67ms | Force-directed |

## Writing New Performance Tests

### Widget Benchmark Template

```dart
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('MyWidget builds in under 16ms', (tester) async {
    final stopwatch = Stopwatch()..start();

    await tester.pumpWidget(
      MaterialApp(
        home: MyWidget(),
      ),
    );

    stopwatch.stop();

    print('MyWidget build: ${stopwatch.elapsedMilliseconds}ms');
    expect(stopwatch.elapsedMilliseconds, lessThan(16));
  });
}
```

### List Performance Template

```dart
testWidgets('Scrolling list maintains 60fps', (tester) async {
  await tester.pumpWidget(
    MaterialApp(
      home: ListView.builder(
        itemCount: 1000,
        itemBuilder: (context, index) => ListTile(title: Text('Item $index')),
      ),
    ),
  );

  final frameTimes = <int>[];

  for (var i = 0; i < 50; i++) {
    final frameStopwatch = Stopwatch()..start();
    await tester.fling(
      find.byType(ListView),
      const Offset(0, -300),
      1000,
    );
    await tester.pump();
    frameStopwatch.stop();
    frameTimes.add(frameStopwatch.elapsedMicroseconds);
  }

  final avgFrameTime = frameTimes.reduce((a, b) => a + b) / frameTimes.length;
  expect(avgFrameTime, lessThan(16667)); // < 16.67ms per frame
});
```

## Writing New Golden Tests

### Basic Golden Test Template

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:golden_toolkit/golden_toolkit.dart';

void main() {
  group('MyWidget Golden Tests', () {
    testGoldens('MyWidget light theme', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.light(),
          home: MyWidget(),
        ),
      );

      await tester.pumpAndSettle();

      await expectLater(
        find.byType(MyWidget),
        matchesGoldenFile('my_widget_light.png'),
      );
    });

    testGoldens('MyWidget dark theme', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.dark(),
          home: MyWidget(),
        ),
      );

      await tester.pumpAndSettle();

      await expectLater(
        find.byType(MyWidget),
        matchesGoldenFile('my_widget_dark.png'),
      );
    });
  });
}
```

### Responsive Golden Test Template

```dart
testGoldens('MyWidget responsive layouts', (tester) async {
  // Test mobile layout
  await tester.pumpWidgetBuilder(
    MaterialApp(
      home: MediaQuery(
        data: const MediaQueryData(size: Size(375, 667)), // iPhone SE
        child: MyWidget(),
      ),
    ),
  );
  await tester.pumpAndSettle();
  await expectLater(
    find.byType(MyWidget),
    matchesGoldenFile('my_widget_mobile.png'),
  );

  // Test tablet layout
  await tester.pumpWidgetBuilder(
    MaterialApp(
      home: MediaQuery(
        data: const MediaQueryData(size: Size(768, 1024)), // iPad
        child: MyWidget(),
      ),
    ),
  );
  await tester.pumpAndSettle();
  await expectLater(
    find.byType(MyWidget),
    matchesGoldenFile('my_widget_tablet.png'),
  );
});
```

### Interactive State Golden Test

```dart
testGoldens('MyWidget with focused state', (tester) async {
  await tester.pumpWidget(
    const MaterialApp(
      home: MyWidget(),
    ),
  );

  await tester.pumpAndSettle();

  // Trigger interactive state
  await tester.tap(find.byType(TextField));
  await tester.pumpAndSettle();

  await expectLater(
    find.byType(MyWidget),
    matchesGoldenFile('my_widget_focused.png'),
  );
});
```

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Flutter Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Flutter
        uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.16.0'

      - name: Install dependencies
        run: cd mobile && flutter pub get

      - name: Run performance tests
        run: cd mobile && flutter test test/performance/

      - name: Run golden tests
        run: cd mobile && flutter test test/goldens/

      - name: Upload golden test results
        uses: actions/upload-artifact@v2
        if: failure()
        with:
          name: golden-failures
          path: mobile/test/goldens/failures/
```

## Troubleshooting

### Golden Test Failures

**Issue**: Golden test fails after valid UI change

**Solution**:
```bash
# Update golden files
flutter test test/goldens/ --update-goldens

# Commit updated golden files
git add test/goldens/*.png
git commit -m "update golden files for UI changes"
```

**Issue**: Golden tests fail on different devices

**Solution**:
- Use `device_builder` from golden_toolkit
- Test on consistent device sizes
- Create device-specific golden files

### Performance Test Failures

**Issue**: Performance degraded after refactor

**Solution**:
- Profile with Flutter DevTools
- Check for unnecessary rebuilds
- Use `const` widgets where possible
- Implement lazy loading for lists

**Issue**: Inconsistent performance results

**Solution**:
- Run tests multiple times
- Use median values
- Ensure device is in performance mode
- Close background apps

### Memory Issues

**Issue**: Memory usage increasing over time

**Solution**:
- Check for undisposed controllers
- Verify provider cleanup
- Use `flutter analyze` for leaks
- Profile with DevTools Memory view

## Best Practices

### Performance Testing

1. **Test realistic scenarios** - Use real data sizes
2. **Measure consistently** - Use Stopwatch and median values
3. **Test on devices** - Emulators don't reflect real performance
4. **Profile before optimizing** - Identify actual bottlenecks
5. **Document targets** - Include performance expectations in tests

### Golden Testing

1. **Test both themes** - Light and dark mode
2. **Test responsive layouts** - Mobile and tablet
3. **Test interactive states** - Focused, pressed, disabled
4. **Keep golden files updated** - Run `--update-goldens` when needed
5. **Organize files** - Group by widget/screen

### General

1. **Run tests before committing** - Catch issues early
2. **Keep tests fast** - Performance tests should run quickly
3. **Use descriptive names** - Make test purposes clear
4. **Document flaky tests** - Mark with @skip if unstable
5. **Monitor trends** - Track performance over time

## See Also

- [Flutter Testing Documentation](https://docs.flutter.dev/cookbook/testing)
- [Golden Toolkit Package](https://pub.dev/packages/golden_toolkit)
- [Flutter Performance Best Practices](https://docs.flutter.dev/perf/best-practices)
- [Flutter DevTools](https://docs.flutter.dev/tools/devtools/overview)
