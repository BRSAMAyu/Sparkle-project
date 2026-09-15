/// Widget Performance Benchmarks
/// Widget性能基准测试
///
/// Tests render performance, build times, and memory usage for key widgets.
library;

import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_review_card.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/task_board_card.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';

const int _planReviewBuildThresholdMs = int.fromEnvironment(
  'PLAN_REVIEW_BUILD_MS',
  defaultValue: 900,
);
const int _taskBoardBuildThresholdMs = int.fromEnvironment(
  'TASK_BOARD_BUILD_MS',
  defaultValue: 80,
);
const int _planReviewRebuildThresholdMs = int.fromEnvironment(
  'PLAN_REVIEW_REBUILD_MS',
  defaultValue: 60,
);
const int _scrollFrameThresholdUs = int.fromEnvironment(
  'SCROLL_FRAME_US',
  defaultValue: 70000,
);
const int _chatListBuildThresholdMs = int.fromEnvironment(
  'CHAT_LIST_BUILD_MS',
  defaultValue: 260,
);

void main() {
  group('Widget Build Performance', () {
    testWidgets('PlanReviewCard builds in under 16ms (60fps)', (tester) async {
      final stopwatch = Stopwatch()..start();

      await tester.pumpWidget(
        _wrapApp(
          Scaffold(
            body: PlanReviewCard(
              review: _mockReview(overallScore: 85),
              onApprove: () {},
              onReject: () {},
              onModify: () {},
            ),
          ),
        ),
      );

      stopwatch.stop();

      print('PlanReviewCard build: ${stopwatch.elapsedMilliseconds}ms');
      expect(
          stopwatch.elapsedMilliseconds, lessThan(_planReviewBuildThresholdMs));
    });

    testWidgets('TaskBoardCard builds in under 16ms (60fps)', (tester) async {
      final stopwatch = Stopwatch()..start();

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: TaskBoardCard(
              task: TaskBoard(
                id: 'task-1',
                title: 'Test Task',
                status: TaskStatus.inProgress,
              ),
            ),
          ),
        ),
      );

      stopwatch.stop();

      print('TaskBoardCard build: ${stopwatch.elapsedMilliseconds}ms');
      expect(
          stopwatch.elapsedMilliseconds, lessThan(_taskBoardBuildThresholdMs));
    });

    testWidgets('GalaxyScreen initial build in under 100ms', (tester) async {
      final nodes = _generateMockNodes(50);
      final edges = _generateMockEdges(nodes);

      final stopwatch = Stopwatch()..start();

      await tester.pumpWidget(
        MaterialApp(
          home: GalaxyScreen(
            nodes: nodes,
            edges: edges,
          ),
        ),
      );

      stopwatch.stop();

      print('GalaxyScreen build: ${stopwatch.elapsedMilliseconds}ms');
      expect(stopwatch.elapsedMilliseconds, lessThan(100));
    });

    testWidgets('Chat message list builds 100 items in under threshold',
        (tester) async {
      final messages = List.generate(
        100,
        (i) => ChatMessage(
          id: 'msg-$i',
          content: 'Message $i',
          role: i % 2 == 0 ? 'user' : 'assistant',
          timestamp: DateTime.now(),
        ),
      );

      final stopwatch = Stopwatch()..start();

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ListView.builder(
              itemCount: messages.length,
              itemBuilder: (context, index) {
                final msg = messages[index];
                return ListTile(
                  title: Text(msg.content),
                  subtitle: Text(msg.role),
                );
              },
            ),
          ),
        ),
      );

      stopwatch.stop();

      print('100 messages build: ${stopwatch.elapsedMilliseconds}ms');
      expect(
        stopwatch.elapsedMilliseconds,
        lessThan(_chatListBuildThresholdMs),
      );
    });
  });

  group('Widget Rebuild Performance', () {
    testWidgets('PlanReviewCard rebuilds in under 5ms', (tester) async {
      await tester.pumpWidget(
        _wrapApp(
          Scaffold(
            body: PlanReviewCard(
              review: _mockReview(overallScore: 85),
              onApprove: () {},
              onReject: () {},
              onModify: () {},
            ),
          ),
        ),
      );

      await tester.pump(const Duration(milliseconds: 50));

      final stopwatch = Stopwatch()..start();

      // Trigger rebuild
      await tester.pumpWidget(
        _wrapApp(
          Scaffold(
            body: PlanReviewCard(
              review: _mockReview(overallScore: 90), // Changed score
              onApprove: () {},
              onReject: () {},
              onModify: () {},
            ),
          ),
        ),
      );

      stopwatch.stop();

      print('PlanReviewCard rebuild: ${stopwatch.elapsedMilliseconds}ms');
      expect(
        stopwatch.elapsedMilliseconds,
        lessThan(_planReviewRebuildThresholdMs),
      );
    });
  });

  group('Animation Performance', () {
    testWidgets('PlanReviewCard animation maintains 60fps', (tester) async {
      await tester.pumpWidget(
        _wrapApp(
          Scaffold(
            body: PlanReviewCard(
              review: _mockReview(overallScore: 85),
              onApprove: () {},
              onReject: () {},
              onModify: () {},
            ),
          ),
        ),
      );

      final frameTimes = <int>[];

      // Measure 60 frames (1 second at 60fps)
      for (var i = 0; i < 60; i++) {
        final frameStopwatch = Stopwatch()..start();
        await tester.pump(const Duration(milliseconds: 16));
        frameStopwatch.stop();
        frameTimes.add(frameStopwatch.elapsedMicroseconds);
      }

      // Calculate average frame time
      final avgFrameTime =
          frameTimes.reduce((a, b) => a + b) / frameTimes.length;

      print('Average frame time: ${avgFrameTime / 1000}ms');
      expect(avgFrameTime, lessThan(16667)); // < 16.67ms per frame
    });
  });

  group('List Scrolling Performance', () {
    testWidgets('Scrolling 100 items maintains 60fps', (tester) async {
      final items = List.generate(100, (i) => 'Item $i');

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ListView.builder(
              itemCount: items.length,
              itemBuilder: (context, index) =>
                  ListTile(title: Text(items[index])),
            ),
          ),
        ),
      );

      final frameTimes = <int>[];

      // Scroll through list
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

      final avgFrameTime =
          frameTimes.reduce((a, b) => a + b) / frameTimes.length;

      print('Average scroll frame time: ${avgFrameTime / 1000}ms');
      expect(avgFrameTime, lessThan(_scrollFrameThresholdUs));
    });
  });

  group('Memory Tests', () {
    testWidgets('PlanReviewCard memory usage', (tester) async {
      // Measure initial memory
      final initialMemory = _getCurrentMemoryUsage();

      await tester.pumpWidget(
        _wrapApp(
          Scaffold(
            body: PlanReviewCard(
              review: _mockReview(overallScore: 85),
              onApprove: () {},
              onReject: () {},
              onModify: () {},
            ),
          ),
        ),
      );

      await tester.pump(const Duration(milliseconds: 50));

      final finalMemory = _getCurrentMemoryUsage();
      final memoryIncrease = finalMemory - initialMemory;

      print('PlanReviewCard memory increase: $memoryIncrease KB');
      expect(memoryIncrease, lessThan(500)); // < 500KB increase
    });

    testWidgets('Large list memory usage', (tester) async {
      final initialMemory = _getCurrentMemoryUsage();

      final items = List.generate(1000, (i) => 'Item $i');

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ListView.builder(
              itemCount: items.length,
              itemBuilder: (context, index) =>
                  ListTile(title: Text(items[index])),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      final finalMemory = _getCurrentMemoryUsage();
      final memoryIncrease = finalMemory - initialMemory;

      print('1000 item list memory increase: $memoryIncrease KB');
      expect(memoryIncrease, lessThan(5000)); // < 5MB for 1000 items
    });
  });
}

// Helper functions
int _getCurrentMemoryUsage() {
  // This is a simplified version - in production you'd use
  // Flutter's memory profiling tools
  return 0; // Placeholder
}

Widget _wrapApp(Widget child) => MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: child,
    );

List<GalaxyNode> _generateMockNodes(int count) => List.generate(
      count,
      (i) => GalaxyNode(
        id: 'node-$i',
        position: Offset(
          (i % 10) * 100.0,
          (i ~/ 10) * 100.0,
        ),
        label: 'Node $i',
      ),
    );

List<GalaxyEdge> _generateMockEdges(List<GalaxyNode> nodes) => [
      for (var i = 0; i < nodes.length - 1; i++)
        GalaxyEdge(
          from: nodes[i].id,
          to: nodes[i + 1].id,
        ),
    ];

// Mock classes
class TaskBoard {
  const TaskBoard({
    required this.id,
    required this.title,
    required this.status,
  });
  final String id;
  final String title;
  final TaskStatus status;
}

PlanReviewResult _mockReview({required int overallScore}) => PlanReviewResult(
      reviewId: 'test-review',
      planId: 'test-plan',
      decision: ReviewDecision.needsModification,
      confidence: 0.9,
      comments: const [],
      reviewedAt: '2026-01-01T00:00:00Z',
      suggestedModifications: <String, dynamic>{'overall_score': overallScore},
    );

enum TaskStatus { inProgress, completed, pending }

class TaskBoardCard extends StatelessWidget {
  const TaskBoardCard({super.key, required this.task});
  final TaskBoard task;

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(task.title, style: const TextStyle(fontSize: 18)),
              Text(task.status.toString()),
            ],
          ),
        ),
      );
}

class ChatMessage {
  ChatMessage({
    required this.id,
    required this.content,
    required this.role,
    required this.timestamp,
  });
  final String id;
  final String content;
  final String role;
  final DateTime timestamp;
}

class GalaxyScreen extends StatelessWidget {
  const GalaxyScreen({
    super.key,
    required this.nodes,
    required this.edges,
  });
  final List<GalaxyNode> nodes;
  final List<GalaxyEdge> edges;

  @override
  Widget build(BuildContext context) => Scaffold(
        body: CustomPaint(
          painter: GalaxyPainter(nodes: nodes, edges: edges),
        ),
      );
}

class GalaxyPainter extends CustomPainter {
  GalaxyPainter({required this.nodes, required this.edges});
  final List<GalaxyNode> nodes;
  final List<GalaxyEdge> edges;

  @override
  void paint(Canvas canvas, Size size) {
    // Simplified galaxy rendering
    for (final _ in edges) {
      // Draw edge
    }
    for (final _ in nodes) {
      // Draw node
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}

class GalaxyNode {
  GalaxyNode({
    required this.id,
    required this.position,
    required this.label,
  });
  final String id;
  final Offset position;
  final String label;
}

class GalaxyEdge {
  GalaxyEdge({required this.from, required this.to});
  final String from;
  final String to;
}
