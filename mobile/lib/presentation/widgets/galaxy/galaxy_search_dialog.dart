import 'dart:async';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/models/galaxy_model.dart';
import 'package:sparkle/presentation/providers/galaxy_provider.dart';

class GalaxySearchDialog extends ConsumerStatefulWidget {
  final Function(String nodeId) onNodeSelected;

  const GalaxySearchDialog({
    required this.onNodeSelected, super.key,
  });

  @override
  ConsumerState<GalaxySearchDialog> createState() => _GalaxySearchDialogState();
}

class _GalaxySearchDialogState extends ConsumerState<GalaxySearchDialog> {
  final TextEditingController _searchController = TextEditingController();
  Timer? _debounce;
  List<GalaxySearchResult> _results = [];
  bool _isLoading = false;

  @override
  void dispose() {
    _searchController.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  void _onSearchChanged(String query) {
    if (_debounce?.isActive ?? false) _debounce!.cancel();
    _debounce = Timer(const Duration(milliseconds: 500), () {
      if (query.isNotEmpty) {
        _performSearch(query);
      } else {
        setState(() {
          _results = [];
        });
      }
    });
  }

  Future<void> _performSearch(String query) async {
    setState(() {
      _isLoading = true;
    });
    try {
      final results = await ref.read(galaxyProvider.notifier).searchNodes(query);
      if (mounted) {
        setState(() {
          _results = results;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.all(DS.xl),
      child: Container(
        width: double.infinity,
        height: 400,
        decoration: BoxDecoration(
          color: const Color(0xFF1E1E1E).withValues(alpha: 0.95),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: DS.brandPrimary24),
          boxShadow: [
            BoxShadow(
              color: DS.brandPrimary.withValues(alpha: 0.5),
              blurRadius: 20,
              spreadRadius: 5,
            ),
          ],
        ),
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: TextField(
                controller: _searchController,
                style: const TextStyle(color: DS.brandPrimary),
                decoration: InputDecoration(
                  hintText: '搜索星系...',
                  hintStyle: TextStyle(color: DS.brandPrimary.withValues(alpha: 0.5)),
                  prefixIcon: const Icon(Icons.search, color: DS.brandPrimary70),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide.none,
                  ),
                  filled: true,
                  fillColor: DS.brandPrimary.withValues(alpha: 0.1),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                ),
                onChanged: _onSearchChanged,
                autofocus: true,
              ),
            ),
            if (_isLoading)
              const Expanded(
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_results.isEmpty && _searchController.text.isNotEmpty)
              const Expanded(
                child: Center(
                  child: Text(
                    '未找到相关节点',
                    style: TextStyle(color: DS.brandPrimary54),
                  ),
                ),
              )
            else
              Expanded(
                child: ListView.builder(
                  itemCount: _results.length,
                  itemBuilder: (context, index) {
                    final item = _results[index];
                    return ListTile(
                      title: Text(
                        item.node.name,
                        style: const TextStyle(color: DS.brandPrimary),
                      ),
                      subtitle: item.node.description != null
                          ? Text(
                              item.node.description!,
                              style: TextStyle(color: DS.brandPrimary.withValues(alpha: 0.6)),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            )
                          : null,
                      trailing: _buildMatchScore(item.similarity),
                      onTap: () {
                        widget.onNodeSelected(item.node.id);
                        Navigator.of(context).pop();
                      },
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildMatchScore(double similarity) {
    // Visual indicator of match quality
    final percentage = (similarity * 100).toInt();
    return Text(
      '$percentage%',
      style: TextStyle(
        color: similarity > 0.8 ? DS.successAccent : DS.brandPrimary54,
        fontSize: 12,
      ),
    );
  }
}
