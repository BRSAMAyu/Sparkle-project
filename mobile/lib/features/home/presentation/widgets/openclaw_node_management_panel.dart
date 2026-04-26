import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/services/openclaw_execution_preferences_service.dart';
import 'package:sparkle/core/services/openclaw_node_inventory_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/openclaw/presentation/widgets/openclaw_primitives.dart';

const _affinityTargets = <(String, String)>[
  ('browser', '浏览器任务'),
  ('shell', '终端任务'),
  ('document', '文档任务'),
  ('api', '接口任务'),
];

class OpenClawNodeManagementPanel extends ConsumerStatefulWidget {
  const OpenClawNodeManagementPanel({super.key});

  @override
  ConsumerState<OpenClawNodeManagementPanel> createState() =>
      _OpenClawNodeManagementPanelState();
}

class _OpenClawNodeManagementPanelState
    extends ConsumerState<OpenClawNodeManagementPanel> {
  Map<String, String> _draftAffinity = <String, String>{};
  bool _hydrated = false;
  bool _dirty = false;

  void _syncDraft(OpenClawExecutionPreferences preferences) {
    if (_hydrated && _dirty) return;
    _draftAffinity = Map<String, String>.from(preferences.nodeAffinity);
    _hydrated = true;
  }

  Future<void> _saveAffinity() async {
    final service = ref.read(openClawExecutionPreferencesProvider);
    final current = service.preferences;
    final filtered = <String, String>{};
    for (final entry in _draftAffinity.entries) {
      final value = entry.value.trim();
      if (value.isNotEmpty) {
        filtered[entry.key] = value;
      }
    }
    final ok = await service.savePreferences(
      current.copyWith(nodeAffinity: filtered),
    );
    if (!mounted) return;
    if (ok) {
      _dirty = false;
    }
    unawaited(
      SensoryFeedbackService.emit(
        ok ? SensoryFeedbackEvent.success : SensoryFeedbackEvent.warning,
      ),
    );
    ScaffoldMessenger.of(context).showSnackBar(
      ok
          ? SparkleSnackBar.success('设备亲和性已保存')
          : SparkleSnackBar.error(service.error ?? '保存设备亲和性失败'),
    );
  }

  @override
  Widget build(BuildContext context) {
    final nodeService = ref.watch(openClawNodeInventoryProvider);
    final preferenceService = ref.watch(openClawExecutionPreferencesProvider);
    final preferences = preferenceService.preferences;
    _syncDraft(preferences);

    final nodes = nodeService.nodes;
    final onlineNodes =
        nodes.where((node) => node.connected).toList(growable: false);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: [
            OpenClawMetricPill(
              icon: Icons.hub_rounded,
              label: '${nodes.length} 台设备',
              tone: nodes.isNotEmpty
                  ? OpenClawVisualTone.active
                  : OpenClawVisualTone.offline,
            ),
            OpenClawMetricPill(
              icon: Icons.sensors_rounded,
              label: '${onlineNodes.length} 台在线',
              tone: onlineNodes.isNotEmpty
                  ? OpenClawVisualTone.connected
                  : OpenClawVisualTone.offline,
              emphasized: onlineNodes.isNotEmpty,
            ),
            if (_dirty)
              const OpenClawMetricPill(
                icon: Icons.tune_rounded,
                label: '有未保存设备偏好',
                tone: OpenClawVisualTone.attention,
                emphasized: true,
              ),
          ],
        ),
        const SizedBox(height: DS.spacing12),
        Text(
          '为不同类型的委派指定偏好设备。未指定时，Sparkle 会按在线状态、能力和负载自动挑选。',
          style: DS.bodySmall.copyWith(
            color: DS.textSecondary,
            height: 1.45,
          ),
        ),
        const SizedBox(height: DS.spacing12),
        if (nodeService.isLoading && nodes.isEmpty)
          const Center(
            child: Padding(
              padding: EdgeInsets.all(DS.spacing12),
              child: CircularProgressIndicator(),
            ),
          )
        else if (nodes.isEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(DS.spacing12),
            decoration: BoxDecoration(
              color: DS.surfaceSecondary,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  nodeService.error ?? '当前还没有发现任何已配对节点。',
                  style: DS.bodySmall.copyWith(
                    color: DS.textSecondary,
                    height: 1.45,
                  ),
                ),
                const SizedBox(height: DS.spacing8),
                TextButton.icon(
                  onPressed: () => unawaited(
                    ref.read(openClawNodeInventoryProvider).refresh(),
                  ),
                  icon: const Icon(Icons.refresh_rounded),
                  label: const Text('重新获取设备列表'),
                ),
              ],
            ),
          )
        else ...[
          ..._affinityTargets.map((target) {
            final key = target.$1;
            final label = target.$2;
            final currentValue = _draftAffinity[key] ?? '';
            return Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing12),
              child: DropdownButtonFormField<String>(
                initialValue: currentValue.isEmpty ? '' : currentValue,
                decoration: InputDecoration(
                  labelText: label,
                  helperText: '选择固定设备，或保留“自动选择”交给 Sparkle 调度。',
                ),
                items: [
                  const DropdownMenuItem<String>(
                    value: '',
                    child: Text('自动选择'),
                  ),
                  ...nodes.map(
                    (node) => DropdownMenuItem<String>(
                      value: node.nodeId,
                      child: Text(
                        '${node.name} · ${node.connected ? '在线' : '离线'}',
                      ),
                    ),
                  ),
                ],
                onChanged: (value) {
                  setState(() {
                    _draftAffinity[key] = value ?? '';
                    _dirty = true;
                  });
                },
              ),
            );
          }),
          Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: preferenceService.isSaving ? null : _saveAffinity,
                  icon: preferenceService.isSaving
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(
                              Colors.white,
                            ),
                          ),
                        )
                      : const Icon(Icons.save_rounded),
                  label: const Text('保存设备亲和性'),
                ),
              ),
              const SizedBox(width: DS.spacing12),
              OutlinedButton.icon(
                onPressed: () => unawaited(
                  ref.read(openClawNodeInventoryProvider).refresh(),
                ),
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('刷新设备'),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),
          ...nodes.map(
            (node) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing10),
              child: _OpenClawNodeCard(node: node),
            ),
          ),
        ],
      ],
    );
  }
}

class _OpenClawNodeCard extends StatelessWidget {
  const _OpenClawNodeCard({required this.node});

  final OpenClawNodeSummary node;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: node.connected
                ? DS.semanticSuccess.withValues(alpha: 0.18)
                : DS.border,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    node.name,
                    style: DS.bodyMedium.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                ),
                OpenClawMetricPill(
                  icon: node.connected
                      ? Icons.check_circle_rounded
                      : Icons.cloud_off_rounded,
                  label: node.connected ? '在线' : '离线',
                  tone: node.connected
                      ? OpenClawVisualTone.connected
                      : OpenClawVisualTone.offline,
                  emphasized: node.connected,
                ),
              ],
            ),
            const SizedBox(height: DS.spacing8),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: [
                OpenClawMetricPill(
                  icon: Icons.developer_board_rounded,
                  label: node.platform,
                ),
                OpenClawMetricPill(
                  icon: Icons.timelapse_rounded,
                  label: '${node.activeRuns} 个运行中',
                  tone: node.activeRuns > 0
                      ? OpenClawVisualTone.attention
                      : OpenClawVisualTone.active,
                ),
                OpenClawMetricPill(
                  icon: Icons.podcasts_rounded,
                  label: node.status,
                  tone: node.connected
                      ? OpenClawVisualTone.connected
                      : OpenClawVisualTone.offline,
                ),
              ],
            ),
            if (node.caps.isNotEmpty || node.commands.isNotEmpty) ...[
              const SizedBox(height: DS.spacing10),
              Text(
                [
                  if (node.caps.isNotEmpty)
                    '能力 ${node.caps.take(4).join(' / ')}',
                  if (node.commands.isNotEmpty)
                    '命令 ${node.commands.take(3).join(' / ')}',
                ].join(' · '),
                style: DS.bodySmall.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
              ),
            ],
          ],
        ),
      );
}
