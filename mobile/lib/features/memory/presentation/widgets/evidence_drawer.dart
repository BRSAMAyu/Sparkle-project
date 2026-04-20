import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/evidence_resolve_service.dart';
import 'package:sparkle/features/memory/presentation/widgets/evidence_cards.dart';

class EvidenceDrawer {
  static Future<void> show(
    BuildContext context, {
    required List<EvidenceRefModel> refs,
    required bool evidenceMissing,
  }) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: DS.deepSpaceStart,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(DS.lg)),
      ),
      builder: (_) => UncontrolledProviderScope(
        container: ProviderScope.containerOf(context),
        child: _EvidenceDrawerContent(
          refs: refs,
          evidenceMissing: evidenceMissing,
        ),
      ),
    );
  }
}

class _EvidenceDrawerContent extends ConsumerStatefulWidget {
  const _EvidenceDrawerContent({
    required this.refs,
    required this.evidenceMissing,
  });

  final List<EvidenceRefModel> refs;
  final bool evidenceMissing;

  @override
  ConsumerState<_EvidenceDrawerContent> createState() =>
      _EvidenceDrawerContentState();
}

class _EvidenceDrawerContentState
    extends ConsumerState<_EvidenceDrawerContent> {
  bool _loading = false;
  String? _error;
  List<EvidenceResolveItem> _resolved = [];

  @override
  void initState() {
    super.initState();
    if (!widget.evidenceMissing && AppFeatureFlags.enableEvidenceViewer) {
      _resolveEvidence();
    }
  }

  Future<void> _resolveEvidence() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final service = ref.read(evidenceResolveServiceProvider);
      final items = await service.resolveEvidence(widget.refs);
      if (!mounted) {
        return;
      }
      setState(() {
        _resolved = items;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = '${context.l10n.memoryEvidenceResolveFailed}: $e';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(DS.lg),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(context.l10n.memoryEvidenceChain, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: DS.sm),
              if (!AppFeatureFlags.enableEvidenceViewer)
                Text(
                  'Evidence viewer disabled',
                  style: Theme.of(context).textTheme.bodyMedium,
                )
              else if (widget.evidenceMissing)
                _buildMissingBanner()
              else if (_loading)
                const Center(child: CircularProgressIndicator())
              else if (_error != null)
                Text(_error!)
              else if (_resolved.isEmpty)
                Text(context.l10n.memoryNoEvidence, style: Theme.of(context).textTheme.bodyMedium)
              else
                Flexible(child: _buildGroupedEvidence()),
            ],
          ),
        ),
      );

  Widget _buildMissingBanner() => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: DS.semanticError.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(DS.md),
          border: Border.all(color: DS.semanticError.withValues(alpha: 0.4)),
        ),
        child: Text(
          'Evidence missing',
          style: TextStyle(color: DS.semanticError),
        ),
      );

  Widget _buildGroupedEvidence() {
    final grouped = <String, List<EvidenceResolveItem>>{};
    for (final item in _resolved) {
      grouped.putIfAbsent(item.type, () => []).add(item);
    }
    final entries = grouped.entries.toList()
      ..sort((a, b) => a.key.compareTo(b.key));
    return ListView(
      shrinkWrap: true,
      children: [
        for (final entry in entries) ...[
          Padding(
            padding: const EdgeInsets.only(bottom: DS.sm, top: DS.sm),
            child: Text(
              entry.key.toUpperCase(),
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
          ...entry.value.map(
            (item) => EvidenceCard(
              item: item,
              onRouteTap: _handleRouteTap,
            ),
          ),
        ],
      ],
    );
  }

  void _handleRouteTap(String route) {
    final router = GoRouter.of(context);
    Navigator.of(context).pop();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      router.go(route);
    });
  }
}
