import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

class TranslatorTool extends StatefulWidget {
  const TranslatorTool({super.key});

  @override
  State<TranslatorTool> createState() => _TranslatorToolState();
}

class _TranslatorToolState extends State<TranslatorTool> {
  final TextEditingController _inputController = TextEditingController();
  String _output = '';
  bool _isLoading = false;

  Future<void> _translate() async {
    if (_inputController.text.isEmpty) return;

    setState(() {
      _isLoading = true;
      _output = '';
    });

    // Mock delay
    await Future.delayed(const Duration(seconds: 1));

    // Mock translation logic (simple reverse or dummy text for now as we don't have API)
    setState(() {
      _isLoading = false;
      // In a real app, we'd call an API here.
      _output = '[翻译结果] ${_inputController.text} (Translated)'; 
    });
  }

  @override
  Widget build(BuildContext context) => Container(
      padding: const EdgeInsets.all(DS.xl),
      height: 500,
      decoration: BoxDecoration(
        color: DS.brandPrimaryConst,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(24),
          topRight: Radius.circular(24),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: DS.neutral300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: DS.xl),
          Row(
            children: [
              const Icon(Icons.translate, color: Colors.purple),
              const SizedBox(width: DS.sm),
              Text(
                '快速翻译',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: DS.xl),
          TextField(
            controller: _inputController,
            maxLines: 4,
            decoration: InputDecoration(
              hintText: '输入要翻译的文本...',
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              filled: true,
              fillColor: DS.neutral50,
            ),
          ),
          const SizedBox(height: DS.lg),
          Center(
            child: IconButton(
              onPressed: _translate,
              icon: const Icon(Icons.arrow_downward_rounded, color: Colors.purple),
              style: IconButton.styleFrom(backgroundColor: Colors.purple.withValues(alpha: 0.1)),
            ),
          ),
          const SizedBox(height: DS.lg),
          Container(
            padding: const EdgeInsets.all(DS.lg),
            height: 120,
            decoration: BoxDecoration(
              color: Colors.purple.withValues(alpha: 0.05),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.purple.withValues(alpha: 0.1)),
            ),
            child: _isLoading 
                ? const Center(child: CircularProgressIndicator()) 
                : SingleChildScrollView(
                    child: Text(
                      _output.isEmpty ? '翻译结果将显示在这里' : _output,
                      style: TextStyle(
                        color: _output.isEmpty ? DS.neutral400 : DS.neutral900,
                      ),
                    ),
                  ),
          ),
        ],
      ),
    );
}
