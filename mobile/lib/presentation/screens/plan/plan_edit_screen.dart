import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';

/// 计划编辑屏幕 - 占位页面
class PlanEditScreen extends StatelessWidget {

  const PlanEditScreen({required this.planId, super.key});
  final String planId;

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(
        title: const Text('编辑计划'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.construction, size: 80, color: DS.brandPrimary),
            const SizedBox(height: DS.lg),
            Text(
              '计划编辑功能开发中',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: DS.sm),
            Text(
              '计划ID: $planId',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: DS.sm),
            const Text(
              '此功能正在开发中，即将推出',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: DS.xl),
            SparkleButton.primary(label: '返回', onPressed: () => context.pop()),
          ],
        ),
      ),
    );
}