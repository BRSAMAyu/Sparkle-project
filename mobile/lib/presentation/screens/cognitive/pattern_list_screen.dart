import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/cognitive_provider.dart';
import 'package:sparkle/presentation/widgets/cognitive/pattern_card.dart';
import 'package:sparkle/presentation/widgets/common/empty_state.dart';

class PatternListScreen extends ConsumerStatefulWidget {
  const PatternListScreen({super.key});

  @override
  ConsumerState<PatternListScreen> createState() => _PatternListScreenState();
}

class _PatternListScreenState extends ConsumerState<PatternListScreen> {
  @override
  void initState() {
    super.initState();
    _loadPatterns();
  }

  Future<void> _loadPatterns() async {
    await ref.read(cognitiveProvider.notifier).loadPatterns();
  }

  @override
  Widget build(BuildContext context) {
    final cognitiveState = ref.watch(cognitiveProvider);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('行为定式'),
        flexibleSpace: Container(
          decoration: const BoxDecoration(
            gradient: AppDesignTokens.primaryGradient,
          ),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: _loadPatterns,
        child: cognitiveState.isLoading && cognitiveState.patterns.isEmpty
            ? const Center(child: CircularProgressIndicator())
            : cognitiveState.patterns.isEmpty
                ? const SingleChildScrollView(
                    physics: AlwaysScrollableScrollPhysics(),
                    child: Padding(
                      padding: EdgeInsets.all(AppDesignTokens.spacing16),
                      child: EmptyState(
                        title: '暂无行为定式',
                        description: '继续记录碎片，AI 会为你分析',
                        icon: Icons.psychology_alt,
                      ),
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(AppDesignTokens.spacing16),
                    itemCount: cognitiveState.patterns.length,
                    itemBuilder: (context, index) {
                      final pattern = cognitiveState.patterns[index];
                      return Padding(
                        padding: const EdgeInsets.only(bottom: AppDesignTokens.spacing16),
                        child: PatternCard(pattern: pattern),
                      );
                    },
                  ),
      ),
    );
  }
}
