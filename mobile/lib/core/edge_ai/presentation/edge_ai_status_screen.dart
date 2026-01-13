import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/edge_ai_provider.dart';
import '../models/edge_state_schema.dart';

class EdgeAIStatusScreen extends ConsumerWidget {
  const EdgeAIStatusScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final aiState = ref.watch(edgeAIStateProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Qwen3 端侧认知看板'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(edgeAIStateProvider.notifier).refresh(),
          ),
        ],
      ),
      body: aiState.when(
        data: (state) => state == null 
            ? _buildInitialState(ref) 
            : _buildDashboard(context, state),
        loading: () => const Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(),
              SizedBox(height: 16),
              Text('Qwen3 正在思考分析中...'),
            ],
          ),
        ),
        error: (e, _) => Center(child: Text('出错了: $e')),
      ),
    );
  }

  Widget _buildInitialState(WidgetRef ref) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.psychology, size: 80, color: Colors.blueGrey),
          const SizedBox(height: 20),
          const Text('尚未运行端侧分析'),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: () => ref.read(edgeAIStateProvider.notifier).refresh(),
            child: const Text('立即运行分析'),
          ),
        ],
      ),
    );
  }

  Widget _buildDashboard(BuildContext context, EdgeState state) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _buildSectionHeader('用户核心状态'),
        _buildMetricTile('注意力', state.attentionScore, Colors.blue),
        _buildMetricTile('疲劳度', state.fatigueScore, Colors.orange),
        _buildMetricTile('压力值', state.stressScore, Colors.red),
        
        const Divider(height: 40),
        
        _buildSectionHeader('决策建议'),
        ListTile(
          leading: Icon(
            state.shouldInterrupt ? Icons.notifications_active : Icons.notifications_off,
            color: state.shouldInterrupt ? Colors.red : Colors.green,
          ),
          title: const Text('是否建议干预'),
          trailing: Text(state.shouldInterrupt ? '建议中断' : '不打扰'),
        ),
        ListTile(
          leading: const Icon(Icons.record_voice_over),
          title: const Text('推荐语气'),
          trailing: Chip(label: Text(state.nudgeTone)),
        ),
        ListTile(
          leading: const Icon(Icons.timer),
          title: const Text('最佳时间窗口'),
          trailing: Text('${state.bestWindow.inMinutes} 分钟后'),
        ),

        const SizedBox(height: 40),
        Text(
          '最后更新: ${DateTime.fromMillisecondsSinceEpoch(state.timestamp * 1000).toLocal()}',
          style: Theme.of(context).textTheme.bodySmall,
          textAlign: TextAlign.center,
        ),
      ],
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Text(
        title,
        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
      ),
    );
  }

  Widget _buildMetricTile(String label, double value, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(label),
              Text('${(value * 100).toInt()}%'),
            ],
          ),
          const SizedBox(height: 4),
          LinearProgressIndicator(
            value: value,
            color: color,
            backgroundColor: color.withOpacity(0.1),
            minHeight: 8,
          ),
        ],
      ),
    );
  }
}
