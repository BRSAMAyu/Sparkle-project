import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/documents/data/models/document_library_models.dart';
import 'package:sparkle/features/documents/presentation/providers/document_library_provider.dart';
import 'package:sparkle/features/file/presentation/widgets/file_picker_with_presigned.dart';
import 'package:sparkle/features/galaxy/galaxy_routes.dart';

class DocumentLibraryScreen extends ConsumerStatefulWidget {
  const DocumentLibraryScreen({super.key});

  @override
  ConsumerState<DocumentLibraryScreen> createState() =>
      _DocumentLibraryScreenState();
}

class _DocumentLibraryScreenState extends ConsumerState<DocumentLibraryScreen> {
  late final TextEditingController _searchController;

  @override
  void initState() {
    super.initState();
    _searchController = TextEditingController();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(documentLibraryProvider);
    final l10n = context.l10n;

    return SparklePageScaffold(
      role: SparklePageRole.content,
      safeArea: false,
      appBar: AppBar(
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0.82),
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () {
            final router = GoRouter.of(context);
            if (router.canPop()) {
              context.pop();
            } else {
              context.go('/profile');
            }
          },
        ),
        title: Text(l10n.studyMaterialsTitle),
        actions: [
          SparkleButton.ghost(
            label: l10n.studyMaterialsUploadCtaShort,
            onPressed: _openUploadSheet,
          ),
          const SizedBox(width: DS.spacing8),
        ],
      ),
      backgroundGradient: LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          DS.deepSpaceStart.withValues(alpha: 0.22),
          DS.surfacePrimary,
          DS.surfaceCanvas,
        ],
      ),
      child: ContentConstraint(
        child: RefreshIndicator(
          onRefresh: () => ref.read(documentLibraryProvider.notifier).refresh(),
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(
              parent: BouncingScrollPhysics(),
            ),
            slivers: [
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(
                    DS.spacing16,
                    DS.spacing16,
                    DS.spacing16,
                    DS.spacing12,
                  ),
                  child: _LibraryHeroCard(
                    state: state,
                    onUpload: _openUploadSheet,
                    onRefresh: () =>
                        ref.read(documentLibraryProvider.notifier).refresh(),
                  ),
                ),
              ),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(
                    DS.spacing16,
                    0,
                    DS.spacing16,
                    DS.spacing8,
                  ),
                  child: _SearchField(
                    controller: _searchController,
                    onChanged: ref
                        .read(documentLibraryProvider.notifier)
                        .setSearchQuery,
                    onClear: () {
                      _searchController.clear();
                      ref
                          .read(documentLibraryProvider.notifier)
                          .setSearchQuery('');
                    },
                  ),
                ),
              ),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
                  child: _FilterSection(state: state),
                ),
              ),
              const SliverToBoxAdapter(
                child: SizedBox(height: DS.spacing12),
              ),
              ..._buildContent(context, state),
              const SliverToBoxAdapter(
                child: SizedBox(height: DS.spacing32),
              ),
            ],
          ),
        ),
      ),
    );
  }

  List<Widget> _buildContent(
    BuildContext context,
    DocumentLibraryState state,
  ) {
    final l10n = context.l10n;
    return state.documents.when(
      loading: () => const <Widget>[
        SliverFillRemaining(
          hasScrollBody: false,
          child: Center(child: CircularProgressIndicator()),
        ),
      ],
      error: (error, _) => <Widget>[
        SliverFillRemaining(
          hasScrollBody: false,
          child: Center(
            child: Padding(
              padding: const EdgeInsets.all(DS.spacing24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.error_outline_rounded,
                    size: 52,
                    color: DS.error,
                  ),
                  const SizedBox(height: DS.spacing12),
                  Text(
                    l10n.studyMaterialsLoadError,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          color: DS.textPrimary,
                          fontWeight: FontWeight.w700,
                        ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: DS.spacing8),
                  Text(
                    error.toString(),
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: DS.textSecondary,
                        ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: DS.spacing16),
                  SparkleButton.primary(
                    label: l10n.retry,
                    onPressed: () => ref
                        .read(documentLibraryProvider.notifier)
                        .refresh(),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
      data: (librarySnapshot) {
        final visible = state.filtered;
        if (visible.isEmpty) {
          return <Widget>[
            SliverFillRemaining(
              hasScrollBody: false,
              child: _DocumentsEmptyState(
                hasAnyDocuments: state.allDocuments.isNotEmpty,
                searchActive: state.searchQuery.trim().isNotEmpty ||
                    state.statusFilter != null ||
                    state.subjectFilter != null ||
                    state.nodeFilterId != null ||
                    state.highlyCitedOnly ||
                    state.dateFilter != DocumentDateFilter.all,
                onUpload: _openUploadSheet,
                onResetFilters: () {
                  _searchController.clear();
                  final notifier = ref.read(documentLibraryProvider.notifier);
                  notifier.setSearchQuery('');
                  notifier.setStatusFilter(null);
                  notifier.setSubjectFilter(null);
                  notifier.clearNodeFilter();
                  if (state.highlyCitedOnly) {
                    notifier.toggleHighlyCitedOnly();
                  }
                  if (state.dateFilter != DocumentDateFilter.all) {
                    notifier.setDateFilter(DocumentDateFilter.all);
                  }
                },
              ),
            ),
          ];
        }

        return <Widget>[
          SliverList(
            delegate: SliverChildBuilderDelegate(
              (context, index) {
                final document = visible[index];
                return Padding(
                  padding: const EdgeInsets.fromLTRB(
                    DS.spacing16,
                    0,
                    DS.spacing16,
                    DS.spacing12,
                  ),
                  child: _DocumentCard(
                    document: document,
                    expanded:
                        state.expandedDocumentIds.contains(document.fileId),
                    onToggleExpanded: () => ref
                        .read(documentLibraryProvider.notifier)
                        .toggleExpanded(document.fileId),
                    onDelete: () => _confirmDelete(document),
                    onShareToGroup: () => _showShareSheet(document),
                    onRefresh: () =>
                        ref.read(documentLibraryProvider.notifier).refresh(),
                    onFilterByNode: (node) => ref
                        .read(documentLibraryProvider.notifier)
                        .setNodeFilter(
                          nodeId: node.nodeId,
                          nodeName: node.name,
                        ),
                  ),
                );
              },
              childCount: visible.length,
            ),
          ),
        ];
      },
    );
  }

  Future<void> _openUploadSheet() async {
    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (sheetContext) => FilePickerWithPresignedUpload(
        onUploaded: (uploadedFile) {
          if (!mounted) return;
          Navigator.of(sheetContext).pop();
          ScaffoldMessenger.of(this.context).showSnackBar(
            SnackBar(content: Text(this.context.l10n.studyMaterialsUploadSuccess)),
          );
          unawaited(ref.read(documentLibraryProvider.notifier).refresh());
        },
        onError: (message) {
          if (!mounted) return;
          ScaffoldMessenger.of(this.context).showSnackBar(
            SnackBar(
              content: Text(message),
              backgroundColor: DS.error,
            ),
          );
        },
      ),
    );
  }

  Future<void> _confirmDelete(DocumentLibraryItem document) async {
    final l10n = context.l10n;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(l10n.studyMaterialsDeleteTitle),
        content: Text(
          l10n.studyMaterialsDeleteMessage(document.filename),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: DS.error,
            ),
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: Text(l10n.studyMaterialsDeleteAction),
          ),
        ],
      ),
    );

    if (confirmed != true || !mounted) return;

    try {
      await ref
          .read(documentLibraryProvider.notifier)
          .deleteDocument(document.fileId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.studyMaterialsDeleteSuccess)),
      );
    } on Exception catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(l10n.studyMaterialsDeleteFailure(error)),
          backgroundColor: DS.error,
        ),
      );
    }
  }

  Future<void> _showShareSheet(DocumentLibraryItem document) async {
    final l10n = context.l10n;
    final groupsFuture =
        ref.read(communityRepositoryProvider).getMyGroups();

    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (sheetContext) => GraphiteModalSurface(
        title: l10n.studyMaterialsShareSheetTitle,
        expandChild: true,
        child: FutureBuilder<List<GroupListItem>>(
          future: groupsFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }

            if (snapshot.hasError) {
              return Center(
                child: Padding(
                  padding: const EdgeInsets.all(DS.spacing16),
                  child: Text(
                    l10n.studyMaterialsShareLoadGroupsError,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: DS.textSecondary,
                        ),
                    textAlign: TextAlign.center,
                  ),
                ),
              );
            }

            final groups = snapshot.data ?? const <GroupListItem>[];
            if (groups.isEmpty) {
              return Center(
                child: Padding(
                  padding: const EdgeInsets.all(DS.spacing16),
                  child: Text(
                    l10n.studyMaterialsShareEmptyGroups,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: DS.textSecondary,
                        ),
                    textAlign: TextAlign.center,
                  ),
                ),
              );
            }

            return ListView.separated(
              shrinkWrap: true,
              itemCount: groups.length,
              separatorBuilder: (context, index) =>
                  Divider(color: DS.borderSubtle),
              itemBuilder: (context, index) {
                final group = groups[index];
                return ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Container(
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      color: DS.brandPrimary.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Icon(
                      Icons.groups_rounded,
                      color: DS.brandPrimary,
                    ),
                  ),
                  title: Text(group.name),
                  subtitle: Text(
                    l10n.studyMaterialsShareGroupSubtitle(group.memberCount),
                  ),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () async {
                    Navigator.of(sheetContext).pop();
                    try {
                      await ref
                          .read(documentLibraryProvider.notifier)
                          .shareToGroup(
                            fileId: document.fileId,
                            groupId: group.id,
                          );
                      if (!mounted) return;
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            l10n.studyMaterialsShareSuccess(group.name),
                          ),
                        ),
                      );
                    } on Exception catch (error) {
                      if (!mounted) return;
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(l10n.studyMaterialsShareFailure(error)),
                          backgroundColor: DS.error,
                        ),
                      );
                    }
                  },
                );
              },
            );
          },
        ),
      ),
    );
  }
}

class _LibraryHeroCard extends StatelessWidget {
  const _LibraryHeroCard({
    required this.state,
    required this.onUpload,
    required this.onRefresh,
  });

  final DocumentLibraryState state;
  final VoidCallback onUpload;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    final documents = state.allDocuments;
    final readyCount = documents
        .where((doc) => doc.effectiveStatus == DocumentStatus.ready)
        .length;
    final processingCount = documents
        .where((doc) => doc.effectiveStatus == DocumentStatus.processing)
        .length;
    final weeklyReferences = documents.fold<int>(
      0,
      (sum, doc) => sum + doc.citationInsight.referencesThisWeek,
    );

    return Container(
      padding: const EdgeInsets.all(DS.spacing20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            DS.deepSpaceStart.withValues(alpha: 0.94),
            DS.surfacePanel.withValues(alpha: 0.96),
            DS.deepSpaceEnd.withValues(alpha: 0.88),
          ],
        ),
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: DS.borderSubtle),
        boxShadow: DS.shadowMd,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.l10n.studyMaterialsHeroEyebrow,
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                            color: DS.brandPrimary,
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: DS.spacing8),
                    Text(
                      context.l10n.studyMaterialsHeroTitle,
                      style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                            color: Colors.white,
                            fontWeight: FontWeight.w800,
                            height: 1.1,
                          ),
                    ),
                    const SizedBox(height: DS.spacing8),
                    Text(
                      context.l10n.studyMaterialsHeroSubtitle,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: Colors.white.withValues(alpha: 0.76),
                            height: 1.45,
                          ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: DS.spacing16),
              const _MiniGalaxyIllustration(),
            ],
          ),
          const SizedBox(height: DS.spacing18),
          Wrap(
            spacing: DS.spacing12,
            runSpacing: DS.spacing12,
            children: [
              _HeroMetric(
                label: context.l10n.studyMaterialsMetricDocs,
                value: '${documents.length}',
              ),
              _HeroMetric(
                label: context.l10n.studyMaterialsMetricReady,
                value: '$readyCount',
              ),
              _HeroMetric(
                label: context.l10n.studyMaterialsMetricInMotion,
                value: '$processingCount',
              ),
              _HeroMetric(
                label: context.l10n.studyMaterialsMetricWeeklyRefs,
                value: '$weeklyReferences',
              ),
            ],
          ),
          const SizedBox(height: DS.spacing18),
          Row(
            children: [
              Expanded(
                child: SparkleButton.primary(
                  label: context.l10n.studyMaterialsUploadCta,
                  onPressed: onUpload,
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: SparkleButton.ghost(
                  label: context.l10n.studyMaterialsRefreshCta,
                  onPressed: onRefresh,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HeroMetric extends StatelessWidget {
  const _HeroMetric({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 120),
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing12,
        vertical: DS.spacing12,
      ),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            value,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: DS.spacing4),
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: Colors.white.withValues(alpha: 0.7),
                ),
          ),
        ],
      ),
    );
  }
}

class _MiniGalaxyIllustration extends StatelessWidget {
  const _MiniGalaxyIllustration();

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 92,
      height: 92,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    DS.brandPrimary.withValues(alpha: 0.32),
                    DS.brandSecondary.withValues(alpha: 0.06),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),
          Positioned(
            left: 20,
            top: 18,
            child: Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(
                  colors: [
                    DS.brandPrimary.withValues(alpha: 0.82),
                    DS.info.withValues(alpha: 0.78),
                  ],
                ),
                boxShadow: [
                  BoxShadow(
                    color: DS.brandPrimary.withValues(alpha: 0.28),
                    blurRadius: 22,
                    spreadRadius: 1,
                  ),
                ],
              ),
              child: const Icon(
                Icons.auto_awesome_rounded,
                color: Colors.white,
              ),
            ),
          ),
          Positioned(
            right: 4,
            top: 10,
            child: _GlowDot(color: DS.warning, size: 10),
          ),
          Positioned(
            left: 8,
            bottom: 10,
            child: _GlowDot(color: DS.success, size: 12),
          ),
          Positioned(
            right: 18,
            bottom: 2,
            child: _GlowDot(color: DS.brandSecondary, size: 8),
          ),
        ],
      ),
    );
  }
}

class _GlowDot extends StatelessWidget {
  const _GlowDot({
    required this.color,
    required this.size,
  });

  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        boxShadow: [
          BoxShadow(
            color: color.withValues(alpha: 0.34),
            blurRadius: 14,
            spreadRadius: 1,
          ),
        ],
      ),
    );
  }
}

class _SearchField extends StatelessWidget {
  const _SearchField({
    required this.controller,
    required this.onChanged,
    required this.onClear,
  });

  final TextEditingController controller;
  final ValueChanged<String> onChanged;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      onChanged: onChanged,
      decoration: InputDecoration(
        hintText: context.l10n.studyMaterialsSearchHint,
        prefixIcon: const Icon(Icons.search_rounded),
        suffixIcon: controller.text.isEmpty
            ? null
            : IconButton(
                icon: const Icon(Icons.close_rounded),
                onPressed: onClear,
              ),
        filled: true,
        fillColor: DS.surfaceSecondary,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(20),
          borderSide: BorderSide.none,
        ),
      ),
    );
  }
}

class _FilterSection extends ConsumerWidget {
  const _FilterSection({required this.state});

  final DocumentLibraryState state;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifier = ref.read(documentLibraryProvider.notifier);
    final l10n = context.l10n;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        GraphiteSectionTitle(
          title: l10n.studyMaterialsFilterTitle,
          trailing: state.nodeFilterId == null
              ? null
              : TextButton(
                  onPressed: notifier.clearNodeFilter,
                  child: Text(l10n.studyMaterialsFilterClearNode),
                ),
        ),
        const SizedBox(height: DS.spacing10),
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: [
            _FilterChip(
              label: l10n.studyMaterialsFilterAllStatus,
              selected: state.statusFilter == null,
              onTap: () => notifier.setStatusFilter(null),
            ),
            _FilterChip(
              label: l10n.studyMaterialsStatusProcessing,
              selected: state.statusFilter == DocumentStatus.processing,
              onTap: () =>
                  notifier.setStatusFilter(DocumentStatus.processing),
            ),
            _FilterChip(
              label: l10n.studyMaterialsStatusReady,
              selected: state.statusFilter == DocumentStatus.ready,
              onTap: () => notifier.setStatusFilter(DocumentStatus.ready),
            ),
            _FilterChip(
              label: l10n.studyMaterialsStatusFailed,
              selected: state.statusFilter == DocumentStatus.failed,
              onTap: () => notifier.setStatusFilter(DocumentStatus.failed),
            ),
          ],
        ),
        const SizedBox(height: DS.spacing8),
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: [
            _FilterChip(
              label: l10n.studyMaterialsDateAll,
              selected: state.dateFilter == DocumentDateFilter.all,
              onTap: () => notifier.setDateFilter(DocumentDateFilter.all),
            ),
            _FilterChip(
              label: l10n.studyMaterialsDate7d,
              selected: state.dateFilter == DocumentDateFilter.last7Days,
              onTap: () =>
                  notifier.setDateFilter(DocumentDateFilter.last7Days),
            ),
            _FilterChip(
              label: l10n.studyMaterialsDate30d,
              selected: state.dateFilter == DocumentDateFilter.last30Days,
              onTap: () =>
                  notifier.setDateFilter(DocumentDateFilter.last30Days),
            ),
            _FilterChip(
              label: l10n.studyMaterialsDate90d,
              selected: state.dateFilter == DocumentDateFilter.last90Days,
              onTap: () =>
                  notifier.setDateFilter(DocumentDateFilter.last90Days),
            ),
            _FilterChip(
              label: l10n.studyMaterialsFilterHighlyCited,
              selected: state.highlyCitedOnly,
              onTap: notifier.toggleHighlyCitedOnly,
            ),
          ],
        ),
        if (state.availableSubjectFilters.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _FilterChip(
                label: l10n.studyMaterialsFilterAllSubjects,
                selected: state.subjectFilter == null,
                onTap: () => notifier.setSubjectFilter(null),
              ),
              ...state.availableSubjectFilters.map(
                (subjectCode) => _FilterChip(
                  label: _localizedSubjectLabel(context, subjectCode),
                  selected: state.subjectFilter == subjectCode,
                  onTap: () => notifier.setSubjectFilter(subjectCode),
                ),
              ),
            ],
          ),
        ],
        if (state.nodeFilterId != null && state.nodeFilterName != null) ...[
          const SizedBox(height: DS.spacing8),
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing12,
              vertical: DS.spacing10,
            ),
            decoration: BoxDecoration(
              color: DS.brandPrimary.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: DS.brandPrimary.withValues(alpha: 0.16),
              ),
            ),
            child: Row(
              children: [
                Icon(
                  Icons.hub_rounded,
                  size: 18,
                  color: DS.brandPrimary,
                ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: Text(
                    l10n.studyMaterialsFilterNode(state.nodeFilterName!),
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: DS.textPrimary,
                          fontWeight: FontWeight.w600,
                        ),
                  ),
                ),
                TextButton(
                  onPressed: notifier.clearNodeFilter,
                  child: Text(l10n.studyMaterialsFilterClearNode),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }

  static String _localizedSubjectLabel(BuildContext context, String code) {
    switch (code) {
      case 'COSMOS':
        return context.l10n.studyMaterialsSubjectCosmos;
      case 'TECH':
        return context.l10n.studyMaterialsSubjectTech;
      case 'ART':
        return context.l10n.studyMaterialsSubjectArt;
      case 'CIVILIZATION':
        return context.l10n.studyMaterialsSubjectCivilization;
      case 'LIFE':
        return context.l10n.studyMaterialsSubjectLife;
      case 'WISDOM':
        return context.l10n.studyMaterialsSubjectWisdom;
      default:
        return context.l10n.studyMaterialsSubjectGeneral;
    }
  }
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return FilterChip(
      label: Text(label),
      selected: selected,
      onSelected: (selectedValue) => onTap(),
      selectedColor: DS.brandPrimary.withValues(alpha: 0.14),
      labelStyle: Theme.of(context).textTheme.labelMedium?.copyWith(
            color: selected ? DS.brandPrimary : DS.textSecondary,
            fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
          ),
      side: BorderSide(
        color: selected
            ? DS.brandPrimary.withValues(alpha: 0.3)
            : DS.borderSubtle,
      ),
    );
  }
}

class _DocumentCard extends StatelessWidget {
  const _DocumentCard({
    required this.document,
    required this.expanded,
    required this.onToggleExpanded,
    required this.onDelete,
    required this.onShareToGroup,
    required this.onRefresh,
    required this.onFilterByNode,
  });

  final DocumentLibraryItem document;
  final bool expanded;
  final VoidCallback onToggleExpanded;
  final VoidCallback onDelete;
  final VoidCallback onShareToGroup;
  final VoidCallback onRefresh;
  final ValueChanged<DocumentGalaxyNode> onFilterByNode;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final status = document.effectiveStatus;
    final nodePreview = document.attachedNodes.take(3).map((node) => node.name).join(' · ');

    return GraphiteCardSurface(
      padding: const EdgeInsets.all(DS.spacing18),
      surfaceRole: SparkleSurfaceRole.card,
      onTap: onToggleExpanded,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _DocumentGlyph(fileType: document.fileType),
              const SizedBox(width: DS.spacing14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      document.filename,
                      style: theme.textTheme.titleMedium?.copyWith(
                            color: DS.textPrimary,
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: DS.spacing6),
                    Wrap(
                      spacing: DS.spacing8,
                      runSpacing: DS.spacing6,
                      children: [
                        _PillLabel(
                          label: _subjectLabel(context, document.subjectArea),
                          icon: Icons.auto_awesome_motion_rounded,
                        ),
                        _StatusBadge(document: document),
                        if (document.processingStatus?.hasDraftsPending == true)
                          _DraftsPendingPill(
                            count: document.processingStatus!.draftsPending!,
                            onTap: () => context.push(GalaxyRoutes.draftReview),
                          ),
                        _PillLabel(
                          label: document.visibility == 'group'
                              ? context.l10n.studyMaterialsVisibilityGroup
                              : context.l10n.studyMaterialsVisibilityPrivate,
                          icon: document.visibility == 'group'
                              ? Icons.groups_rounded
                              : Icons.lock_outline_rounded,
                        ),
                      ],
                    ),
                    const SizedBox(height: DS.spacing10),
                    Text(
                      _usageLine(context, document),
                      style: theme.textTheme.bodyMedium?.copyWith(
                            color: DS.textSecondary,
                          ),
                    ),
                    if (nodePreview.isNotEmpty) ...[
                      const SizedBox(height: DS.spacing6),
                      Text(
                        nodePreview,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: theme.textTheme.bodySmall?.copyWith(
                              color: DS.textTertiary,
                            ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Icon(
                    expanded
                        ? Icons.keyboard_arrow_up_rounded
                        : Icons.keyboard_arrow_down_rounded,
                    color: DS.textSecondary,
                  ),
                  const SizedBox(height: DS.spacing10),
                  Text(
                    _uploadedLabel(context, document.uploadedAt),
                    style: theme.textTheme.labelSmall?.copyWith(
                          color: DS.textTertiary,
                        ),
                  ),
                ],
              ),
            ],
          ),
          AnimatedCrossFade(
            duration: const Duration(milliseconds: 220),
            firstChild: const SizedBox(width: double.infinity),
            secondChild: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: DS.spacing18),
                Divider(color: DS.borderSubtle),
                const SizedBox(height: DS.spacing14),
                _SectionHeader(
                  title: context.l10n.studyMaterialsAttachedNodesTitle,
                ),
                const SizedBox(height: DS.spacing10),
                if (document.attachedNodes.isEmpty)
                  _HintPanel(
                    icon: status == DocumentStatus.processing
                        ? Icons.sync_rounded
                        : Icons.hub_outlined,
                    text: status == DocumentStatus.processing
                        ? context.l10n.studyMaterialsNodesPending
                        : context.l10n.studyMaterialsNodesEmpty,
                  )
                else
                  Wrap(
                    spacing: DS.spacing8,
                    runSpacing: DS.spacing8,
                    children: document.attachedNodes.map((node) {
                      return _NodeChip(
                        node: node,
                        onNavigate: () => context.push(
                          GalaxyRoutes.knowledgeDetail
                              .replaceFirst(':id', node.nodeId),
                        ),
                        onFilter: () => onFilterByNode(node),
                      );
                    }).toList(),
                  ),
                const SizedBox(height: DS.spacing16),
                _SectionHeader(
                  title: context.l10n.studyMaterialsTopChunksTitle,
                ),
                const SizedBox(height: DS.spacing10),
                if (document.citationInsight.topChunks.isEmpty)
                  _HintPanel(
                    icon: Icons.notes_rounded,
                    text: context.l10n.studyMaterialsTopChunksEmpty,
                  )
                else
                  Column(
                    children: document.citationInsight.topChunks.map((chunk) {
                      return Padding(
                        padding:
                            const EdgeInsets.only(bottom: DS.spacing10),
                        child: _ChunkInsightCard(chunk: chunk),
                      );
                    }).toList(),
                  ),
                const SizedBox(height: DS.spacing16),
                Row(
                  children: [
                    Expanded(
                      child: _StatPanel(
                        label: context
                            .l10n.studyMaterialsConversationCountLabel,
                        value:
                            '${document.citationInsight.conversationCount}',
                      ),
                    ),
                    const SizedBox(width: DS.spacing10),
                    Expanded(
                      child: _StatPanel(
                        label: context.l10n.studyMaterialsReferenceCountLabel,
                        value: '${document.citationInsight.totalReferences}',
                      ),
                    ),
                    const SizedBox(width: DS.spacing10),
                    Expanded(
                      child: _StatPanel(
                        label: context.l10n.studyMaterialsKnowledgeStarsLabel,
                        value: '${document.knowledgeStarCount}',
                      ),
                    ),
                  ],
                ),
                if (document.qualityScore != null) ...[
                  const SizedBox(height: DS.spacing12),
                  _QualityIndicator(score: document.qualityScore!),
                ],
                const SizedBox(height: DS.spacing16),
                Wrap(
                  spacing: DS.spacing10,
                  runSpacing: DS.spacing10,
                  children: [
                    OutlinedButton.icon(
                      onPressed: onShareToGroup,
                      icon: const Icon(Icons.groups_rounded),
                      label: Text(
                        context.l10n.studyMaterialsShareAction,
                      ),
                    ),
                    OutlinedButton.icon(
                      onPressed: onDelete,
                      icon: Icon(
                        Icons.delete_outline_rounded,
                        color: DS.error,
                      ),
                      label: Text(
                        context.l10n.studyMaterialsDeleteAction,
                        style: TextStyle(color: DS.error),
                      ),
                    ),
                    OutlinedButton.icon(
                      onPressed: onRefresh,
                      icon: const Icon(Icons.refresh_rounded),
                      label: Text(
                        context.l10n.studyMaterialsRefreshAction,
                      ),
                    ),
                  ],
                ),
              ],
            ),
            crossFadeState:
                expanded ? CrossFadeState.showSecond : CrossFadeState.showFirst,
          ),
        ],
      ),
    );
  }

  static String _subjectLabel(BuildContext context, String? subjectCode) {
    switch ((subjectCode ?? '').trim().toUpperCase()) {
      case 'COSMOS':
        return context.l10n.studyMaterialsSubjectCosmos;
      case 'TECH':
        return context.l10n.studyMaterialsSubjectTech;
      case 'ART':
        return context.l10n.studyMaterialsSubjectArt;
      case 'CIVILIZATION':
        return context.l10n.studyMaterialsSubjectCivilization;
      case 'LIFE':
        return context.l10n.studyMaterialsSubjectLife;
      case 'WISDOM':
        return context.l10n.studyMaterialsSubjectWisdom;
      default:
        return context.l10n.studyMaterialsSubjectGeneral;
    }
  }

  static String _usageLine(BuildContext context, DocumentLibraryItem document) {
    final l10n = context.l10n;
    final weekly = document.citationInsight.referencesThisWeek;
    if (weekly > 0) {
      return l10n.studyMaterialsUsageWeekly(weekly);
    }
    if (document.citationInsight.totalReferences > 0) {
      return l10n.studyMaterialsUsageTotal(
        document.citationInsight.totalReferences,
      );
    }
    return l10n.studyMaterialsUsageEmpty;
  }

  static String _uploadedLabel(BuildContext context, DateTime uploadedAt) {
    final diff = DateTime.now().difference(uploadedAt);
    if (diff.inDays >= 1) {
      return context.l10n.studyMaterialsUploadedDays(diff.inDays);
    }
    if (diff.inHours >= 1) {
      return context.l10n.studyMaterialsUploadedHours(diff.inHours);
    }
    final minutes = diff.inMinutes <= 0 ? 1 : diff.inMinutes;
    return context.l10n.studyMaterialsUploadedMinutes(minutes);
  }
}

class _NodeChip extends StatelessWidget {
  const _NodeChip({
    required this.node,
    required this.onNavigate,
    required this.onFilter,
  });

  final DocumentGalaxyNode node;
  final VoidCallback onNavigate;
  final VoidCallback onFilter;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: DS.surfacePanel,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          InkWell(
            borderRadius: const BorderRadius.horizontal(
              left: Radius.circular(999),
            ),
            onTap: onNavigate,
            child: Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing12,
                vertical: DS.spacing10,
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    node.isPrimary ? Icons.star_rounded : Icons.hub_rounded,
                    size: 16,
                    color: DS.brandPrimary,
                  ),
                  const SizedBox(width: DS.spacing6),
                  Text(
                    node.name,
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: DS.textPrimary,
                          fontWeight: FontWeight.w600,
                        ),
                  ),
                ],
              ),
            ),
          ),
          Container(
            width: 1,
            height: 24,
            color: DS.borderSubtle,
          ),
          InkWell(
            borderRadius: const BorderRadius.horizontal(
              right: Radius.circular(999),
            ),
            onTap: onFilter,
            child: Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing10,
                vertical: DS.spacing10,
              ),
              child: Icon(
                Icons.filter_alt_outlined,
                size: 16,
                color: DS.textSecondary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _DocumentGlyph extends StatelessWidget {
  const _DocumentGlyph({required this.fileType});

  final String fileType;

  @override
  Widget build(BuildContext context) {
    final (icon, accent) = switch (fileType) {
      'pdf' => (Icons.picture_as_pdf_rounded, const Color(0xFFE06A6A)),
      'docx' => (Icons.description_rounded, const Color(0xFF63A1FF)),
      'pptx' => (Icons.slideshow_rounded, const Color(0xFFFFB45E)),
      'md' => (Icons.notes_rounded, const Color(0xFF74C8A6)),
      'image' => (Icons.image_rounded, const Color(0xFFC88BFF)),
      _ => (Icons.insert_drive_file_rounded, DS.textSecondary),
    };

    return Container(
      width: 60,
      height: 72,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            accent.withValues(alpha: 0.22),
            accent.withValues(alpha: 0.08),
          ],
        ),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: accent.withValues(alpha: 0.24)),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, color: accent, size: 28),
          const SizedBox(height: DS.spacing6),
          Text(
            fileType.toUpperCase(),
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: accent,
                  fontWeight: FontWeight.w800,
                ),
          ),
        ],
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.document});

  final DocumentLibraryItem document;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final status = document.effectiveStatus;
    late final Color color;
    late final String label;

    switch (status) {
      case DocumentStatus.processing:
        color = DS.warning;
        final progress = document.processingStatus?.progressPercent ?? 0;
        label = progress > 0
            ? l10n.studyMaterialsStatusProcessingPercent(progress)
            : l10n.studyMaterialsStatusProcessing;
      case DocumentStatus.ready:
        color = DS.success;
        label = document.knowledgeStarCount > 0
            ? l10n.studyMaterialsStatusKnowledgeStars(
                document.knowledgeStarCount,
              )
            : l10n.studyMaterialsStatusReady;
      case DocumentStatus.failed:
        color = DS.error;
        label = l10n.studyMaterialsStatusFailed;
    }

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (status == DocumentStatus.processing)
            SizedBox(
              width: 12,
              height: 12,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                value: (document.processingStatus?.progressPercent ?? 0) == 0
                    ? null
                    : (document.processingStatus!.progressPercent / 100),
                color: color,
              ),
            )
          else
            Icon(
              status == DocumentStatus.ready
                  ? Icons.auto_awesome_rounded
                  : Icons.error_outline_rounded,
              size: 14,
              color: color,
            ),
          const SizedBox(width: DS.spacing6),
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: color,
                  fontWeight: FontWeight.w700,
                ),
          ),
        ],
      ),
    );
  }
}

class _DraftsPendingPill extends StatelessWidget {
  const _DraftsPendingPill({required this.count, required this.onTap});

  final int count;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.brandPrimary20,
          borderRadius: BorderRadius.circular(999),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.rate_review_rounded, size: 14, color: DS.brandPrimary),
            const SizedBox(width: DS.spacing6),
            Text(
              '$count draft${count != 1 ? 's' : ''} to review',
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: DS.brandPrimary,
                    fontWeight: FontWeight.w700,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PillLabel extends StatelessWidget {
  const _PillLabel({
    required this.label,
    required this.icon,
  });

  final String label;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: DS.surfacePanel,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: DS.textSecondary),
          const SizedBox(width: DS.spacing6),
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: DS.textSecondary,
                ),
          ),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    return Text(
      title,
      style: Theme.of(context).textTheme.titleSmall?.copyWith(
            color: DS.textPrimary,
            fontWeight: FontWeight.w700,
          ),
    );
  }
}

class _HintPanel extends StatelessWidget {
  const _HintPanel({
    required this.icon,
    required this.text,
  });

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing14),
      decoration: BoxDecoration(
        color: DS.surfacePanel,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Row(
        children: [
          Icon(icon, color: DS.textSecondary),
          const SizedBox(width: DS.spacing10),
          Expanded(
            child: Text(
              text,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ChunkInsightCard extends StatelessWidget {
  const _ChunkInsightCard({required this.chunk});

  final DocumentCitationChunk chunk;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing14),
      decoration: BoxDecoration(
        color: DS.surfacePanel,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  chunk.sectionTitle?.trim().isNotEmpty ?? false
                      ? chunk.sectionTitle!
                      : chunk.label,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: DS.textPrimary,
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing10,
                  vertical: DS.spacing6,
                ),
                decoration: BoxDecoration(
                  color: DS.brandPrimary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  context.l10n.studyMaterialsChunkHitCount(chunk.hitCount),
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: DS.brandPrimary,
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            chunk.preview,
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.textSecondary,
                  height: 1.4,
                ),
          ),
        ],
      ),
    );
  }
}

class _StatPanel extends StatelessWidget {
  const _StatPanel({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.surfacePanel,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            value,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  color: DS.textPrimary,
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: DS.spacing4),
          Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: DS.textSecondary,
                ),
          ),
        ],
      ),
    );
  }
}

class _DocumentsEmptyState extends StatelessWidget {
  const _DocumentsEmptyState({
    required this.hasAnyDocuments,
    required this.searchActive,
    required this.onUpload,
    required this.onResetFilters,
  });

  final bool hasAnyDocuments;
  final bool searchActive;
  final VoidCallback onUpload;
  final VoidCallback onResetFilters;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final title = hasAnyDocuments && searchActive
        ? l10n.studyMaterialsNoResultsTitle
        : l10n.studyMaterialsEmptyTitle;
    final subtitle = hasAnyDocuments && searchActive
        ? l10n.studyMaterialsNoResultsSubtitle
        : l10n.studyMaterialsEmptySubtitle;

    return Padding(
      padding: const EdgeInsets.all(DS.spacing24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const _LargeGalaxyIllustration(),
          const SizedBox(height: DS.spacing24),
          Text(
            title,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: DS.textPrimary,
                  fontWeight: FontWeight.w800,
                ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: DS.spacing10),
          Text(
            subtitle,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  color: DS.textSecondary,
                  height: 1.5,
                ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: DS.spacing24),
          SparkleButton.primary(
            label: hasAnyDocuments && searchActive
                ? l10n.studyMaterialsResetFilters
                : l10n.studyMaterialsUploadCta,
            onPressed: hasAnyDocuments && searchActive
                ? onResetFilters
                : onUpload,
          ),
        ],
      ),
    );
  }
}

class _LargeGalaxyIllustration extends StatelessWidget {
  const _LargeGalaxyIllustration();

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 220,
      height: 180,
      child: Stack(
        children: [
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  colors: [
                    DS.brandPrimary.withValues(alpha: 0.16),
                    DS.brandSecondary.withValues(alpha: 0.08),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),
          Positioned(
            left: 44,
            top: 34,
            child: Container(
              width: 96,
              height: 96,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(
                  colors: [
                    DS.brandPrimary.withValues(alpha: 0.9),
                    DS.info.withValues(alpha: 0.82),
                  ],
                ),
                boxShadow: [
                  BoxShadow(
                    color: DS.brandPrimary.withValues(alpha: 0.24),
                    blurRadius: 34,
                  ),
                ],
              ),
              child: const Icon(
                Icons.auto_awesome_rounded,
                color: Colors.white,
                size: 42,
              ),
            ),
          ),
          Positioned(
            right: 28,
            top: 38,
            child: _OrbitTile(
              icon: Icons.description_outlined,
              color: DS.warning,
            ),
          ),
          Positioned(
            left: 24,
            bottom: 28,
            child: _OrbitTile(
              icon: Icons.picture_as_pdf_outlined,
              color: DS.error,
            ),
          ),
          Positioned(
            right: 48,
            bottom: 18,
            child: _OrbitTile(
              icon: Icons.notes_rounded,
              color: DS.success,
            ),
          ),
        ],
      ),
    );
  }
}

class _OrbitTile extends StatelessWidget {
  const _OrbitTile({
    required this.icon,
    required this.color,
  });

  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 52,
      height: 52,
      decoration: BoxDecoration(
        color: DS.surfaceOverlay,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: color.withValues(alpha: 0.26)),
        boxShadow: [
          BoxShadow(
            color: color.withValues(alpha: 0.14),
            blurRadius: 18,
          ),
        ],
      ),
      child: Icon(icon, color: color),
    );
  }
}

class _QualityIndicator extends StatelessWidget {
  const _QualityIndicator({required this.score});

  final double score;

  @override
  Widget build(BuildContext context) {
    final clamped = score.clamp(-1.0, 1.0);
    final color = clamped >= 0.3
        ? DS.success
        : clamped >= 0.0
            ? DS.warning
            : DS.error;
    final label = clamped >= 0.3
        ? 'High quality'
        : clamped >= 0.0
            ? 'Mixed feedback'
            : 'Low quality';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing10, vertical: DS.spacing6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.signal_cellular_alt_rounded, size: 14, color: color),
          const SizedBox(width: DS.spacing6),
          Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(color: color, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}
