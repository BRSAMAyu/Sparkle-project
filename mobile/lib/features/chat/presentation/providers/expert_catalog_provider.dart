import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/chat/data/models/expert_catalog_model.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';

final multiAgentCatalogProvider =
    FutureProvider<MultiAgentCatalog>((ref) async {
  final repository = ref.watch(chatRepositoryProvider);
  return repository.getMultiAgentCatalog();
});
