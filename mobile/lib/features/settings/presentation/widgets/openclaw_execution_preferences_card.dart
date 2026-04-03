import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/openclaw_execution_preferences_service.dart';

const Map<String, String> _modeLabels = <String, String>{
  'cautious': '谨慎模式',
  'balanced': '平衡模式',
  'autonomous': '信任模式',
  'custom': '自定义',
};

const Map<String, String> _ruleLabels = <String, String>{
  'browser_read': '浏览器读取',
  'browser_write': '浏览器写入',
  'file_read': '文件读取',
  'file_write': '文件写入',
  'file_delete': '文件删除',
  'shell_exec': '终端执行',
  'shell_read': '终端只读',
  'install': '安装类操作',
  'send': '发送/提交',
};

const Map<String, String> _ruleOptionLabels = <String, String>{
  'auto': '自动',
  'confirm': '确认',
  'skip': '跳过',
  'reject': '拒绝',
};

class OpenClawExecutionPreferencesCard extends ConsumerStatefulWidget {
  const OpenClawExecutionPreferencesCard({super.key});

  @override
  ConsumerState<OpenClawExecutionPreferencesCard> createState() =>
      _OpenClawExecutionPreferencesCardState();
}

class _OpenClawExecutionPreferencesCardState
    extends ConsumerState<OpenClawExecutionPreferencesCard> {
  OpenClawExecutionPreferences? _draft;
  bool _dirty = false;

  int? _parseOptionalInt(String value) {
    final trimmed = value.trim();
    if (trimmed.isEmpty) return null;
    final parsed = int.tryParse(trimmed);
    if (parsed == null || parsed <= 0) return null;
    return parsed;
  }

  @override
  Widget build(BuildContext context) {
    final service = ref.watch(openClawExecutionPreferencesProvider);
    final current = service.preferences;
    if (!_dirty || _draft == null) {
      _draft = current;
    }
    final draft = _draft ?? current;

    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  '执行偏好',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
              ),
              if (service.isLoading || service.isSaving)
                const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            draft.summary.isNotEmpty
                ? draft.summary
                : '你可以决定哪些动作自动执行，哪些动作仍然要你亲自确认。',
            style: DS.bodySmall.copyWith(
              color: DS.textSecondary,
              height: 1.45,
            ),
          ),
          if (service.error != null && service.error!.trim().isNotEmpty) ...[
            const SizedBox(height: DS.spacing10),
            Text(
              service.error!,
              style: DS.bodySmall.copyWith(color: DS.semanticError),
            ),
          ],
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: _modeLabels.entries
                .map(
                  (entry) => ChoiceChip(
                    label: Text(entry.value),
                    selected: draft.mode == entry.key,
                    onSelected: (_) {
                      setState(() {
                        _dirty = true;
                        _draft = draft.copyWith(mode: entry.key);
                      });
                    },
                  ),
                )
                .toList(),
          ),
          const SizedBox(height: DS.spacing10),
          Text(
            _modeDescription(draft.mode),
            style: DS.bodySmall.copyWith(
              color: DS.textSecondary,
              height: 1.45,
            ),
          ),
          if (draft.mode == 'custom') ...[
            const SizedBox(height: DS.spacing8),
            ..._ruleLabels.entries.map(
              (entry) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing10),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      entry.value,
                      style: DS.bodySmall.copyWith(
                        color: DS.textPrimary,
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                    const SizedBox(height: DS.spacing6),
                    DropdownButtonFormField<String>(
                      initialValue: draft.customRules[entry.key] ?? 'confirm',
                      key: ValueKey(
                        'execution-pref-${entry.key}-${draft.customRules[entry.key] ?? 'confirm'}',
                      ),
                      decoration: const InputDecoration(
                        isDense: true,
                        border: OutlineInputBorder(),
                      ),
                      items: _ruleOptionLabels.entries
                          .map(
                            (option) => DropdownMenuItem<String>(
                              value: option.key,
                              child: Text(option.value),
                            ),
                          )
                          .toList(),
                      onChanged: (value) {
                        if (value == null) {
                          return;
                        }
                        final nextRules =
                            Map<String, String>.from(draft.customRules)
                              ..[entry.key] = value;
                        setState(() {
                          _dirty = true;
                          _draft = draft.copyWith(customRules: nextRules);
                        });
                      },
                    ),
                  ],
                ),
              ),
            ),
          ],
          const SizedBox(height: DS.spacing8),
          SwitchListTile.adaptive(
            value: draft.autoExtendTimeout,
            contentPadding: EdgeInsets.zero,
            title: const Text('自动延长长任务超时'),
            subtitle: Text(
              '长耗时任务接近超时时，优先尝试自动续期。',
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            ),
            onChanged: (value) {
              setState(() {
                _dirty = true;
                _draft = draft.copyWith(autoExtendTimeout: value);
              });
            },
          ),
          SwitchListTile.adaptive(
            value: draft.trustAutoUpgrade,
            contentPadding: EdgeInsets.zero,
            title: const Text('允许系统基于历史自动建议升级信任'),
            subtitle: Text(
              '当某类动作长期稳定成功时，Sparkle 会建议减少确认频率。',
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            ),
            onChanged: (value) {
              setState(() {
                _dirty = true;
                _draft = draft.copyWith(trustAutoUpgrade: value);
              });
            },
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            '通知级别',
            style: DS.bodySmall.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
          const SizedBox(height: DS.spacing6),
          DropdownButtonFormField<String>(
            initialValue: draft.notificationLevel,
            key: ValueKey(
              'execution-pref-notification-${draft.notificationLevel}',
            ),
            decoration: const InputDecoration(
              isDense: true,
              border: OutlineInputBorder(),
            ),
            items: const [
              DropdownMenuItem(value: 'all', child: Text('全部通知')),
              DropdownMenuItem(value: 'essential', child: Text('仅关键节点')),
              DropdownMenuItem(value: 'silent', child: Text('安静模式')),
            ],
            onChanged: (value) {
              if (value == null) {
                return;
              }
              setState(() {
                _dirty = true;
                _draft = draft.copyWith(notificationLevel: value);
              });
            },
          ),
          const SizedBox(height: DS.spacing12),
          Text(
            '执行预算',
            style: DS.bodySmall.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
          const SizedBox(height: DS.spacing6),
          Text(
            '预算会在真正执行前生效。留空表示不限制；下面会显示当前已用 tokens。',
            style: DS.bodySmall.copyWith(
              color: DS.textSecondary,
              height: 1.45,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  key: ValueKey(
                    'execution-budget-daily-${draft.executionBudget.dailyTokenLimit ?? 'none'}',
                  ),
                  initialValue:
                      draft.executionBudget.dailyTokenLimit?.toString() ?? '',
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(
                    labelText: '每日上限',
                    helperText:
                        '已用 ${draft.executionBudget.dailyUsed} tokens',
                  ),
                  onChanged: (value) {
                    setState(() {
                      _dirty = true;
                      _draft = draft.copyWith(
                        executionBudget: draft.executionBudget.copyWith(
                          dailyTokenLimit: _parseOptionalInt(value),
                        ),
                      );
                    });
                  },
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: TextFormField(
                  key: ValueKey(
                    'execution-budget-monthly-${draft.executionBudget.monthlyTokenLimit ?? 'none'}',
                  ),
                  initialValue:
                      draft.executionBudget.monthlyTokenLimit?.toString() ?? '',
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(
                    labelText: '每月上限',
                    helperText:
                        '已用 ${draft.executionBudget.monthlyUsed} tokens',
                  ),
                  onChanged: (value) {
                    setState(() {
                      _dirty = true;
                      _draft = draft.copyWith(
                        executionBudget: draft.executionBudget.copyWith(
                          monthlyTokenLimit: _parseOptionalInt(value),
                        ),
                      );
                    });
                  },
                ),
              ),
            ],
          ),
          if (draft.recommendations.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Text(
              '系统建议',
              style: DS.bodySmall.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            ...draft.recommendations.map(
              (item) => Container(
                width: double.infinity,
                margin: const EdgeInsets.only(bottom: DS.spacing8),
                padding: const EdgeInsets.all(DS.spacing10),
                decoration: BoxDecoration(
                  color: DS.info.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: DS.info.withValues(alpha: 0.18),
                  ),
                ),
                child: Text(
                  '${_modeLabels[item.recommendedMode] ?? item.recommendedMode} · ${item.reason}',
                  style: DS.bodySmall.copyWith(
                    color: DS.textPrimary,
                    height: 1.4,
                  ),
                ),
              ),
            ),
          ],
          const SizedBox(height: DS.spacing12),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: (!_dirty || service.isSaving)
                  ? null
                  : () async {
                      final messenger = ScaffoldMessenger.of(context);
                      final ok = await ref
                          .read(openClawExecutionPreferencesProvider)
                          .savePreferences(_draft ?? draft);
                      if (!mounted) {
                        return;
                      }
                      if (ok) {
                        setState(() {
                          _dirty = false;
                        });
                        messenger.showSnackBar(
                          const SnackBar(content: Text('执行偏好已保存')),
                        );
                      }
                    },
              child: Text(_dirty ? '保存执行偏好' : '当前已同步'),
            ),
          ),
        ],
      ),
    );
  }

  String _modeDescription(String mode) {
    switch (mode) {
      case 'cautious':
        return '尽量每一步都先确认，更适合刚开始使用远程执行时。';
      case 'autonomous':
        return '低到中风险动作默认自动完成，只在危险动作前打断。';
      case 'custom':
        return '按动作类型单独指定自动、确认、跳过或拒绝。';
      default:
        return '读取类动作自动执行，写入和高风险动作保持确认。';
    }
  }
}
