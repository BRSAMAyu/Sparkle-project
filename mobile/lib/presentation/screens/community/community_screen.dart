import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';

class CommunityScreen extends StatelessWidget {
  const CommunityScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('社群'),
        centerTitle: true,
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.groups_rounded, size: 64, color: Colors.grey),
            const SizedBox(height: AppDesignTokens.spacing16),
            Text(
              '社群功能开发中...',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: Colors.grey,
                  ),
            ),
            const SizedBox(height: AppDesignTokens.spacing8),
            const Text('在这里找到你的学习伙伴'),
          ],
        ),
      ),
    );
  }
}
