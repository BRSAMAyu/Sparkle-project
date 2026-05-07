import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/services/openclaw_execution_preferences_service.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/l10n/app_localizations.dart';

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

  Map<String, String> _modeLabels(AppLocalizations l) => {
        'cautious': l.execPrefCautious,
        'balanced': l.execPrefBalanced,
        'autonomous': l.execPrefAutonomous,
        'custom': l.execPrefCustom,
      };

  Map<String, String> _ruleLabels(AppLocalizations l) => {
        'browser_read': l.execPrefBrowserRead,
        'browser_write': l.execPrefBrowserWrite,
        'file_read': l.execPrefFileRead,
        'file_write': l.execPrefFileWrite,
        'file_delete': l.execPrefFileDelete,
        'shell_exec': l.execPrefShellExec,
        'shell_read': l.execPrefShellRead,
        'install': l.execPrefInstall,
        'send': l.execPrefSend,
      };

  Map<String, String> _ruleOptionLabels(AppLocalizations l) => {
        'auto': l.execPrefAuto,
        'confirm': l.settingsConfirm,
        'skip': l.execPrefSkip,
        'reject': l.execPrefReject,
      };

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    final service = ref.watch(openClawExecutionPreferencesProvider);
    final current = service.preferences;
    if (!_dirty || _draft == null) {
      _draft = current;
    }
    final draft = _draft ?? current;
    final modeLabels = _modeLabels(l);
    final ruleLabels = _ruleLabels(l);
    final ruleOptions = _ruleOptionLabels(l);

    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  l.execPrefTitle,
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
                : l.execPrefDescription,
            style: DS.bodySmall.copyWith(
              color: DS.textSecondary,
              height: 1.52,
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
            children: modeLabels.entries
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
            _modeDescription(l, draft.mode),
            style: DS.bodySmall.copyWith(
              color: DS.textSecondary,
              height: 1.52,
            ),
          ),
          if (draft.mode == 'custom') ...[
            const SizedBox(height: DS.spacing8),
            ...ruleLabels.entries.map(
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
                      items: ruleOptions.entries
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
            title: Text(l.settingsAutoExtend),
            subtitle: Text(
              l.execPrefAutoExtendDesc,
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
            title: Text(l.settingsAutoSuggestTrust),
            subtitle: Text(
              l.execPrefTrustUpgradeDesc,
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
            l.execPrefNotificationLevel,
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
            items: [
              DropdownMenuItem(value: 'all', child: Text(l.settingsAllNotifications)),
              DropdownMenuItem(value: 'essential', child: Text(l.settingsCriticalOnly)),
              DropdownMenuItem(value: 'silent', child: Text(l.settingsQuietMode)),
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
            l.execPrefBudgetTitle,
            style: DS.bodySmall.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
          const SizedBox(height: DS.spacing6),
          Text(
            l.execPrefBudgetDescription,
            style: DS.bodySmall.copyWith(
              color: DS.textSecondary,
              height: 1.52,
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
                    labelText: l.settingsDailyLimit,
                    helperText:
                        l.execPrefTokensUsed(draft.executionBudget.dailyUsed),
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
                    labelText: l.settingsMonthlyLimit,
                    helperText: l.execPrefTokensUsed(draft.executionBudget.monthlyUsed),
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
              l.execPrefSystemSuggestion,
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
                  '${modeLabels[item.recommendedMode] ?? item.recommendedMode} · ${item.reason}',
                  style: DS.bodySmall.copyWith(
                    color: DS.textPrimary,
                    height: 1.52,
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
                          SparkleSnackBar.success(l.settingsPreferencesSaved),
                        );
                      }
                    },
              child: Text(_dirty ? l.settingsSavePreferences : l.execPrefSynced),
            ),
          ),
        ],
      ),
    );
  }

  String _modeDescription(AppLocalizations l, String mode) {
    switch (mode) {
      case 'cautious':
        return l.execPrefCautiousDesc;
      case 'autonomous':
        return l.execPrefAutonomousDesc;
      case 'custom':
        return l.execPrefCustomDesc;
      default:
        return l.execPrefBalancedDesc;
    }
  }
}
