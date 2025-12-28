import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:go_router/go_router.dart';

/// 计划创建屏幕 - 占位页面
class PlanCreateScreen extends StatelessWidget {
  final String? planType;

  const PlanCreateScreen({super.key, this.planType});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(planType == 'growth' ? '创建成长计划' : '创建冲刺计划'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.construction, size: 80, color: Colors.orange),
            const SizedBox(height: DS.lg),
            Text(
              '计划创建功能开发中',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: DS.sm),
            const Text(
              '此功能正在开发中，即将推出',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: DS.xl),
            ElevatedButton(
              onPressed: () => context.pop(),
              child: const Text('返回'),
            ),
          ],
        ),
      ),
    );
  }
}