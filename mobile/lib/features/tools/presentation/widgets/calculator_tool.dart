import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:math_expressions/math_expressions.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/tools/data/repositories/tool_history_repository.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class CalculatorTool extends ConsumerStatefulWidget {
  const CalculatorTool({
    super.key,
    this.surface = ToolSurface.page,
  });

  final ToolSurface surface;

  @override
  ConsumerState<CalculatorTool> createState() => _CalculatorToolState();
}

class _CalculatorToolState extends ConsumerState<CalculatorTool> {
  static const List<String> _keyRows = [
    'C DEL ( )',
    '7 8 9 /',
    '4 5 6 x',
    '1 2 3 -',
    '0 . ANS +',
  ];

  String _expression = '';
  String _result = '';
  final List<String> _history = <String>[];

  void _onPressed(String text) {
    setState(() {
      switch (text) {
        case 'C':
          _expression = '';
          _result = '';
          return;
        case 'DEL':
          if (_expression.isNotEmpty) {
            _expression = _expression.substring(0, _expression.length - 1);
          }
          return;
        case 'ANS':
          if (_result.isNotEmpty && _result != 'Error') {
            _expression += _result;
          }
          return;
        default:
          _expression += text;
      }
    });
  }

  void _evaluate() {
    if (_expression.trim().isEmpty) {
      return;
    }

    String? complexity;
    var evaluated = false;
    setState(() {
      try {
        final parser = GrammarParser();
        final sanitized = _expression
            .replaceAll('x', '*')
            .replaceAll('÷', '/')
            .replaceAll('ANS', _result.isEmpty ? '0' : _result);
        final exp = parser.parse(sanitized);
        final evaluator = RealEvaluator(ContextModel());
        final nextResult = '${evaluator.evaluate(exp)}';
        _result = nextResult.endsWith('.0')
            ? nextResult.substring(0, nextResult.length - 2)
            : nextResult;
        _history.insert(0, '$_expression = $_result');
        if (_history.length > 6) {
          _history.removeLast();
        }
        complexity = _complexityFor(_expression);
        evaluated = true;
      } catch (_) {
        _result = 'Error';
      }
    });

    if (evaluated && complexity != null) {
      unawaited(
        ref.read(toolHistoryRepositoryProvider).recordCalculatorEvaluated(
              complexity: complexity!,
              surface: widget.surface.name,
            ),
      );
    }
  }

  String _complexityFor(String expression) {
    final operatorCount = RegExp(r'[+\-x*/÷]').allMatches(expression).length;
    final hasGrouping = expression.contains('(') || expression.contains(')');
    if (operatorCount <= 1 && !hasGrouping) {
      return 'simple';
    }
    if (operatorCount <= 3 && expression.length <= 20) {
      return 'medium';
    }
    return 'complex';
  }

  Future<void> _copyResult() async {
    if (_result.isEmpty || _result == 'Error') {
      return;
    }
    await Clipboard.setData(ClipboardData(text: _result));
    if (!mounted) {
      return;
    }
    AppFeedback.success(context, '结果已复制');
  }

  @override
  Widget build(BuildContext context) {
    final accent = DS.brandPrimary;
    return ToolShell(
      surface: widget.surface,
      icon: Icons.calculate_outlined,
      title: context.l10n.toolsCalcTitle,
      subtitle: context.l10n.toolsCalcSubtitle,
      accentColor: accent,
      compactHeader: true,
      heroChips: [
        ToolHeroChip(
          label: _history.isEmpty ? context.l10n.toolsCalcNoHistory : '${_history.length} 条历史',
          accentColor: accent,
          icon: Icons.history_rounded,
        ),
        ToolHeroChip(
          label: _result.isEmpty ? context.l10n.toolsCalcWaiting : context.l10n.toolsCalcResultReady,
          accentColor: accent,
          icon: Icons.auto_graph_rounded,
        ),
      ],
      body: Column(
        children: [
          ToolSectionCard(
            accentColor: accent,
            title: context.l10n.toolsCalcExpression,
            subtitle: context.l10n.toolsCalcExpressionDesc,
            child: Column(
              children: [
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(DS.spacing18),
                  decoration: BoxDecoration(
                    color: DS.surfacePrimary,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: DS.borderSubtle),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        _expression.isEmpty ? '0' : _expression,
                        textAlign: TextAlign.right,
                        style:
                            Theme.of(context).textTheme.headlineSmall?.copyWith(
                                  color: _expression.isEmpty
                                      ? DS.textSecondary
                                      : DS.textPrimary,
                                  fontWeight: DS.fontWeightSemiBold,
                                ),
                      ),
                      const SizedBox(height: DS.spacing12),
                      Text(
                        _result.isEmpty ? context.l10n.toolsCalcReady : _result,
                        textAlign: TextAlign.right,
                        style:
                            Theme.of(context).textTheme.displaySmall?.copyWith(
                                  color: _result == 'Error'
                                      ? DS.error
                                      : DS.textPrimary,
                                  fontWeight: DS.fontWeightBold,
                                ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: DS.spacing16),
                Row(
                  children: [
                    Expanded(
                      child: SparkleButton(
                        label: context.l10n.toolsCalcCopyResult,
                        variant: ButtonVariant.ghost,
                        onPressed: _copyResult,
                        icon: const Icon(Icons.copy_rounded),
                      ),
                    ),
                    const SizedBox(width: DS.spacing12),
                    Expanded(
                      child: SparkleButton(
                        label: context.l10n.toolsCalcCompute,
                        onPressed: _evaluate,
                        icon: const Icon(Icons.play_arrow_rounded),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.spacing16),
          ToolSectionCard(
            accentColor: accent,
            title: context.l10n.toolsCalcKeyboard,
            subtitle: context.l10n.toolsCalcKeyboardDesc,
            child: Column(
              children: [
                LayoutBuilder(
                  builder: (context, constraints) {
                    final keyHeight = constraints.maxWidth < 340
                        ? 38.0
                        : constraints.maxWidth < 400
                            ? 42.0
                            : 48.0;
                    return Column(
                      children: [
                        for (final row in _keyRows)
                          Row(
                            children: row.split(' ').map((key) {
                              final isOperator =
                                  const ['/', 'x', '-', '+'].contains(key);
                              final isDanger = const ['C', 'DEL'].contains(key);
                              return Expanded(
                                child: Padding(
                                  padding: const EdgeInsets.all(DS.spacing4),
                                  child: _CalculatorKey(
                                    label: key,
                                    accentColor: accent,
                                    isOperator: isOperator,
                                    isDanger: isDanger,
                                    height: keyHeight,
                                    onTap: () => _onPressed(key),
                                  ),
                                ),
                              );
                            }).toList(),
                          ),
                        Row(
                          children: [
                            Expanded(
                              child: Padding(
                                padding: const EdgeInsets.all(DS.spacing4),
                                child: _CalculatorKey(
                                  label: '=',
                                  accentColor: accent,
                                  isPrimary: true,
                                  height: keyHeight,
                                  onTap: _evaluate,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    );
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.spacing16),
          ToolSectionCard(
            accentColor: accent,
            title: context.l10n.toolsCalcRecentHistory,
            subtitle: context.l10n.toolsCalcRecentHistoryDesc,
            child: _history.isEmpty
                ? ToolEmptyState(
                    icon: Icons.receipt_long_rounded,
                    title: context.l10n.toolsCalcNoHistoryLabel,
                    description: context.l10n.toolsCalcNoHistoryDesc,
                    accentColor: accent,
                  )
                : Column(
                    children: _history
                        .map(
                          (entry) => ListTile(
                            contentPadding: EdgeInsets.zero,
                            leading: Icon(
                              Icons.subdirectory_arrow_right_rounded,
                              color: accent,
                            ),
                            title: Text(
                              entry,
                              style: Theme.of(context)
                                  .textTheme
                                  .bodyMedium
                                  ?.copyWith(
                                    color: DS.textPrimary,
                                    fontWeight: DS.fontWeightMedium,
                                  ),
                            ),
                            trailing: IconButton(
                              onPressed: () => setState(() {
                                _expression = entry.split(' = ').first;
                              }),
                              icon: const Icon(Icons.undo_rounded),
                            ),
                          ),
                        )
                        .toList(),
                  ),
          ),
        ],
      ),
    );
  }
}

class _CalculatorKey extends StatelessWidget {
  const _CalculatorKey({
    required this.label,
    required this.accentColor,
    required this.onTap,
    required this.height,
    this.isOperator = false,
    this.isPrimary = false,
    this.isDanger = false,
  });

  final String label;
  final Color accentColor;
  final VoidCallback onTap;
  final double height;
  final bool isOperator;
  final bool isPrimary;
  final bool isDanger;

  @override
  Widget build(BuildContext context) {
    final background = isPrimary
        ? accentColor
        : isDanger
            ? DS.error.withValues(alpha: 0.10)
            : isOperator
                ? accentColor.withValues(alpha: 0.12)
                : DS.surfacePrimary;
    final foreground = isPrimary
        ? DS.textOnPrimary
        : isDanger
            ? DS.error
            : isOperator
                ? accentColor
                : DS.textPrimary;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: Ink(
        height: height,
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: isPrimary
                ? accentColor.withValues(alpha: 0.72)
                : DS.borderSubtle,
          ),
        ),
        child: Center(
          child: Text(
            label,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: foreground,
                  fontWeight: DS.fontWeightBold,
                ),
          ),
        ),
      ),
    );
  }
}
