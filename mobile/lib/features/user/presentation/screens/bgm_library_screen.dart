import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/services/bgm_service.dart';

class BgmLibraryScreen extends StatefulWidget {
  const BgmLibraryScreen({super.key});

  @override
  State<BgmLibraryScreen> createState() => _BgmLibraryScreenState();
}

class _BgmLibraryScreenState extends State<BgmLibraryScreen> {
  final TextEditingController _searchController = TextEditingController();

  bool _loading = true;
  bool _importing = false;
  BgmLibrarySnapshot? _librarySnapshot;
  BgmPlaybackSnapshot? _playbackSnapshot;
  BgmLibrarySourceKind? _sourceFilter;
  BgmMode _mode = BgmMode.adaptive;
  BgmPalette _palette = BgmPalette.adaptive;
  BgmIntensity _intensity = BgmIntensity.gentle;
  BgmVariety _variety = BgmVariety.balanced;
  double _volume = 0.85;
  bool _enabled = true;

  @override
  void initState() {
    super.initState();
    unawaited(_loadData());
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    final snapshot = await BgmService.librarySnapshot();
    final playback = await BgmService.currentPlaybackSnapshot();
    final mode = await BgmService.getMode();
    final palette = await BgmService.getPalette();
    final tuning = await BgmService.getUserTuning();
    final volume = await BgmService.getVolume();
    final enabled = await BgmService.isEnabled();
    if (!mounted) {
      return;
    }
    setState(() {
      _librarySnapshot = snapshot;
      _playbackSnapshot = playback;
      _mode = mode;
      _palette = palette;
      _intensity = tuning.intensity;
      _variety = tuning.variety;
      _volume = volume;
      _enabled = enabled;
      _loading = false;
    });
  }

  Future<void> _setMode(BgmMode mode) async {
    setState(() => _mode = mode);
    await BgmService.setMode(mode);
    await _loadData();
  }

  Future<void> _setPalette(BgmPalette palette) async {
    setState(() => _palette = palette);
    await BgmService.setPalette(palette);
    await _loadData();
  }

  Future<void> _setIntensity(BgmIntensity intensity) async {
    setState(() => _intensity = intensity);
    await BgmService.setIntensity(intensity);
    await _loadData();
  }

  Future<void> _setVariety(BgmVariety variety) async {
    setState(() => _variety = variety);
    await BgmService.setVariety(variety);
    await _loadData();
  }

  Future<void> _setVolume(double value) async {
    setState(() => _volume = value);
    await BgmService.setVolume(value);
    await _loadData();
  }

  Future<void> _setEnabled(bool value) async {
    setState(() => _enabled = value);
    await BgmService.setEnabled(value);
    await _loadData();
  }

  Future<void> _importTracks() async {
    setState(() => _importing = true);
    try {
      final imported = await BgmService.importTracksFromPicker();
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SparkleSnackBar.info(
          imported.isEmpty ? '没有导入新曲目' : '已导入 ${imported.length} 首本地音乐',
        ),
      );
      await _loadData();
    } finally {
      if (mounted) {
        setState(() => _importing = false);
      }
    }
  }

  Future<void> _playEntry(BgmLibraryEntry entry) async {
    if (!_enabled) {
      await BgmService.setEnabled(true);
    }
    if (_mode != BgmMode.continuous) {
      await BgmService.setMode(BgmMode.continuous);
    }
    await BgmService.playLibraryEntry(entry);
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SparkleSnackBar.info('正在播放 ${entry.title}，已切换到播放器模式'),
    );
    await _loadData();
  }

  Future<void> _removeEntry(BgmLibraryEntry entry) async {
    await BgmService.removeImportedTrack(entry.id);
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SparkleSnackBar.success('已移除 ${entry.title}'),
    );
    await _loadData();
  }

  List<BgmLibraryEntry> get _filteredEntries {
    final snapshot = _librarySnapshot;
    if (snapshot == null) {
      return const <BgmLibraryEntry>[];
    }
    final query = _searchController.text.trim().toLowerCase();
    return snapshot.entries.where((entry) {
      if (_sourceFilter != null && entry.sourceKind != _sourceFilter) {
        return false;
      }
      if (query.isEmpty) {
        return true;
      }
      return entry.title.toLowerCase().contains(query) ||
          entry.album.toLowerCase().contains(query) ||
          entry.sceneTags.any((tag) => tag.toLowerCase().contains(query));
    }).toList(growable: false);
  }

  @override
  Widget build(BuildContext context) {
    final snapshot = _librarySnapshot;
    return Scaffold(
      appBar: AppBar(
        title: const Text('BGM 曲库与播放器'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => context.pop(),
        ),
        actions: [
          IconButton(
            tooltip: '刷新',
            onPressed: _loading ? null : () => unawaited(_loadData()),
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.fromLTRB(
                DS.spacing16,
                DS.spacing12,
                DS.spacing16,
                DS.spacing32,
              ),
              children: [
                _buildNowPlayingCard(),
                const SizedBox(height: DS.spacing12),
                _buildPlayerModeCard(),
                const SizedBox(height: DS.spacing12),
                _buildQuickStrategyCard(),
                const SizedBox(height: DS.spacing12),
                _buildLibraryStatsCard(snapshot),
                const SizedBox(height: DS.spacing12),
                _buildImportCard(),
                const SizedBox(height: DS.spacing12),
                _buildFilterBar(),
                const SizedBox(height: DS.spacing12),
                if (_filteredEntries.isEmpty)
                  GraphiteCardSurface(
                    child: Padding(
                      padding: const EdgeInsets.all(DS.spacing16),
                      child: Text(
                        '当前筛选下没有曲目，可以尝试切换筛选或导入本地音乐。',
                        style: DS.bodyMedium.copyWith(color: DS.textSecondary),
                      ),
                    ),
                  )
                else
                  ..._filteredEntries.map(_buildEntryCard),
              ],
            ),
    );
  }

  Widget _buildNowPlayingCard() {
    final snapshot = _playbackSnapshot;
    final title = snapshot?.trackTitle ?? snapshot?.trackId ?? '当前未播放';
    final subtitle = snapshot?.album ?? snapshot?.sourceLabel ?? '等待播放中';
    final reason = snapshot?.selectionReason ?? '你可以在这里直接点播曲库里的任意曲目';
    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.graphic_eq_rounded),
              const SizedBox(width: DS.spacing8),
              Text('当前播放', style: DS.bodyLarge),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          Text(title, style: DS.titleLarge),
          const SizedBox(height: DS.spacing4),
          Text(
            subtitle,
            style: DS.bodyMedium.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing10),
          Text(
            reason,
            style: DS.bodySmall.copyWith(color: DS.textSecondary, height: 1.4),
          ),
        ],
      ),
    );
  }

  Widget _buildPlayerModeCard() {
    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('播放器模式', style: DS.bodyLarge),
          const SizedBox(height: DS.spacing6),
          Text(
            '播放器模式下音乐不会因页面跳转而被打断，适合把 Sparkle 当成舒缓音乐播放器来用。',
            style: DS.bodySmall.copyWith(color: DS.textSecondary, height: 1.4),
          ),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: BgmMode.values
                .map(
                  (mode) => ChoiceChip(
                    label: Text(_modeLabel(mode)),
                    selected: _mode == mode,
                    onSelected: (_) => unawaited(_setMode(mode)),
                  ),
                )
                .toList(),
          ),
          const SizedBox(height: DS.spacing12),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('启用背景音乐'),
            subtitle: const Text('关闭后播放器页也不会继续播放背景音乐'),
            value: _enabled,
            onChanged: (value) => unawaited(_setEnabled(value)),
            activeThumbColor: DS.primaryBase,
          ),
          Row(
            children: [
              const Icon(Icons.volume_down_rounded, size: 18),
              Expanded(
                child: Slider(
                  value: _volume,
                  onChanged: (value) => setState(() => _volume = value),
                  onChangeEnd: (value) => unawaited(_setVolume(value)),
                ),
              ),
              const Icon(Icons.volume_up_rounded, size: 18),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildQuickStrategyCard() {
    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('快速策略调节', style: DS.bodyLarge),
          const SizedBox(height: DS.spacing6),
          Text(
            '这里保留最常用的调节项，完整细项仍然可以在设置页里继续调整。',
            style: DS.bodySmall.copyWith(color: DS.textSecondary, height: 1.4),
          ),
          const SizedBox(height: DS.spacing12),
          _buildChipGroup<BgmPalette>(
            title: '风格取向',
            values: BgmPalette.values,
            selected: _palette,
            labelBuilder: _paletteLabel,
            onSelect: (value) => unawaited(_setPalette(value)),
          ),
          const SizedBox(height: DS.spacing12),
          _buildChipGroup<BgmIntensity>(
            title: '氛围强度',
            values: BgmIntensity.values,
            selected: _intensity,
            labelBuilder: _intensityLabel,
            onSelect: (value) => unawaited(_setIntensity(value)),
          ),
          const SizedBox(height: DS.spacing12),
          _buildChipGroup<BgmVariety>(
            title: '轮换节奏',
            values: BgmVariety.values,
            selected: _variety,
            labelBuilder: _varietyLabel,
            onSelect: (value) => unawaited(_setVariety(value)),
          ),
        ],
      ),
    );
  }

  Widget _buildLibraryStatsCard(BgmLibrarySnapshot? snapshot) {
    if (snapshot == null) {
      return const SizedBox.shrink();
    }
    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('曲库状态', style: DS.bodyLarge),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing10,
            runSpacing: DS.spacing10,
            children: [
              _buildStatChip('总曲目', '${snapshot.totalCount}'),
              _buildStatChip('精选曲库', '${snapshot.curatedCount}'),
              _buildStatChip('本地导入', '${snapshot.importedCount}'),
              _buildStatChip('系统兜底', '${snapshot.bundledCount}'),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          Text(
            '本地导入目录：${snapshot.importDirectoryPath}',
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing4),
          Text(
            '下载缓存目录：${snapshot.downloadDirectoryPath}',
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            '这两个目录已经准备好，后续可以直接接“默认只打包少量曲目，其余从服务器下载到本地”的轻量化方案。',
            style: DS.bodySmall.copyWith(color: DS.textSecondary, height: 1.4),
          ),
        ],
      ),
    );
  }

  Widget _buildImportCard() {
    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('导入与管理', style: DS.bodyLarge),
          const SizedBox(height: DS.spacing6),
          Text(
            '你可以把自己的舒缓音乐直接导入进来。点播任意曲目时，系统会自动切换到播放器模式，后续跳页也不会中断。',
            style: DS.bodySmall.copyWith(color: DS.textSecondary, height: 1.4),
          ),
          const SizedBox(height: DS.spacing12),
          Row(
            children: [
              FilledButton.icon(
                onPressed: _importing ? null : () => unawaited(_importTracks()),
                icon: _importing
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.library_music_rounded),
                label: const Text('导入本地歌曲'),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: TextField(
                  controller: _searchController,
                  onChanged: (_) => setState(() {}),
                  decoration: const InputDecoration(
                    hintText: '搜索曲目、专辑或场景标签',
                    prefixIcon: Icon(Icons.search_rounded),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildFilterBar() {
    return Wrap(
      spacing: DS.spacing8,
      runSpacing: DS.spacing8,
      children: [
        ChoiceChip(
          label: const Text('全部'),
          selected: _sourceFilter == null,
          onSelected: (_) => setState(() => _sourceFilter = null),
        ),
        ...BgmLibrarySourceKind.values.map(
          (kind) => ChoiceChip(
            label: Text(_sourceLabel(kind)),
            selected: _sourceFilter == kind,
            onSelected: (_) => setState(() => _sourceFilter = kind),
          ),
        ),
      ],
    );
  }

  Widget _buildEntryCard(BgmLibraryEntry entry) {
    final isPlaying = _playbackSnapshot?.trackId == entry.id;
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing10),
      child: GraphiteCardSurface(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(_sourceIcon(entry.sourceKind)),
                const SizedBox(width: DS.spacing10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(entry.title, style: DS.bodyLarge),
                      const SizedBox(height: 2),
                      Text(
                        '${_sourceLabel(entry.sourceKind)} · ${entry.album}',
                        style: DS.bodySmall.copyWith(color: DS.textSecondary),
                      ),
                    ],
                  ),
                ),
                if (isPlaying)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.spacing8,
                      vertical: DS.spacing4,
                    ),
                    decoration: BoxDecoration(
                      color: DS.primaryBase.withValues(alpha: 0.12),
                      borderRadius: DS.borderRadius16,
                    ),
                    child: Text(
                      '播放中',
                      style: DS.labelSmall.copyWith(color: DS.primaryBase),
                    ),
                  ),
                const SizedBox(width: DS.spacing4),
                IconButton(
                  tooltip: '播放',
                  onPressed: () => unawaited(_playEntry(entry)),
                  icon: const Icon(Icons.play_circle_fill_rounded),
                ),
                if (entry.sourceKind == BgmLibrarySourceKind.imported)
                  IconButton(
                    tooltip: '移除',
                    onPressed: () => unawaited(_removeEntry(entry)),
                    icon: const Icon(Icons.delete_outline_rounded),
                  ),
              ],
            ),
            const SizedBox(height: DS.spacing10),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: [
                _buildStatChip('标签', entry.sceneTags.take(3).join(' / ')),
                _buildStatChip('风格', entry.paletteTags.take(3).join(' / ')),
                _buildStatChip('能量', entry.energy.toStringAsFixed(2)),
                _buildStatChip('密度', entry.density.toStringAsFixed(2)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildChipGroup<T>({
    required String title,
    required List<T> values,
    required T selected,
    required String Function(T value) labelBuilder,
    required ValueChanged<T> onSelect,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: DS.labelSmall.copyWith(color: DS.textSecondary)),
        const SizedBox(height: DS.spacing8),
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: values
              .map(
                (value) => ChoiceChip(
                  label: Text(labelBuilder(value)),
                  selected: selected == value,
                  onSelected: (_) => onSelect(value),
                ),
              )
              .toList(),
        ),
      ],
    );
  }

  Widget _buildStatChip(String label, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        borderRadius: DS.borderRadius16,
        color: DS.surfaceSecondary,
      ),
      child: Text(
        '$label · $value',
        style: DS.labelSmall.copyWith(color: DS.textSecondary),
      ),
    );
  }

  String _modeLabel(BgmMode mode) => switch (mode) {
        BgmMode.adaptive => '跟随页面',
        BgmMode.continuous => '播放器模式',
        BgmMode.focusOnly => '仅专注',
        BgmMode.silent => '静音',
      };

  String _paletteLabel(BgmPalette palette) => switch (palette) {
        BgmPalette.adaptive => '自适应',
        BgmPalette.classical => '精选古典',
        BgmPalette.piano => '钢琴优先',
        BgmPalette.airy => '空灵氛围',
        BgmPalette.warm => '温暖轻快',
      };

  String _intensityLabel(BgmIntensity intensity) => switch (intensity) {
        BgmIntensity.gentle => '柔和',
        BgmIntensity.balanced => '平衡',
        BgmIntensity.lush => '丰盈',
      };

  String _varietyLabel(BgmVariety variety) => switch (variety) {
        BgmVariety.steady => '稳定',
        BgmVariety.balanced => '均衡',
        BgmVariety.dynamic => '灵动',
      };

  String _sourceLabel(BgmLibrarySourceKind kind) => switch (kind) {
        BgmLibrarySourceKind.curated => '精选曲库',
        BgmLibrarySourceKind.imported => '本地导入',
        BgmLibrarySourceKind.bundled => '系统兜底',
      };

  IconData _sourceIcon(BgmLibrarySourceKind kind) => switch (kind) {
        BgmLibrarySourceKind.curated => Icons.auto_awesome_rounded,
        BgmLibrarySourceKind.imported => Icons.folder_rounded,
        BgmLibrarySourceKind.bundled => Icons.inventory_2_outlined,
      };
}
