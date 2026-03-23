import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';

// ─── Provider ────────────────────────────────────────────────────────────────

final groupModerationProvider = StateNotifierProvider.autoDispose
    .family<GroupModerationNotifier, AsyncValue<GroupModerationSettings>,
        String>((ref, groupId) => GroupModerationNotifier(
      ref.watch(communityRepositoryProvider), groupId,),);

class GroupModerationNotifier
    extends StateNotifier<AsyncValue<GroupModerationSettings>> {
  GroupModerationNotifier(this._repo, this._groupId)
      : super(const AsyncValue.loading()) {
    load();
  }

  final CommunityRepository _repo;
  final String _groupId;

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      final s = await _repo.getModerationSettings(_groupId);
      state = AsyncValue.data(s);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> save(GroupModerationSettings settings) async {
    await _repo.updateModerationSettings(_groupId, settings);
    state = AsyncValue.data(settings);
  }
}

// ─── Screen ──────────────────────────────────────────────────────────────────

class GroupModerationScreen extends ConsumerStatefulWidget {
  const GroupModerationScreen({required this.groupId, super.key});
  final String groupId;

  @override
  ConsumerState<GroupModerationScreen> createState() =>
      _GroupModerationScreenState();
}

class _GroupModerationScreenState
    extends ConsumerState<GroupModerationScreen> {
  bool _muteAll = false;
  int _slowModeSeconds = 0;
  final List<String> _keywordFilters = [];
  final _keywordController = TextEditingController();

  @override
  void dispose() {
    _keywordController.dispose();
    super.dispose();
  }

  void _applySettings(GroupModerationSettings s) {
    _muteAll = s.muteAll ?? false;
    _slowModeSeconds = s.slowModeSeconds ?? 0;
    _keywordFilters
      ..clear()
      ..addAll(s.keywordFilters ?? []);
  }

  Future<void> _save() async {
    try {
      unawaited(
        SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm),
      );
      await ref.read(groupModerationProvider(widget.groupId).notifier).save(
            GroupModerationSettings(
              muteAll: _muteAll,
              slowModeSeconds: _slowModeSeconds,
              keywordFilters: List.from(_keywordFilters),
            ),
          );
      if (!mounted) return;
      AppFeedback.success(context, '调节设置已保存');
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, '保存失败: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final settingsState =
        ref.watch(groupModerationProvider(widget.groupId));

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('群调节设置'),
        actions: [
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.save_outlined),
            onPressed: _save,
          ),
        ],
      ),
      child: settingsState.when(
        loading: () => const Center(child: LoadingIndicator()),
        error: (e, _) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text('加载失败: $e', style: TextStyle(color: DS.error)),
              const SizedBox(height: DS.md),
              SparkleButton.primary(
                label: '重试',
                onPressed: () => ref
                    .read(groupModerationProvider(widget.groupId).notifier)
                    .load(),
              ),
            ],
          ),
        ),
        data: (settings) {
          // Initialize state on first load
          if (_muteAll != (settings.muteAll ?? false) ||
              _slowModeSeconds != (settings.slowModeSeconds ?? 0)) {
            WidgetsBinding.instance.addPostFrameCallback((_) {
              if (mounted) setState(() => _applySettings(settings));
            });
          }

          return ContentConstraint(
            child: ListView(
              padding: const EdgeInsets.all(DS.spacing16),
              children: [
                // Mute all section
                SparkleStaggerItem(
                  index: 0,
                  child: GraphiteCardSurface(
                    surfaceRole: SparkleSurfaceRole.panel,
                    child: Column(
                      children: [
                        SwitchListTile(
                          title: const Text('全体禁言'),
                          subtitle: const Text('开启后只有管理员可以发言'),
                          value: _muteAll,
                          onChanged: (v) {
                            unawaited(
                              SensoryFeedbackService.emit(
                                SensoryFeedbackEvent.selection,
                              ),
                            );
                            setState(() => _muteAll = v);
                          },
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: DS.spacing16),

                // Slow mode section
                SparkleStaggerItem(
                  index: 1,
                  child: GraphiteCardSurface(
                    surfaceRole: SparkleSurfaceRole.panel,
                    child: Padding(
                      padding: const EdgeInsets.all(DS.spacing16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                        Row(
                          children: [
                            const Text('慢速模式',
                                style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: DS.fontSizeBase,),),
                            const Spacer(),
                            Switch(
                              value: _slowModeSeconds > 0,
                              onChanged: (v) {
                                unawaited(
                                  SensoryFeedbackService.emit(
                                    SensoryFeedbackEvent.selection,
                                  ),
                                );
                                setState(
                                  () => _slowModeSeconds = v ? 30 : 0,
                                );
                              },
                            ),
                          ],
                        ),
                        if (_slowModeSeconds > 0) ...[
                          const SizedBox(height: DS.spacing8),
                          Text(
                            '发言间隔: $_slowModeSeconds 秒',
                            style: TextStyle(color: DS.textSecondary),
                          ),
                          Slider(
                            value: _slowModeSeconds.toDouble(),
                            min: 5,
                            max: 300,
                            divisions: 59,
                            label: '$_slowModeSeconds 秒',
                            onChanged: (v) =>
                                setState(() => _slowModeSeconds = v.toInt()),
                          ),
                        ],
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: DS.spacing16),

                // Keyword filters section
                SparkleStaggerItem(
                  index: 2,
                  child: GraphiteCardSurface(
                    surfaceRole: SparkleSurfaceRole.panel,
                    child: Padding(
                      padding: const EdgeInsets.all(DS.spacing16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                        const Text('关键词过滤',
                            style: TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: DS.fontSizeBase,),),
                        const SizedBox(height: DS.spacing8),
                        const Text(
                          '包含以下关键词的消息将被自动屏蔽',
                          style: TextStyle(fontSize: DS.fontSizeSm),
                        ),
                        const SizedBox(height: DS.spacing12),
                        if (_keywordFilters.isNotEmpty)
                          Wrap(
                            spacing: DS.spacing8,
                            runSpacing: DS.spacing4,
                            children: _keywordFilters
                                .map(
                                  (kw) => Chip(
                                    label: Text(kw),
                                    deleteIcon: const Icon(Icons.close, size: 16),
                                    onDeleted: () => setState(
                                        () => _keywordFilters.remove(kw),),
                                  ),
                                )
                                .toList(),
                          ),
                        const SizedBox(height: DS.spacing8),
                        Row(
                          children: [
                            Expanded(
                              child: TextField(
                                controller: _keywordController,
                                decoration: const InputDecoration(
                                  hintText: '添加关键词',
                                  border: OutlineInputBorder(),
                                ),
                                onSubmitted: (_) => _addKeyword(),
                              ),
                            ),
                            const SizedBox(width: DS.spacing8),
                            SparkleIconButton(
                              icon: const Icon(Icons.add),
                              onPressed: () {
                                unawaited(
                                  SensoryFeedbackService.emit(
                                    SensoryFeedbackEvent.confirm,
                                  ),
                                );
                                _addKeyword();
                              },
                            ),
                          ],
                        ),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: DS.spacing24),
                SparkleButton.primary(
                  label: '保存设置',
                  onPressed: _save,
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  void _addKeyword() {
    final kw = _keywordController.text.trim();
    if (kw.isEmpty || _keywordFilters.contains(kw)) return;
    setState(() {
      _keywordFilters.add(kw);
      _keywordController.clear();
    });
  }
}
