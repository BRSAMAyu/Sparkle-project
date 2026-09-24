import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/network/api_timeouts.dart';

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
    unawaited(_fetchStatus());
  }

  Future<void> _fetchStatus() async {
    try {
      // N37：package:http 裸调用零超时（WT273 审计补登记）；超时走 catch。
      final response = await http
          .get(Uri.parse('${ApiConstants.baseUrl}/admin/chaos/status'))
          .timeout(ApiTimeouts.chaosAdminCallTimeout);
      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        final thresholdValue = data['threshold'];
        final queueValue = data['queue_length'];
        setState(() {
          _currentThreshold = thresholdValue is int
              ? thresholdValue
              : int.tryParse(thresholdValue?.toString() ?? '') ?? _currentThreshold;
          _queueLength = queueValue is int
              ? queueValue
              : int.tryParse(queueValue?.toString() ?? '') ?? _queueLength;
        });
      }
    } catch (e) {
      debugPrint('Failed to fetch chaos status: $e');
    }
  }

  Future<void> _setThreshold(int value) async {
    setState(() => _isLoading = true);
    try {
      // N37：同上，config 设置面整请求总闸；超时走 catch → 失败 SnackBar。
      final response = await http
          .post(
            Uri.parse('${ApiConstants.baseUrl}/admin/chaos/config'),
            headers: {
              'Content-Type': 'application/json',
              'X-Admin-Secret': 'sparkle_2025',
            },
            body: json.encode({
              'target': 'queue_persist',
              'value': value,
            }),
          )
          .timeout(ApiTimeouts.chaosAdminCallTimeout);

      if (response.statusCode == 200) {
        await _fetchStatus();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SparkleSnackBar.success(context.l10n.chaosModeSwitched(value)),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SparkleSnackBar.error(context.l10n.chaosModeSwitchFailed(e)),
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
          const SizedBox(width: DS.smConst),
          Text(context.l10n.chaosControlTitle),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.chaosQueueWaterLevel(_queueLength, _currentThreshold),
            style: const TextStyle(fontWeight: DS.fontWeightBold),
          ),
          const SizedBox(height: DS.sm),
          LinearProgressIndicator(
            value:
                _currentThreshold > 0 ? _queueLength / _currentThreshold : 1.0,
            color: isTripped ? DS.error : DS.success,
            backgroundColor: DS.brandPrimary200,
          ),
          const SizedBox(height: DS.lg),
          const Text('brandPrimary'),
          const SizedBox(height: DS.sm),
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: _isLoading ? null : () => _setThreshold(10000),
                  icon: const Icon(Icons.check_circle_outline),
                  label: Text(context.l10n.chaosNormalMode),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: DS.success.withValues(alpha: 0.1),
                    foregroundColor: DS.success,
                  ),
                ),
              ),
              const SizedBox(width: DS.sm),
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: _isLoading ? null : () => _setThreshold(5),
                  icon: const Icon(Icons.error_outline),
                  label: Text(context.l10n.chaosStressMode),
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
        SparkleButton.ghost(
            label: context.l10n.chaosClose, onPressed: () => Navigator.pop(context),),
      ],
    );
  }
}
