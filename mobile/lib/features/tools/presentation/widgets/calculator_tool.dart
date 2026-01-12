import 'package:flutter/material.dart';
import 'package:math_expressions/math_expressions.dart';
import 'package:sparkle/core/design/design_system.dart';

class CalculatorTool extends StatefulWidget {
  const CalculatorTool({super.key});

  @override
  State<CalculatorTool> createState() => _CalculatorToolState();
}

class _CalculatorToolState extends State<CalculatorTool> {
  String _expression = '';
  String _result = '';

  void _onPressed(String text) {
    setState(() {
      if (text == 'C') {
        _expression = '';
        _result = '';
      } else if (text == '=') {
        try {
          final p = GrammarParser();
          final exp = p.parse(_expression.replaceAll('x', '*'));
          final cm = ContextModel();
          final evaluator = RealEvaluator(cm);
          _result = '${evaluator.evaluate(exp)}';
          // Remove .0 if integer
          if (_result.endsWith('.0')) {
            _result = _result.substring(0, _result.length - 2);
          }
        } catch (e) {
          _result = 'Error';
        }
      } else if (text == 'DEL') {
        if (_expression.isNotEmpty) {
          _expression = _expression.substring(0, _expression.length - 1);
        }
      } else {
        _expression += text;
      }
    });
  }

  Widget _buildButton(String text, {Color? color, Color? textColor}) =>
      Expanded(
        child: InkWell(
          onTap: () => _onPressed(text),
          child: Container(
            margin: const EdgeInsets.all(DS.xs),
            decoration: BoxDecoration(
              color: color ?? DS.neutral100,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Center(
              child: Text(
                text,
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: textColor ?? DS.neutral900,
                ),
              ),
            ),
          ),
        ),
      );

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.lg),
        height: 500,
        decoration: BoxDecoration(
          color: DS.brandPrimaryConst,
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(24),
            topRight: Radius.circular(24),
          ),
        ),
        child: Column(
          children: [
            // Drag handle
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: DS.neutral300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: DS.lg),
            // Display
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(DS.lg),
              alignment: Alignment.bottomRight,
              decoration: BoxDecoration(
                color: DS.neutral50,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    _expression,
                    style: TextStyle(fontSize: 24, color: DS.neutral500),
                  ),
                  const SizedBox(height: DS.sm),
                  Text(
                    _result.isEmpty ? '0' : _result,
                    style: const TextStyle(
                        fontSize: 32, fontWeight: FontWeight.bold,),
                  ),
                ],
              ),
            ),
            const SizedBox(height: DS.lg),
            // Buttons
            Expanded(
              child: Column(
                children: [
                  Expanded(
                    child: Row(
                      children: [
                        _buildButton('C',
                            color: DS.error.withValues(alpha: 0.1),
                            textColor: DS.error,),
                        _buildButton('(', color: DS.neutral200),
                        _buildButton(')', color: DS.neutral200),
                        _buildButton('DEL', color: DS.neutral200),
                      ],
                    ),
                  ),
                  Expanded(
                    child: Row(
                      children: [
                        _buildButton('7'),
                        _buildButton('8'),
                        _buildButton('9'),
                        _buildButton('/',
                            color: DS.primaryBase.withValues(alpha: 0.1),
                            textColor: DS.primaryBase,),
                      ],
                    ),
                  ),
                  Expanded(
                    child: Row(
                      children: [
                        _buildButton('4'),
                        _buildButton('5'),
                        _buildButton('6'),
                        _buildButton('x',
                            color: DS.primaryBase.withValues(alpha: 0.1),
                            textColor: DS.primaryBase,),
                      ],
                    ),
                  ),
                  Expanded(
                    child: Row(
                      children: [
                        _buildButton('1'),
                        _buildButton('2'),
                        _buildButton('3'),
                        _buildButton('-',
                            color: DS.primaryBase.withValues(alpha: 0.1),
                            textColor: DS.primaryBase,),
                      ],
                    ),
                  ),
                  Expanded(
                    child: Row(
                      children: [
                        _buildButton('0'),
                        _buildButton('.'),
                        _buildButton('=',
                            color: DS.primaryBase, textColor: DS.brandPrimary,),
                        _buildButton('+',
                            color: DS.primaryBase.withValues(alpha: 0.1),
                            textColor: DS.primaryBase,),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}
