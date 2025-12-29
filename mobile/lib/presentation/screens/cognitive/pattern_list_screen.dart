import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/behavior_pattern_model.dart';
import 'package:sparkle/presentation/providers/cognitive_provider.dart';

/// PatternListScreen - Cognitive Prism Details v2.3
///
/// Displays all behavior patterns with deep space theme
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

    return Scaffold(
      body: DecoratedBox(
        decoration: BoxDecoration(
          gradient: DS.deepSpaceGradient,
        ),
        child: SafeArea(
          child: Column(
            children: [
              // Custom app bar
              _buildAppBar(context),

              // Content
              Expanded(
                child: RefreshIndicator(
                  onRefresh: _loadPatterns,
                  child: cognitiveState.isLoading && cognitiveState.patterns.isEmpty
                      ? Center(
                          child: CircularProgressIndicator(
                            valueColor: AlwaysStoppedAnimation<Color>(DS.brandPrimary70),
                          ),
                        )
                      : cognitiveState.patterns.isEmpty
                          ? _buildEmptyState()
                          : _buildPatternList(cognitiveState.patterns),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAppBar(BuildContext context) => Padding(
      padding: const EdgeInsets.fromLTRB(8, 8, 16, 16),
      child: Row(
        children: [
          IconButton(
            onPressed: () => Navigator.of(context).pop(),
            icon: Icon(Icons.arrow_back_ios_rounded, color: DS.brandPrimary),
          ),
          Expanded(
            child: Text(
              '认知棱镜',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: DS.brandPrimary,
              ),
            ),
          ),
          Container(
            padding: const EdgeInsets.all(DS.sm),
            decoration: BoxDecoration(
              color: DS.prismPurple.withAlpha(40),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              Icons.diamond_outlined,
              color: DS.brandPrimaryConst,
              size: 20,
            ),
          ),
        ],
      ),
    );

  Widget _buildEmptyState() => SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(DS.xxl),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const SizedBox(height: 80),
          Container(
            padding: const EdgeInsets.all(DS.xl),
            decoration: BoxDecoration(
              color: DS.prismPurple.withAlpha(30),
              shape: BoxShape.circle,
            ),
            child: Icon(
              Icons.psychology_alt_rounded,
              size: 64,
              color: DS.prismPurple.withAlpha(150),
            ),
          ),
          const SizedBox(height: DS.xl),
          Text(
            '暂无行为定式',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: DS.brandPrimary,
            ),
          ),
          const SizedBox(height: DS.sm),
          Text(
            '继续记录你的想法和情绪\nAI 会为你发现行为模式',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 14,
              color: DS.brandPrimary.withAlpha(150),
              height: 1.5,
            ),
          ),
        ],
      ),
    );

  Widget _buildPatternList(List<BehaviorPatternModel> patterns) => ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      itemCount: patterns.length,
      itemBuilder: (context, index) => Padding(
          padding: const EdgeInsets.only(bottom: 16),
          child: _PatternCard(pattern: patterns[index]),
        ),
    );
}

/// Pattern Card with glassmorphism style
class _PatternCard extends StatelessWidget {

  const _PatternCard({required this.pattern});
  final BehaviorPatternModel pattern;

  @override
  Widget build(BuildContext context) => ClipRRect(
      borderRadius: DS.borderRadius20,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          decoration: BoxDecoration(
            color: DS.glassBackground,
            borderRadius: DS.borderRadius20,
            border: Border.all(color: DS.glassBorder),
          ),
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: _getTypeColor(pattern.patternType).withAlpha(40),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(
                      _getTypeIcon(pattern.patternType),
                      color: _getTypeColor(pattern.patternType),
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: DS.md),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          pattern.patternName,
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: DS.brandPrimaryConst,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          _getTypeLabel(pattern.patternType),
                          style: TextStyle(
                            fontSize: 12,
                            color: _getTypeColor(pattern.patternType),
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (pattern.isArchived)
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: DS.success.withAlpha(40),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        '已克服',
                        style: TextStyle(
                          fontSize: 10,
                          color: DS.success,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                ],
              ),

              // Description
              if (pattern.description != null) ...[
                const SizedBox(height: DS.lg),
                Text(
                  pattern.description!,
                  style: TextStyle(
                    fontSize: 14,
                    color: DS.brandPrimary.withAlpha(200),
                    height: 1.5,
                  ),
                ),
              ],

              // Solution
              if (pattern.solutionText != null) ...[
                const SizedBox(height: DS.lg),
                Container(
                  padding: const EdgeInsets.all(DS.md),
                  decoration: BoxDecoration(
                    color: DS.success.withAlpha(20),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: DS.success.withAlpha(50),
                    ),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(
                        Icons.lightbulb_outline_rounded,
                        color: DS.success,
                        size: 18,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          pattern.solutionText!,
                          style: TextStyle(
                            fontSize: 13,
                            color: DS.successLight,
                            height: 1.4,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],

              // Date
              const SizedBox(height: DS.md),
              Text(
                '发现于 ${_formatDate(pattern.createdAt)}',
                style: TextStyle(
                  fontSize: 11,
                  color: DS.brandPrimary.withAlpha(100),
                ),
              ),
            ],
          ),
        ),
      ),
    );

  Color _getTypeColor(String type) {
    switch (type) {
      case 'cognitive':
        return DS.prismBlue;
      case 'emotional':
        return DS.prismPurple;
      case 'execution':
        return DS.prismGreen;
      default:
        return DS.neutral400;
    }
  }

  IconData _getTypeIcon(String type) {
    switch (type) {
      case 'cognitive':
        return Icons.psychology_rounded;
      case 'emotional':
        return Icons.mood_rounded;
      case 'execution':
        return Icons.bolt_rounded;
      default:
        return Icons.diamond_outlined;
    }
  }

  String _getTypeLabel(String type) {
    switch (type) {
      case 'cognitive':
        return '认知偏差';
      case 'emotional':
        return '情绪模式';
      case 'execution':
        return '执行习惯';
      default:
        return '行为模式';
    }
  }

  String _formatDate(DateTime date) => '${date.month}月${date.day}日';
}
