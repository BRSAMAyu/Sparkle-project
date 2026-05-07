import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
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
          imported.isEmpty
              ? context.l10n.bgmLibraryNoImport
              : context.l10n.bgmLibraryImportedCount(imported.length),
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
      SparkleSnackBar.info(context.l10n.bgmLibraryPlayingSwitched(entry.title)),
    );
    await _loadData();
  }

  Future<void> _removeEntry(BgmLibraryEntry entry) async {
    await BgmService.removeImportedTrack(entry.id);
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SparkleSnackBar.success(context.l10n.bgmLibraryRemoved(entry.title)),
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
        title: Text(context.l10n.bgmLibraryTitle),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => context.pop(),
        ),
        actions: [
          IconButton(
            tooltip: context.l10n.bgmLibraryRefresh,
            onPressed: _loading ? null : () => unawaited(_loadData()),
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: _loading
          ? const SparkleListSkeleton()
          : ListView.builder(
              padding: const EdgeInsets.fromLTRB(
                DS.spacing16,
                DS.spacing12,
                DS.spacing16,
                DS.spacing32,
              ),
              itemCount: 12 + (_filteredEntries.isEmpty
                  ? 1
                  : _filteredEntries.length),
              itemBuilder: (context, index) {
                switch (index) {
                  case 0: return _buildNowPlayingCard();
                  case 1: return const SizedBox(height: DS.spacing12);
                  case 2: return _buildPlayerModeCard();
                  case 3: return const SizedBox(height: DS.spacing12);
                  case 4: return _buildQuickStrategyCard();
                  case 5: return const SizedBox(height: DS.spacing12);
                  case 6: return _buildLibraryStatsCard(snapshot);
                  case 7: return const SizedBox(height: DS.spacing12);
                  case 8: return _buildImportCard();
                  case 9: return const SizedBox(height: DS.spacing12);
                  case 10: return _buildFilterBar();
                  case 11: return const SizedBox(height: DS.spacing12);
                  default:
                    if (_filteredEntries.isEmpty) {
                      return GraphiteCardSurface(
                        child: Padding(
                          padding: const EdgeInsets.all(DS.spacing16),
                          child: Text(
                            context.l10n.bgmLibraryEmptyFilter,
                            style:
                                DS.bodyMedium.copyWith(color: DS.textSecondary),
                          ),
                        ),
                      );
                    }
                    return _buildEntryCard(_filteredEntries[index - 12]);
                }
              },
            ),
    );
  }

  Widget _buildNowPlayingCard() {
    final snapshot = _playbackSnapshot;
    final title = snapshot?.trackTitle ?? snapshot?.trackId ?? context.l10n.bgmLibraryNotPlaying;
    final subtitle = snapshot?.album ?? snapshot?.sourceLabel ?? context.l10n.bgmLibraryWaitingPlay;
    final reason = snapshot?.selectionReason ?? context.l10n.bgmLibraryBrowseHint;
    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.graphic_eq_rounded),
              const SizedBox(width: DS.spacing8),
              Text(context.l10n.bgmLibraryNowPlaying, style: DS.bodyLarge),
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
          Text(context.l10n.bgmLibraryPlayerMode, style: DS.bodyLarge),
          const SizedBox(height: DS.spacing6),
          Text(
            context.l10n.bgmLibraryPlayerModeDesc,
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
            title: Text(context.l10n.bgmLibraryEnableBgm),
            subtitle: Text(context.l10n.bgmLibraryDisableHint),
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
          Text(context.l10n.bgmLibraryQuickStrategy, style: DS.bodyLarge),
          const SizedBox(height: DS.spacing6),
          Text(
            context.l10n.bgmLibraryQuickStrategyDesc,
            style: DS.bodySmall.copyWith(color: DS.textSecondary, height: 1.4),
          ),
          const SizedBox(height: DS.spacing12),
          _buildChipGroup<BgmPalette>(
            title: context.l10n.bgmLibraryStyleOrientation,
            values: BgmPalette.values,
            selected: _palette,
            labelBuilder: _paletteLabel,
            onSelect: (value) => unawaited(_setPalette(value)),
          ),
          const SizedBox(height: DS.spacing12),
          _buildChipGroup<BgmIntensity>(
            title: context.l10n.bgmLibraryIntensityLabel,
            values: BgmIntensity.values,
            selected: _intensity,
            labelBuilder: _intensityLabel,
            onSelect: (value) => unawaited(_setIntensity(value)),
          ),
          const SizedBox(height: DS.spacing12),
          _buildChipGroup<BgmVariety>(
            title: context.l10n.bgmLibraryVarietyLabel,
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
          Text(context.l10n.bgmLibraryStats, style: DS.bodyLarge),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing10,
            runSpacing: DS.spacing10,
            children: [
              _buildStatChip(context.l10n.bgmLibraryTotalTracks, '${snapshot.totalCount}'),
              _buildStatChip(context.l10n.bgmLibraryCurated, '${snapshot.curatedCount}'),
              _buildStatChip(context.l10n.bgmLibraryImportedLabel, '${snapshot.importedCount}'),
              _buildStatChip(context.l10n.bgmLibraryBundled, '${snapshot.bundledCount}'),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          Text(
            context.l10n.bgmLibraryImportDir(snapshot.importDirectoryPath),
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing4),
          Text(
            context.l10n.bgmLibraryCacheDir(snapshot.downloadDirectoryPath),
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            context.l10n.bgmLibraryDirReadyNote,
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
          Text(context.l10n.bgmLibraryImportManage, style: DS.bodyLarge),
          const SizedBox(height: DS.spacing6),
          Text(
            context.l10n.bgmLibraryImportManageDesc,
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
                label: Text(context.l10n.bgmLibraryImportLocal),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: TextField(
                  controller: _searchController,
                  onChanged: (_) => setState(() {}),
                  decoration: InputDecoration(
                    hintText: context.l10n.bgmLibrarySearchHint,
                    prefixIcon: const Icon(Icons.search_rounded),
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
          label: Text(context.l10n.bgmLibraryFilterAll),
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
                      context.l10n.bgmLibraryPlaying,
                      style: DS.labelSmall.copyWith(color: DS.primaryBase),
                    ),
                  ),
                const SizedBox(width: DS.spacing4),
                IconButton(
                  tooltip: context.l10n.bgmLibraryPlay,
                  onPressed: () => unawaited(_playEntry(entry)),
                  icon: const Icon(Icons.play_circle_fill_rounded),
                ),
                if (entry.sourceKind == BgmLibrarySourceKind.imported)
                  IconButton(
                    tooltip: context.l10n.bgmLibraryRemove,
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
                _buildStatChip(context.l10n.bgmLibraryTags, entry.sceneTags.take(3).join(' / ')),
                _buildStatChip(context.l10n.bgmLibraryStyle, entry.paletteTags.take(3).join(' / ')),
                _buildStatChip(context.l10n.bgmLibraryEnergy, entry.energy.toStringAsFixed(2)),
                _buildStatChip(context.l10n.bgmLibraryDensity, entry.density.toStringAsFixed(2)),
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
        BgmMode.adaptive => context.l10n.bgmLibraryModeAdaptive,
        BgmMode.continuous => context.l10n.bgmLibraryModeContinuous,
        BgmMode.focusOnly => context.l10n.bgmLibraryModeFocusOnly,
        BgmMode.silent => context.l10n.bgmLibraryModeSilent,
      };

  String _paletteLabel(BgmPalette palette) => switch (palette) {
        BgmPalette.adaptive => context.l10n.bgmLibraryPaletteAdaptive,
        BgmPalette.classical => context.l10n.bgmLibraryPaletteClassical,
        BgmPalette.piano => context.l10n.bgmLibraryPalettePiano,
        BgmPalette.airy => context.l10n.bgmLibraryPaletteAiry,
        BgmPalette.warm => context.l10n.bgmLibraryPaletteWarm,
      };

  String _intensityLabel(BgmIntensity intensity) => switch (intensity) {
        BgmIntensity.gentle => context.l10n.bgmLibraryIntensityGentle,
        BgmIntensity.balanced => context.l10n.bgmLibraryIntensityBalanced,
        BgmIntensity.lush => context.l10n.bgmLibraryIntensityLush,
      };

  String _varietyLabel(BgmVariety variety) => switch (variety) {
        BgmVariety.steady => context.l10n.bgmLibraryVarietySteady,
        BgmVariety.balanced => context.l10n.bgmLibraryVarietyBalanced,
        BgmVariety.dynamic => context.l10n.bgmLibraryVarietyDynamic,
      };

  String _sourceLabel(BgmLibrarySourceKind kind) => switch (kind) {
        BgmLibrarySourceKind.curated => context.l10n.bgmLibrarySourceCurated,
        BgmLibrarySourceKind.imported => context.l10n.bgmLibrarySourceImported,
        BgmLibrarySourceKind.bundled => context.l10n.bgmLibrarySourceBundled,
      };

  IconData _sourceIcon(BgmLibrarySourceKind kind) => switch (kind) {
        BgmLibrarySourceKind.curated => Icons.auto_awesome_rounded,
        BgmLibrarySourceKind.imported => Icons.folder_rounded,
        BgmLibrarySourceKind.bundled => Icons.inventory_2_outlined,
      };
}
