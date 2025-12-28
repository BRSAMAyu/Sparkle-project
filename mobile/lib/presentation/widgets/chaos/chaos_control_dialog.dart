import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/core/design/design_system.dart';

class ChaosControlDialog extends StatefulWidget {
  const ChaosControlDialog({super.key});

  @override
  State<ChaosControlDialog> createState() => _ChaosControlDialogState();
}

class _ChaosControlDialogState extends State<ChaosControlDialog> {
  bool _isLoading = false;
  int _currentThreshold = 10000;
  int _queueLength = 0;

  @override
  void initState() {
    super.initState();
    _fetchStatus();
  }

  Future<void> _fetchStatus() async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConstants.baseUrl}/admin/chaos/status'),
      );
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          _currentThreshold = data['threshold'];
          _queueLength = data['queue_length'];
        });
      }
    } catch (e) {
      debugPrint('Failed to fetch chaos status: $e');
    }
  }

  Future<void> _setThreshold(int value) async {
    setState(() => _isLoading = true);
    try {
      final response = await http.post(
        Uri.parse('${ApiConstants.baseUrl}/admin/chaos/config'),
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Secret': 'sparkle_2025',
        },
        body: json.encode({
          'target': 'queue_persist',
          'value': value,
        }),
      );

      if (response.statusCode == 200) {
        await _fetchStatus();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('模式已切换: $value')),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('切换失败: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isTripped = _queueLength >= _currentThreshold;

    return AlertDialog(
      title: Row(
        children: [
          Icon(Icons.flash_on, color: DS.brandPrimaryConst),
          SizedBox(width: DS.smConst),
          const Text('Sparkle 混沌控制台'),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('队列水位: $_queueLength / $_currentThreshold',
              style: TextStyle(fontWeight: FontWeight.bold),),
          SizedBox(height: DS.sm),
          LinearProgressIndicator(
            value: _currentThreshold > 0 ? _queueLength / _currentThreshold : 1.0,
            color: isTripped ? DS.error : DS.success,
            backgroundColor: DS.brandPrimary200,
          ),
          SizedBox(height: DS.lg),
          Text('brandPrimary'),
          SizedBox(height: DS.sm),
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: _isLoading ? null : () => _setThreshold(10000),
                  icon: Icon(Icons.check_circle_outline),
                  label: Text('正常模式'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: DS.success.withValues(alpha: 0.1),
                    foregroundColor: DS.success,
                  ),
                ),
              ),
              SizedBox(width: DS.sm),
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: _isLoading ? null : () => _setThreshold(5),
                  icon: Icon(Icons.error_outline),
                  label: Text('施压模式'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: DS.error.withValues(alpha: 0.1),
                    foregroundColor: DS.error,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
      actions: [
        SparkleButton.ghost(label: '关闭', onPressed: () => Navigator.pop(context)),
      ],
    );
  }
}